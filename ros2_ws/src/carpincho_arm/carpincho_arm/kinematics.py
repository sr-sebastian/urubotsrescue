"""Cinemática del brazo C1 (5 GDL). Python puro.

Convenciones (coinciden con cad/carpincho_cad/arm.py y el URDF):
  - Frame arm_base_link: centro del eje J1 sobre el deck, X adelante, Z arriba.
  - J1 gira en Z. J2, J3, J4 cabecean en Y; ángulo 0 = eslabón vertical, positivo = hacia adelante.
  - J5 gira sobre el eje de la herramienta (no afecta la posición de la punta).
  - "pitch" de la herramienta = θ2+θ3+θ4 medido desde la vertical (π/2 = horizontal hacia adelante,
    π = apuntando al piso).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class ArmGeometry:
    h0: float = 0.085      # altura del eje J2 sobre arm_base_link [m]
    l1: float = 0.260
    l2: float = 0.240
    l3: float = 0.155      # muñeca -> punta de herramienta (centro de los dedos)
    limits: dict = field(default_factory=lambda: {
        "j1": (-math.radians(170), math.radians(170)),
        "j2": (-math.radians(90), math.radians(85)),
        "j3": (-math.radians(5), math.radians(140)),
        "j4": (-math.radians(100), math.radians(100)),
        "j5": (-math.pi, math.pi),
    })


def fk(q: list[float], g: ArmGeometry) -> tuple[float, float, float, float]:
    """q = [j1..j5] -> (x, y, z, pitch) de la punta en arm_base_link."""
    j1, j2, j3, j4 = q[:4]
    a2 = j2
    a3 = j2 + j3
    a4 = j2 + j3 + j4
    r = g.l1 * math.sin(a2) + g.l2 * math.sin(a3) + g.l3 * math.sin(a4)
    z = g.h0 + g.l1 * math.cos(a2) + g.l2 * math.cos(a3) + g.l3 * math.cos(a4)
    return r * math.cos(j1), r * math.sin(j1), z, a4


class Unreachable(ValueError):
    pass


def ik(x: float, y: float, z: float, pitch: float, g: ArmGeometry, elbow_up: bool = True,
       j5: float = 0.0, check_limits: bool = True) -> list[float]:
    """Punta en (x, y, z) con la herramienta a `pitch` -> [j1..j5]. Lanza Unreachable."""
    j1 = math.atan2(y, x) if (abs(x) > 1e-9 or abs(y) > 1e-9) else 0.0
    r = math.hypot(x, y)
    rw = r - g.l3 * math.sin(pitch)
    zw = z - g.l3 * math.cos(pitch) - g.h0
    d2 = rw * rw + zw * zw
    c3 = (d2 - g.l1 ** 2 - g.l2 ** 2) / (2 * g.l1 * g.l2)
    if c3 > 1 + 1e-9 or c3 < -1 - 1e-9:
        raise Unreachable(f"fuera de alcance (muñeca a {math.sqrt(d2):.3f} m)")
    c3 = max(-1.0, min(1.0, c3))
    j3 = math.acos(c3)
    if not elbow_up:
        j3 = -j3
    alpha = math.atan2(rw, zw)                               # ángulo desde la vertical
    beta = math.atan2(g.l2 * math.sin(j3), g.l1 + g.l2 * math.cos(j3))
    j2 = alpha - beta
    j4 = pitch - j2 - j3
    q = [j1, j2, j3, _wrap(j4), j5]
    if check_limits:
        for name, v in zip(("j1", "j2", "j3", "j4", "j5"), q):
            lo, hi = g.limits[name]
            if v < lo - 1e-6 or v > hi + 1e-6:
                raise Unreachable(f"{name}={math.degrees(v):.0f}° fuera de límites")
    return q


def _wrap(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


def clamp_joints(q: list[float], g: ArmGeometry) -> list[float]:
    out = []
    for name, v in zip(("j1", "j2", "j3", "j4", "j5"), q):
        lo, hi = g.limits[name]
        out.append(min(hi, max(lo, v)))
    return out


def interpolate(q0: list[float], q1: list[float], n: int) -> list[list[float]]:
    """Trayectoria articular con perfil coseno (arranque y frenado suaves)."""
    pts = []
    for i in range(1, n + 1):
        s = 0.5 - 0.5 * math.cos(math.pi * i / n)
        pts.append([a + (b - a) * s for a, b in zip(q0, q1)])
    return pts


def static_torques(q: list[float], g: ArmGeometry, m_link1=0.35, m_link2=0.30, m_wrist=0.30,
                   payload=0.2) -> tuple[float, float]:
    """Torque estático [N·m] en J2 y J3 por gravedad (para chequear servos y reducciones)."""
    gr = 9.81
    _, j2, j3, j4 = q[:4]
    a2, a3, a4 = j2, j2 + j3, j2 + j3 + j4
    x_l1 = g.l1 / 2 * math.sin(a2)
    x_e = g.l1 * math.sin(a2)
    x_l2 = x_e + g.l2 / 2 * math.sin(a3)
    x_w = x_e + g.l2 * math.sin(a3)
    x_tip = x_w + g.l3 * math.sin(a4)
    t2 = gr * (m_link1 * x_l1 + m_link2 * x_l2 + m_wrist * (x_w + x_tip) / 2 + payload * x_tip)
    t3 = gr * (m_link2 * (x_l2 - x_e) + m_wrist * ((x_w + x_tip) / 2 - x_e) + payload * (x_tip - x_e))
    return t2, t3
