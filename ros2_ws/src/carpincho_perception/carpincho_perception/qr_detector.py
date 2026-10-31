"""Detector de códigos QR (OpenCV). Muestra el texto decodificado en pantalla (tarea QR / Inspect).

Suscribe: image (sensor_msgs/Image)   — remapear a la cámara que corresponda
Publica:  detections (DetectionArray), image_annotated (Image), qr/text (String, solo textos nuevos)
"""

from __future__ import annotations

import time

import cv2
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from carpincho_interfaces.msg import DetectionArray

from .common import BRIDGE, draw, make_detection, to_bgr


class QrDetector(Node):
    def __init__(self) -> None:
        super().__init__("qr_detector")
        self.max_rate = self.declare_parameter("max_rate", 10.0).value
        self.upscale = self.declare_parameter("upscale", 1.0).value   # >1 ayuda con QR chicos/lejanos
        self.det = cv2.QRCodeDetector()
        try:  # detector WeChat (más robusto) si está opencv-contrib
            self.wechat = cv2.wechat_qrcode_WeChatQRCode()
        except Exception:  # noqa: BLE001
            self.wechat = None
        self.last = 0.0
        self.seen: dict[str, float] = {}
        self.pub = self.create_publisher(DetectionArray, "detections", 10)
        self.pub_img = self.create_publisher(Image, "image_annotated", 2)
        self.pub_txt = self.create_publisher(String, "qr/text", 10)
        self.create_subscription(Image, "image", self.on_image, qos_profile_sensor_data)

    def decode(self, img):
        out = []
        if self.wechat is not None:
            texts, pts = self.wechat.detectAndDecode(img)
            for t, p in zip(texts, pts):
                out.append((t, p.reshape(-1, 2)))
            return out
        ok, texts, pts, _ = self.det.detectAndDecodeMulti(img)
        if ok and pts is not None:
            for t, p in zip(texts, pts):
                if t:
                    out.append((t, p.reshape(-1, 2)))
        return out

    def on_image(self, msg: Image) -> None:
        now = time.monotonic()
        if now - self.last < 1.0 / self.max_rate:
            return
        self.last = now
        img = to_bgr(msg)
        work = cv2.resize(img, None, fx=self.upscale, fy=self.upscale) if self.upscale != 1.0 else img
        arr = DetectionArray()
        arr.header = msg.header
        for text, pts in self.decode(work):
            pts = pts / self.upscale
            x, y = pts.min(axis=0)
            x2, y2 = pts.max(axis=0)
            arr.detections.append(make_detection(msg.header, "qr_code", text, 1.0, (x, y, x2 - x, y2 - y)))
            if now - self.seen.get(text, -1e9) > 5.0:
                self.pub_txt.publish(String(data=text))
                self.get_logger().info(f"QR: {text}")
            self.seen[text] = now
        self.pub.publish(arr)
        if self.pub_img.get_subscription_count():
            out = BRIDGE.cv2_to_imgmsg(draw(img, arr.detections), "bgr8")
            out.header = msg.header
            self.pub_img.publish(out)


def main() -> None:
    rclpy.init()
    n = QrDetector()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
