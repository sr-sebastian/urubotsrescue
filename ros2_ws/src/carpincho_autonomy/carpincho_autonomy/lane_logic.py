"""Lógica pura de la travesía autónoma de carriles (15 puntos por tramo vs 1 teleoperado).

Idea: los carriles de prueba son pasillos rectos con paredes. Mantenemos el centro del pasillo con
el LiDAR y el rumbo con el IMU, avanzamos la distancia del carril (pre-mapeado permitido fuera del
laberinto) o hasta ver el QR de la zona final, giramos 180° en la zona final y volvemos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def wrap(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


def sector_distance(ranges, angle_min, angle_inc, a0, a1, range_max=6.0, pct=0.2):
    """Distancia "robusta" (percentil bajo) de los rayos válidos entre a0 y a1 [rad]."""
    vals = []
    for i, r in enumerate(ranges):
        a = angle_min + i * angle_inc
        if a0 <= a <= a1 and 0.05 < r < range_max and math.isfinite(r):
            vals.append(r)
    if len(vals) < 3:
        return None
    vals.sort()
    return vals[int(pct * (len(vals) - 1))]


@dataclass
class LaneParams:
    lane_length: float = 4.8         # m entre zonas de inicio y fin (medir/pre-mapear)
    speed: float = 0.30              # m/s nominal
    slow_speed: float = 0.15         # en pendientes / escaleras
    k_lat: float = 1.5               # rad/s por m de error lateral
    k_head: float = 2.0              # rad/s por rad de error de rumbo
    max_w: float = 0.8
    wall_max: float = 1.0            # más lejos que esto = "no hay pared"
    front_stop: float = 0.25         # pared/puerta adelante: parar
    turn_tol: float = 0.08           # rad
    turn_w: float = 0.7
    traverses: int = 10              # ida+vuelta cuentan 2
    stuck_time: float = 4.0          # s sin progreso -> recuperar
    stuck_dist: float = 0.05
    max_recoveries: int = 3
    pitch_slow: float = math.radians(10)


@dataclass
class LaneState:
    state: str = "IDLE"
    lane_yaw: float = 0.0
    start_dist: float = 0.0
    traverses_done: int = 0
    progress_ref: float = 0.0
    progress_t: float = 0.0
    recover_until: float = 0.0
    recoveries: int = 0
    event: str = ""
    lateral_error: float = 0.0
    heading_error: float = 0.0
    seen_end_qr: bool = False
    history: list = field(default_factory=list)


class LaneTraverse:
    def __init__(self, p: LaneParams | None = None) -> None:
        self.p = p or LaneParams()
        self.s = LaneState()

    def start(self, yaw: float, dist: float, t: float) -> None:
        self.s = LaneState(state="OUTBOUND", lane_yaw=yaw, start_dist=dist, progress_ref=dist, progress_t=t,
                           event="inicio")

    def abort(self, why: str) -> None:
        self.s.state = "ABORT"
        self.s.event = why

    def end_qr(self) -> None:
        self.s.seen_end_qr = True

    def step(self, t: float, yaw: float, dist: float, pitch: float, left: float | None, right: float | None,
             front: float | None) -> tuple[float, float]:
        """Devuelve (v, w). `dist` = odometría acumulada (preferir LiDAR-odometría)."""
        p, s = self.p, self.s
        if s.state in ("IDLE", "DONE", "ABORT"):
            return 0.0, 0.0

        if s.state == "RECOVER":
            if t < s.recover_until:
                return -0.15, 0.0
            s.state = s.history[-1] if s.history else "OUTBOUND"
            s.progress_ref, s.progress_t = dist, t
            return 0.0, 0.0

        if s.state == "TURN":
            target = wrap(s.lane_yaw + math.pi)
            err = wrap(target - yaw)
            if abs(err) < p.turn_tol:
                s.lane_yaw = target
                s.state = "INBOUND"
                s.start_dist = dist
                s.seen_end_qr = False
                s.progress_ref, s.progress_t = dist, t
                s.event = "giro completo"
                return 0.0, 0.0
            return 0.0, math.copysign(min(p.turn_w, max(0.25, abs(err) * 1.5)), err)

        # OUTBOUND / INBOUND
        travelled = dist - s.start_dist
        if travelled >= p.lane_length or s.seen_end_qr or (front is not None and front < p.front_stop
                                                            and travelled > 0.6 * p.lane_length):
            s.traverses_done += 1
            s.event = f"zona final ({travelled:.2f} m)"
            if s.traverses_done >= p.traverses:
                s.state = "DONE"
                return 0.0, 0.0
            s.state = "TURN"
            return 0.0, 0.0

        # atasco
        if dist - s.progress_ref > p.stuck_dist:
            s.progress_ref, s.progress_t = dist, t
        elif t - s.progress_t > p.stuck_time:
            s.recoveries += 1
            if s.recoveries > p.max_recoveries:
                self.abort("atascado: pasar a teleoperación")
                return 0.0, 0.0
            s.history.append(s.state)
            s.state = "RECOVER"
            s.recover_until = t + 1.5
            s.event = f"recuperación {s.recoveries}"
            return 0.0, 0.0

        s.heading_error = wrap(yaw - s.lane_yaw)
        lat = 0.0
        if left is not None and right is not None and left < p.wall_max and right < p.wall_max:
            lat = (right - left) / 2.0           # >0: estamos corridos a la izquierda
        s.lateral_error = lat
        w = -p.k_lat * lat - p.k_head * s.heading_error
        w = max(-p.max_w, min(p.max_w, w))
        v = p.slow_speed if abs(pitch) > p.pitch_slow else p.speed
        if front is not None and front < p.front_stop:
            v = 0.0
        return v, w


# ---------------------------------------------------------------- flippers automáticos
@dataclass
class AutoFlipper:
    """Pose de flippers según el cabeceo (pitch > 0 = trompa arriba). Con histéresis."""

    flat: float = math.radians(20)
    climb: float = math.radians(-10)
    crest: float = math.radians(-35)
    descend: float = math.radians(-25)
    enter: float = math.radians(8)
    leave: float = math.radians(4)
    mode: str = "FLAT"

    def update(self, pitch: float, pitch_rate: float) -> float:
        m = self.mode
        if m == "FLAT":
            if pitch > self.enter:
                m = "CLIMB"
            elif pitch < -self.enter:
                m = "DESCEND"
        elif m == "CLIMB":
            if pitch_rate < -math.radians(15):        # la trompa cae rápido: coronando el escalón
                m = "CREST"
            elif pitch < self.leave:
                m = "FLAT"
        elif m == "CREST":
            if pitch < -self.enter:
                m = "DESCEND"
            elif abs(pitch) < self.leave and abs(pitch_rate) < math.radians(5):
                m = "FLAT"
        elif m == "DESCEND":
            if pitch > -self.leave:
                m = "FLAT"
        self.mode = m
        return {"FLAT": self.flat, "CLIMB": self.climb, "CREST": self.crest, "DESCEND": self.descend}[m]
