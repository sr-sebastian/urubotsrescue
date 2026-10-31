"""Cinemática diferencial de orugas + odometría (Python puro, testeable)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class TrackGeometry:
    # separación entre centros de oruga (2 * Y_TRACK_C = 0.275 m) multiplicada por un factor de
    # deslizamiento: las orugas patinan al girar, así que la separación "efectiva" es mayor.
    # Calibrar: girar 10 vueltas en el lugar y comparar con el IMU (ver docs/05-software/calibracion.md)
    track_separation: float = 0.275
    slip_factor: float = 1.6

    @property
    def effective_separation(self) -> float:
        return self.track_separation * self.slip_factor


def twist_to_tracks(v: float, w: float, geom: TrackGeometry, v_max: float) -> tuple[float, float]:
    """(v [m/s], w [rad/s]) -> velocidades de oruga izquierda/derecha, escaladas para no saturar."""
    b = geom.effective_separation
    vl = v - w * b / 2.0
    vr = v + w * b / 2.0
    m = max(abs(vl), abs(vr))
    if m > v_max > 0:
        k = v_max / m
        vl *= k
        vr *= k
    return vl, vr


def tracks_to_twist(vl: float, vr: float, geom: TrackGeometry) -> tuple[float, float]:
    return (vl + vr) / 2.0, (vr - vl) / geom.effective_separation


@dataclass
class Odometry:
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0

    def update(self, d_left: float, d_right: float, geom: TrackGeometry, yaw_override: float | None = None):
        """Integra desplazamientos de cada oruga [m]. Si hay IMU, `yaw_override` reemplaza el
        rumbo integrado (mucho más confiable en orugas, que patinan al girar)."""
        ds = (d_left + d_right) / 2.0
        dyaw = (d_right - d_left) / geom.effective_separation
        mid = self.yaw + dyaw / 2.0 if yaw_override is None else yaw_override
        self.x += ds * math.cos(mid)
        self.y += ds * math.sin(mid)
        self.yaw = wrap(self.yaw + dyaw) if yaw_override is None else wrap(yaw_override)
        return ds, dyaw


def wrap(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


def yaw_from_quat(w: float, x: float, y: float, z: float) -> float:
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def pitch_from_quat(w: float, x: float, y: float, z: float) -> float:
    s = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    return math.asin(s)


def quat_from_yaw(yaw: float) -> tuple[float, float, float, float]:
    """Devuelve (x, y, z, w)."""
    return 0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2)
