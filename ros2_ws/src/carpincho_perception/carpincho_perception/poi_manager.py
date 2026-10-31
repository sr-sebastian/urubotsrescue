"""Ubica en el mapa las detecciones (con profundidad + TF), las confirma y deduplica.

Suscribe: /perception/detections (DetectionArray) — todos los detectores remapeados acá
          depth_topic (Image alineada al color) + camera_info_topic (CameraInfo)
          /autonomy/active (Bool) — para marcar modo A/T
Publica:  /poi/list (PoiArray), /poi/markers (MarkerArray)
Servicio: /poi/clear (Trigger)
"""

from __future__ import annotations

import time

import rclpy
from rclpy.executors import ExternalShutdownException
from geometry_msgs.msg import PointStamped
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Bool
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformListener
from visualization_msgs.msg import Marker, MarkerArray

from carpincho_interfaces.msg import DetectionArray, Poi, PoiArray

from .common import BRIDGE
from .poi_store import PoiStore
from .vision import bbox_to_point, depth_to_meters

try:
    import tf2_geometry_msgs  # noqa: F401  (registra PointStamped en tf2)
except ImportError:  # pragma: no cover
    tf2_geometry_msgs = None

REPORT_TYPES = ("ar_code", "hazmat_sign", "real_object", "heat_sig")
MARKER_COLORS = {"ar_code": (1.0, 0.78, 0.0), "hazmat_sign": (1.0, 0.39, 0.12),
                 "real_object": (0.94, 0.04, 0.04), "heat_sig": (1.0, 0.0, 1.0)}


class PoiManager(Node):
    def __init__(self) -> None:
        super().__init__("poi_manager")
        p = self.declare_parameter
        self.map_frame = p("map_frame", "map").value
        self.robot_name = p("robot_name", "Carpincho").value
        self.fallback_range = p("fallback_range", 0.6).value
        self.store = PoiStore(p("min_hits", 3).value, p("radius", 0.5).value)
        self.depth = None
        self.depth_frame = ""
        self.K = None
        self.autonomous = False
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.pub_list = self.create_publisher(PoiArray, "/poi/list", 10)
        self.pub_mk = self.create_publisher(MarkerArray, "/poi/markers", 10)
        self.create_subscription(DetectionArray, "/perception/detections", self.on_dets, 20)
        self.create_subscription(Image, p("depth_topic", "/depth_cam/aligned_depth_to_color/image_raw").value,
                                 self.on_depth, qos_profile_sensor_data)
        self.create_subscription(CameraInfo, p("camera_info_topic", "/depth_cam/color/camera_info").value,
                                 self.on_info, 10)
        self.create_subscription(Bool, "/autonomy/active", lambda m: setattr(self, "autonomous", m.data), 10)
        self.create_service(Trigger, "/poi/clear", self.on_clear)
        self.create_timer(1.0, self.publish)

    def on_depth(self, msg: Image) -> None:
        self.depth = depth_to_meters(BRIDGE.imgmsg_to_cv2(msg, desired_encoding="passthrough"))
        self.depth_frame = msg.header.frame_id

    def on_info(self, msg: CameraInfo) -> None:
        self.K = (msg.k[0], msg.k[4], msg.k[2], msg.k[5])

    def on_clear(self, req, res):
        self.store.clear()
        res.success, res.message = True, "POIs borrados"
        return res

    def locate(self, det) -> PointStamped | None:
        ps = PointStamped()
        ps.header = det.header
        if det.has_position:
            ps.point = det.position
        elif self.depth is not None and self.K is not None and det.header.frame_id == self.depth_frame:
            pt = bbox_to_point(self.depth, (det.x, det.y, det.w, det.h), *self.K)
            if pt is None:
                return None
            ps.point.x, ps.point.y, ps.point.z = pt
        else:
            # sin profundidad (p. ej. térmica): punto a distancia fija sobre el eje óptico
            ps.point.z = self.fallback_range
        try:
            return self.tf_buffer.transform(ps, self.map_frame, timeout=Duration(seconds=0.1))
        except Exception as e:  # noqa: BLE001
            self.get_logger().warn(f"TF {det.header.frame_id}->{self.map_frame}: {e}", throttle_duration_sec=5.0)
            return None

    def on_dets(self, msg: DetectionArray) -> None:
        for d in msg.detections:
            if d.type not in REPORT_TYPES:
                continue
            p = self.locate(d)
            if p is None:
                continue
            c = self.store.add(d.type, d.name, p.point.x, p.point.y, p.point.z, d.confidence, time.time(),
                               "A" if self.autonomous else "T")
            if c is not None:
                self.get_logger().info(f"POI #{c.id} {c.type} '{c.name}' en ({c.x:.2f}, {c.y:.2f}, {c.z:.2f})")
                self.publish()

    def publish(self) -> None:
        arr = PoiArray()
        arr.header.stamp = self.get_clock().now().to_msg()
        arr.header.frame_id = self.map_frame
        mk = MarkerArray()
        for c in self.store.confirmed:
            p = Poi()
            p.header = arr.header
            p.id, p.type, p.name = c.id, c.type, c.name
            p.position.x, p.position.y, p.position.z = c.x, c.y, c.z
            p.confidence = c.confidence
            p.robot, p.mode = self.robot_name, c.mode
            p.found.sec = int(c.t)
            p.found.nanosec = int((c.t % 1) * 1e9)
            arr.pois.append(p)
            for k, (typ, scale) in enumerate(((Marker.SPHERE, 0.15), (Marker.TEXT_VIEW_FACING, 0.12))):
                m = Marker()
                m.header = arr.header
                m.ns, m.id, m.type = "poi", c.id * 2 + k, typ
                m.pose.position.x, m.pose.position.y = c.x, c.y
                m.pose.position.z = c.z + (0.2 if k else 0.0)
                m.pose.orientation.w = 1.0
                m.scale.x = m.scale.y = m.scale.z = scale
                m.color.r, m.color.g, m.color.b = MARKER_COLORS.get(c.type, (1.0, 1.0, 1.0))
                m.color.a = 1.0
                m.text = f"#{c.id} {c.name}"
                mk.markers.append(m)
        self.pub_list.publish(arr)
        self.pub_mk.publish(mk)


def main() -> None:
    rclpy.init()
    n = PoiManager()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
