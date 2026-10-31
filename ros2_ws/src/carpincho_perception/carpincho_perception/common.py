"""Utilidades compartidas por los nodos de percepción (dependen de ROS / OpenCV)."""

from __future__ import annotations

import cv2
import numpy as np
from cv_bridge import CvBridge

from carpincho_interfaces.msg import Detection

BRIDGE = CvBridge()

COLORS = {
    "qr_code": (0, 200, 0),
    "hazmat_sign": (0, 120, 255),
    "motion": (255, 0, 255),
    "heat_sig": (0, 0, 255),
    "ar_code": (0, 200, 255),
    "real_object": (255, 80, 0),
}


def to_bgr(msg) -> np.ndarray:
    img = BRIDGE.imgmsg_to_cv2(msg, desired_encoding="passthrough")
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if msg.encoding.lower().startswith("rgb"):
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return img


def make_detection(header, type_: str, name: str, conf: float, bbox) -> Detection:
    d = Detection()
    d.header = header
    d.type = type_
    d.name = name
    d.confidence = float(conf)
    d.x, d.y, d.w, d.h = (int(v) for v in bbox)
    return d


def draw(img: np.ndarray, dets: list[Detection]) -> np.ndarray:
    """Dibuja caja + etiqueta (el reglamento pide caja y nombre en la pantalla del operador)."""
    for d in dets:
        c = COLORS.get(d.type, (255, 255, 255))
        cv2.rectangle(img, (d.x, d.y), (d.x + d.w, d.y + d.h), c, 2)
        label = f"{d.name} {d.confidence:.2f}" if d.confidence < 0.999 else d.name
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        y0 = max(th + 4, d.y)
        cv2.rectangle(img, (d.x, y0 - th - 4), (d.x + tw + 4, y0), c, -1)
        cv2.putText(img, label, (d.x + 2, y0 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    return img
