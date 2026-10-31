"""Visualización de la cámara térmica (tarea "Thermal Image Acuity" y firma de calor del laberinto).

Entrada: thermal/image_raw — mono16 (Y16, temperatura cruda) o mono8/bgr8 (imagen ya coloreada).
Salida:  thermal/image_color (Image con paleta "inferno" + temperatura máx.), detections (heat_sig).
"""

from __future__ import annotations

import cv2
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from carpincho_interfaces.msg import DetectionArray

from .common import BRIDGE, make_detection
from .vision import hot_bbox, hotspot, normalize_u8, raw_to_celsius


class ThermalViewer(Node):
    def __init__(self) -> None:
        super().__init__("thermal_viewer")
        self.scale = self.declare_parameter("raw_scale", 1.0 / 64.0).value
        self.offset = self.declare_parameter("raw_offset", -273.15).value
        self.heat_threshold = self.declare_parameter("heat_threshold_c", 32.0).value
        self.upscale = self.declare_parameter("upscale", 3).value
        self.pub_img = self.create_publisher(Image, "thermal/image_color", 2)
        self.pub = self.create_publisher(DetectionArray, "detections", 10)
        self.create_subscription(Image, "thermal/image_raw", self.on_image, qos_profile_sensor_data)

    def on_image(self, msg: Image) -> None:
        raw = BRIDGE.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        arr = DetectionArray()
        arr.header = msg.header
        if raw.dtype == np.uint16:
            t = raw_to_celsius(raw, self.scale, self.offset)
            u8 = normalize_u8(t)
            c, r, tmax = hotspot(t)
            box = hot_bbox(t)
            if tmax >= self.heat_threshold and box is not None:
                arr.detections.append(make_detection(msg.header, "heat_sig", "0", 1.0, box))
        else:
            u8 = raw if raw.ndim == 2 else cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
            c, r, tmax = hotspot(u8.astype(np.float32))
            tmax = float("nan")
        color = cv2.applyColorMap(u8, cv2.COLORMAP_INFERNO)
        k = int(self.upscale)
        color = cv2.resize(color, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
        cv2.drawMarker(color, (c * k, r * k), (255, 255, 255), cv2.MARKER_CROSS, 18, 2)
        if np.isfinite(tmax):
            cv2.putText(color, f"max {tmax:.1f} C", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        for d in arr.detections:
            cv2.rectangle(color, (d.x * k, d.y * k), ((d.x + d.w) * k, (d.y + d.h) * k), (0, 255, 0), 2)
        out = BRIDGE.cv2_to_imgmsg(color, "bgr8")
        out.header = msg.header
        self.pub_img.publish(out)
        self.pub.publish(arr)


def main() -> None:
    rclpy.init()
    n = ThermalViewer()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
