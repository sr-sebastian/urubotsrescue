"""Detector de carteles hazmat con YOLO (ultralytics). Corre en el Jetson (GPU, TensorRT opcional).

Entrenar el modelo: ver docs/05-software/percepcion.md (dataset de etiquetas hazmat + aumentaciones).
Parámetros: model_path (.pt o .engine), conf (0.5), imgsz (640), device ("0" GPU / "cpu").
"""

from __future__ import annotations

import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from carpincho_interfaces.msg import DetectionArray

from .common import BRIDGE, draw, make_detection, to_bgr


class HazmatDetector(Node):
    def __init__(self) -> None:
        super().__init__("hazmat_detector")
        self.model_path = self.declare_parameter("model_path", "hazmat_yolov8n.pt").value
        self.conf = self.declare_parameter("conf", 0.5).value
        self.imgsz = self.declare_parameter("imgsz", 640).value
        self.device = self.declare_parameter("device", "0").value
        self.max_rate = self.declare_parameter("max_rate", 8.0).value
        self.type = self.declare_parameter("detection_type", "hazmat_sign").value
        self.model = None
        try:
            from ultralytics import YOLO

            self.model = YOLO(self.model_path)
            self.get_logger().info(f"Modelo cargado: {self.model_path}")
        except Exception as e:  # noqa: BLE001
            self.get_logger().error(f"No pude cargar YOLO ({e}). pip install ultralytics y revisá model_path.")
        self.last = 0.0
        self.pub = self.create_publisher(DetectionArray, "detections", 10)
        self.pub_img = self.create_publisher(Image, "image_annotated", 2)
        self.create_subscription(Image, "image", self.on_image, qos_profile_sensor_data)

    def on_image(self, msg: Image) -> None:
        if self.model is None:
            return
        now = time.monotonic()
        if now - self.last < 1.0 / self.max_rate:
            return
        self.last = now
        img = to_bgr(msg)
        res = self.model.predict(img, conf=self.conf, imgsz=self.imgsz, device=self.device, verbose=False)[0]
        arr = DetectionArray()
        arr.header = msg.header
        names = res.names
        for b in res.boxes:
            x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
            name = names[int(b.cls[0])]
            arr.detections.append(make_detection(msg.header, self.type, name, float(b.conf[0]),
                                                 (x1, y1, x2 - x1, y2 - y1)))
        self.pub.publish(arr)
        if self.pub_img.get_subscription_count():
            out = BRIDGE.cv2_to_imgmsg(draw(img, arr.detections), "bgr8")
            out.header = msg.header
            self.pub_img.publish(out)


def main() -> None:
    rclpy.init()
    n = HazmatDetector()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
