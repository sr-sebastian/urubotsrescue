"""Algoritmos de visión puros (numpy). Los nodos ROS solo hacen de envoltorio."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


# ---------------------------------------------------------------- movimiento
@dataclass
class MotionDetector:
    """Detecta el blanco giratorio del cajón de víctimas por diferencia de cuadros.

    Mantiene un fondo con media exponencial y devuelve la caja del blob en movimiento más grande.
    Funciona con el robot QUIETO (frenar antes de evaluar el sensor)."""

    alpha: float = 0.05            # velocidad de adaptación del fondo
    threshold: int = 25            # diferencia de gris para considerar "movimiento"
    min_area_frac: float = 0.002   # área mínima del blob (fracción de la imagen)
    _bg: np.ndarray | None = field(default=None, repr=False)

    def update(self, gray: np.ndarray) -> tuple[int, int, int, int] | None:
        g = gray.astype(np.float32)
        if self._bg is None or self._bg.shape != g.shape:
            self._bg = g.copy()
            return None
        diff = np.abs(g - self._bg)
        self._bg = (1 - self.alpha) * self._bg + self.alpha * g
        mask = diff > self.threshold
        if mask.sum() < self.min_area_frac * mask.size:
            return None
        return largest_blob_bbox(mask)

    def reset(self) -> None:
        self._bg = None


def largest_blob_bbox(mask: np.ndarray, cell: int = 8) -> tuple[int, int, int, int] | None:
    """Caja (x, y, w, h) de la región conexa más grande, con una grilla gruesa (rápido, sin OpenCV)."""
    H, W = mask.shape
    gh, gw = H // cell, W // cell
    if gh == 0 or gw == 0:
        return None
    coarse = mask[:gh * cell, :gw * cell].reshape(gh, cell, gw, cell).mean(axis=(1, 3)) > 0.15
    labels = np.zeros((gh, gw), np.int32)
    best, best_n, cur = None, 0, 0
    for i in range(gh):
        for j in range(gw):
            if coarse[i, j] and labels[i, j] == 0:
                cur += 1
                stack = [(i, j)]
                labels[i, j] = cur
                cells = []
                while stack:
                    a, b = stack.pop()
                    cells.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        na, nb = a + da, b + db
                        if 0 <= na < gh and 0 <= nb < gw and coarse[na, nb] and labels[na, nb] == 0:
                            labels[na, nb] = cur
                            stack.append((na, nb))
                if len(cells) > best_n:
                    best_n, best = len(cells), cells
    if not best:
        return None
    rs = [c[0] for c in best]
    cs = [c[1] for c in best]
    return min(cs) * cell, min(rs) * cell, (max(cs) - min(cs) + 1) * cell, (max(rs) - min(rs) + 1) * cell


# ---------------------------------------------------------------- térmica
def raw_to_celsius(raw: np.ndarray, scale: float, offset: float) -> np.ndarray:
    """Cámaras tipo InfiRay P2/TC001 en modo Y16: T[°C] = raw * scale + offset (p. ej. 1/64, -273.15)."""
    return raw.astype(np.float32) * scale + offset


def hotspot(temp_c: np.ndarray) -> tuple[int, int, float]:
    idx = int(np.argmax(temp_c))
    r, c = divmod(idx, temp_c.shape[1])
    return c, r, float(temp_c[r, c])


def normalize_u8(temp_c: np.ndarray, t_min: float | None = None, t_max: float | None = None) -> np.ndarray:
    lo = float(np.percentile(temp_c, 2)) if t_min is None else t_min
    hi = float(np.percentile(temp_c, 99.5)) if t_max is None else t_max
    hi = max(hi, lo + 1.0)
    return (np.clip((temp_c - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)


def hot_bbox(temp_c: np.ndarray, delta: float = 6.0) -> tuple[int, int, int, int] | None:
    """Caja de la zona más caliente que el fondo por más de `delta` °C (el calentador de manos)."""
    bg = float(np.median(temp_c))
    mask = temp_c > bg + delta
    if mask.sum() < 4:
        return None
    return largest_blob_bbox(mask, cell=2)


# ---------------------------------------------------------------- geometría
def bbox_to_point(depth_m: np.ndarray, bbox: tuple[int, int, int, int], fx: float, fy: float,
                  cx: float, cy: float) -> tuple[float, float, float] | None:
    """Punto 3D (frame óptico de la cámara: Z adelante, X derecha, Y abajo) del centro de la caja,
    usando la mediana de la profundidad válida dentro del 50% central de la caja."""
    x, y, w, h = bbox
    H, W = depth_m.shape
    x0, x1 = max(0, x + w // 4), min(W, x + 3 * w // 4 + 1)
    y0, y1 = max(0, y + h // 4), min(H, y + 3 * h // 4 + 1)
    roi = depth_m[y0:y1, x0:x1]
    valid = roi[(roi > 0.1) & (roi < 8.0) & np.isfinite(roi)]
    if valid.size < 5:
        return None
    z = float(np.median(valid))
    u, v = x + w / 2.0, y + h / 2.0
    return (u - cx) * z / fx, (v - cy) * z / fy, z


def depth_to_meters(depth: np.ndarray) -> np.ndarray:
    """Acepta 16UC1 en mm (RealSense/Orbbec) o 32FC1 en m."""
    if depth.dtype == np.uint16:
        return depth.astype(np.float32) / 1000.0
    return depth.astype(np.float32)
