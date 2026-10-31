"""Detección de movimiento (disco giratorio del cajón de víctimas). Frenar el robot antes de usarlo.

Publica caja + seguimiento en image_annotated. Servicio motion/reset para reiniciar el fondo.
"""

from __future__ import annotations

import cv2
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

from carpincho_interfaces.msg import DetectionArray

from .common import BRIDGE, draw, make_detection, to_bgr
from .vision import MotionDetector


class MotionNode(Node):
    def __init__(self) -> None:
        super().__init__("motion_detector")
        self.md = MotionDetector(alpha=self.declare_parameter("alpha", 0.05).value,
                                 threshold=self.declare_parameter("threshold", 25).value,
                                 min_area_frac=self.declare_parameter("min_area_frac", 0.002).value)
        self.scale = self.declare_parameter("scale", 0.5).value
        self.trail = []
        self.pub = self.create_publisher(DetectionArray, "detections", 10)
        self.pub_img = self.create_publisher(Image, "image_annotated", 2)
        self.create_subscription(Image, "image", self.on_image, qos_profile_sensor_data)
        self.create_service(Trigger, "motion/reset", self.on_reset)

    def on_reset(self, req, res):
        self.md.reset()
        self.trail.clear()
        res.success, res.message = True, "fondo reiniciado"
        return res

    def on_image(self, msg: Image) -> None:
        img = to_bgr(msg)
        small = cv2.resize(img, None, fx=self.scale, fy=self.scale)
        gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
        box = self.md.update(gray)
        arr = DetectionArray()
        arr.header = msg.header
        if box is not None:
            x, y, w, h = (v / self.scale for v in box)
            arr.detections.append(make_detection(msg.header, "motion", "movimiento", 1.0, (x, y, w, h)))
            self.trail = (self.trail + [(int(x + w / 2), int(y + h / 2))])[-60:]
        self.pub.publish(arr)
        if self.pub_img.get_subscription_count():
            out = draw(img, arr.detections)
            for p, q in zip(self.trail, self.trail[1:]):
                cv2.line(out, p, q, (255, 0, 255), 2)
            m = BRIDGE.cv2_to_imgmsg(out, "bgr8")
            m.header = msg.header
            self.pub_img.publish(m)


def main() -> None:
    rclpy.init()
    n = MotionNode()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
