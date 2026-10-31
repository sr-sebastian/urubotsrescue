"""Genera los archivos de entrega del laberinto (GeoTIFF 2D, PLY 3D y CSV de POIs) en el robot.

Servicios: /mission/start  (Trigger) — marca la hora de inicio y reinicia el recorrido
           /mission/export (Trigger) — escribe los 3 archivos en output_dir/<fecha-hora>/
Los archivos se generan automáticamente (el reglamento prohíbe editarlos a mano) y hay 5 minutos
para copiarlos: tools/fetch_mission.sh los trae a la estación de operador.
"""

from __future__ import annotations

import os
from datetime import datetime

import cv2
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import PointCloud2
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformListener

from carpincho_interfaces.msg import PoiArray

from .rrl_export import (C_FILENAME, C_SCALE, GridMap, PoiRow, filenames, map_to_ply_frame, ply_ascii,
                         pois_csv, render_map, voxel_downsample)

try:
    from sensor_msgs_py import point_cloud2
except ImportError:  # pragma: no cover
    point_cloud2 = None


def bgr(c):
    return (c[2], c[1], c[0])


class MissionExporter(Node):
    def __init__(self) -> None:
        super().__init__("mission_exporter")
        p = self.declare_parameter
        self.team = p("team", "UruBots").value
        self.country = p("country", "Uruguay").value
        self.mission = p("mission", "Prelim1").value
        self.robot = p("robot_name", "Carpincho").value
        self.out_dir = os.path.expanduser(p("output_dir", "~/carpincho_mission").value)
        self.map_frame = p("map_frame", "map").value
        self.base_frame = p("base_frame", "base_footprint").value
        self.front_offset = p("front_offset", 0.26).value
        self.voxel = p("voxel", 0.03).value
        self.grid = None
        self.cloud = None
        self.pois: list = []
        self.path: list[tuple[float, float]] = []
        self.start = datetime.now()
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(OccupancyGrid, p("map_topic", "/map").value, self.on_map, latched)
        self.create_subscription(PointCloud2, p("cloud_topic", "/Laser_map").value, self.on_cloud, 2)
        self.create_subscription(PoiArray, "/poi/list", lambda m: setattr(self, "pois", m.pois), 10)
        self.create_service(Trigger, "/mission/start", self.on_start)
        self.create_service(Trigger, "/mission/export", self.on_export)
        self.create_timer(0.5, self.track_path)

    def on_map(self, m: OccupancyGrid) -> None:
        self.grid = m

    def on_cloud(self, m: PointCloud2) -> None:
        self.cloud = m

    def on_start(self, req, res):
        self.start = datetime.now()
        self.path.clear()
        res.success, res.message = True, f"misión iniciada {self.start:%H:%M:%S}"
        return res

    def track_path(self) -> None:
        try:
            t = self.tf_buffer.lookup_transform(self.map_frame, self.base_frame, rclpy.time.Time())
        except Exception:  # noqa: BLE001
            return
        x, y = t.transform.translation.x, t.transform.translation.y
        if not self.path or np.hypot(x - self.path[-1][0], y - self.path[-1][1]) > 0.05:
            self.path.append((x, y))

    def rows(self) -> list[PoiRow]:
        out = []
        for p in self.pois:
            t = datetime.fromtimestamp(p.found.sec + p.found.nanosec * 1e-9).strftime("%H:%M:%S")
            out.append(PoiRow(p.id, t, p.type, p.name, p.position.x, p.position.y, p.position.z, p.robot, p.mode))
        return out

    def on_export(self, req, res):
        try:
            folder = os.path.join(self.out_dir, self.start.strftime("%Y%m%d-%H%M%S"))
            os.makedirs(folder, exist_ok=True)
            names = filenames(self.start.year, self.team, self.mission, self.start)
            rows = self.rows()
            with open(os.path.join(folder, names["csv"]), "w", encoding="ascii", errors="replace") as f:
                f.write(pois_csv(rows, self.team, self.country, self.mission, self.start))
            msgs = [f"CSV: {len(rows)} POIs"]
            if self.grid is not None:
                self.write_tiff(os.path.join(folder, names["tiff"]), names["tiff"], rows)
                msgs.append("TIFF ok")
            else:
                msgs.append("SIN /map (no hay TIFF)")
            if self.cloud is not None and point_cloud2 is not None:
                n = self.write_ply(os.path.join(folder, names["ply"]))
                msgs.append(f"PLY: {n} puntos")
            else:
                msgs.append("SIN nube 3D (no hay PLY)")
            res.success, res.message = True, f"{folder}: " + ", ".join(msgs)
        except Exception as e:  # noqa: BLE001
            res.success, res.message = False, f"error exportando: {e}"
        self.get_logger().info(res.message)
        return res

    def write_tiff(self, path: str, title: str, rows: list[PoiRow]) -> None:
        g = self.grid
        data = np.array(g.data, dtype=np.int8).reshape(g.info.height, g.info.width)
        grid = GridMap(data, g.info.resolution, g.info.origin.position.x, g.info.origin.position.y)
        img, tf = render_map(grid, self.path, rows)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        ppm = tf["px_per_m"]
        H, W = img.shape[:2]
        cv2.putText(img, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, bgr(C_FILENAME), 2)
        # escala de exactamente 1 m (arriba a la derecha) + ejes X arriba / Y izquierda
        x1 = W - 20
        cv2.line(img, (x1 - ppm, 40), (x1, 40), bgr(C_SCALE), 3)
        cv2.putText(img, "1 m", (x1 - ppm // 2 - 18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, bgr(C_SCALE), 2)
        ox, oy = x1 - ppm - 40, 90
        cv2.arrowedLine(img, (ox, oy), (ox, oy - ppm // 2), bgr(C_SCALE), 2, tipLength=0.25)
        cv2.arrowedLine(img, (ox, oy), (ox - ppm // 2, oy), bgr(C_SCALE), 2, tipLength=0.25)
        cv2.putText(img, "X", (ox + 6, oy - ppm // 2 + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, bgr(C_SCALE), 2)
        cv2.putText(img, "Y", (ox - ppm // 2 - 4, oy - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, bgr(C_SCALE), 2)
        for r, c, p in tf["marks"]:
            label = p.name if p.type == "ar_code" else p.name[:2].upper()
            cv2.putText(img, label, (c - 9, r + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2)
            cv2.putText(img, str(p.detection), (c + 12, r - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        cv2.imwrite(path, img)

    def to_map(self, pts: np.ndarray, frame: str) -> np.ndarray:
        if not frame or frame == self.map_frame:
            return pts
        t = self.tf_buffer.lookup_transform(self.map_frame, frame, rclpy.time.Time()).transform
        w, x, y, z = t.rotation.w, t.rotation.x, t.rotation.y, t.rotation.z
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        return pts @ R.T + np.array([t.translation.x, t.translation.y, t.translation.z])

    def write_ply(self, path: str) -> int:
        pts = point_cloud2.read_points_numpy(self.cloud, field_names=("x", "y", "z"), skip_nans=True)
        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 3)
        # la nube de FAST-LIO viene en camera_init (el LiDAR en la pose inicial): pasarla a map
        pts = self.to_map(pts, self.cloud.header.frame_id)
        pts, _ = voxel_downsample(pts, self.voxel)
        pts = map_to_ply_frame(pts, self.front_offset)
        with open(path, "w", encoding="ascii") as f:
            f.write(ply_ascii(pts, self.team, self.start.strftime("%H:%M:%S"), self.mission))
        return len(pts)


def main() -> None:
    rclpy.init()
    n = MissionExporter()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
