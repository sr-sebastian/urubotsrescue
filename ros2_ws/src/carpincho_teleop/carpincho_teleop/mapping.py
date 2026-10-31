"""Lógica de teleoperación (Python puro, testeable). Mapa por defecto: joystick tipo Xbox (xpad).

MODO MANEJO (por defecto)                     MODO BRAZO (botón BACK alterna)
  LB (mantener) = hombre muerto (OBLIGATORIO)   LB = hombre muerto
  stick izq. vertical  = avance                 stick izq.  = punta adelante/atrás, izq./der.
  stick der. horizontal = giro                  stick der. vertical = punta arriba/abajo
  RB + stick der. vertical = flipper (vel.)     stick der. horizontal = cabeceo de muñeca
  Y = flippers arriba (+60°, subir escalón)     cruceta izq./der. = giro de base (J1)
  B = flippers horizontales (0°)                cruceta arriba/abajo = giro de muñeca (J5)
  A = flippers abajo (-35°, levantar trompa)    LT / RT = cerrar / abrir pinza
  X = flippers de marcha (+15°)                 Y = guardar (stow)  X = listo (ready)
  cruceta arriba/abajo = velocidad (3 niveles)  A = inspeccionar frente  B = inspeccionar piso
  cruceta izq./der. = focos -/+
START = armar/desarmar motores    GUIDE = pedir modo autónomo (soltá todo después)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

AXES = dict(lx=0, ly=1, lt=2, rx=3, ry=4, rt=5, dx=6, dy=7)
BUTTONS = dict(a=0, b=1, x=2, y=3, lb=4, rb=5, back=6, start=7, guide=8, ls=9, rs=10)


@dataclass
class TeleopConfig:
    speeds: tuple = (0.12, 0.25, 0.40)        # m/s por nivel
    turn_rate: tuple = (0.5, 1.0, 1.6)        # rad/s por nivel
    deadzone: float = 0.12
    flipper_vel: float = 1.2                  # rad/s a fondo
    flipper_presets: dict = field(default_factory=lambda: {
        "y": math.radians(60), "b": 0.0, "a": math.radians(-35), "x": math.radians(15)})
    arm_lin: float = 0.12                     # m/s a fondo
    arm_ang: float = 0.8                      # rad/s a fondo
    arm_poses: dict = field(default_factory=lambda: {
        "y": "stow", "x": "ready", "a": "inspect_front", "b": "inspect_floor"})
    lights_step: int = 64
    axes: dict = field(default_factory=lambda: dict(AXES))
    buttons: dict = field(default_factory=lambda: dict(BUTTONS))
    triggers_rest_at_one: bool = True         # xpad: gatillos valen +1 sueltos y -1 apretados


@dataclass
class Output:
    v: float = 0.0
    w: float = 0.0
    flipper_vel: float | None = None
    flipper_pos: float | None = None
    arm_jog: tuple | None = None              # (vx, vy, vz, pitch_rate, base_rate, roll_rate)
    gripper: float | None = None
    named_pose: str | None = None
    toggle_enable: bool = False
    request_autonomy: bool = False
    lights: int | None = None
    mode_changed: bool = False


def dz(v: float, d: float) -> float:
    if abs(v) < d:
        return 0.0
    return math.copysign((abs(v) - d) / (1 - d), v)


class TeleopMapper:
    def __init__(self, cfg: TeleopConfig | None = None) -> None:
        self.cfg = cfg or TeleopConfig()
        self.mode = "drive"
        self.level = 1
        self.lights = 0
        self.grip = 0.0
        self._prev_buttons: list[int] = []
        self._prev_dpad = (0.0, 0.0)

    def _ax(self, axes, name) -> float:
        i = self.cfg.axes[name]
        return axes[i] if i < len(axes) else 0.0

    def _bt(self, buttons, name) -> bool:
        i = self.cfg.buttons[name]
        return i < len(buttons) and bool(buttons[i])

    def _pressed(self, buttons, name) -> bool:
        i = self.cfg.buttons[name]
        prev = self._prev_buttons[i] if i < len(self._prev_buttons) else 0
        return self._bt(buttons, name) and not prev

    def _trigger(self, axes, name) -> float:
        """0 suelto .. 1 a fondo."""
        v = self._ax(axes, name)
        return (1 - v) / 2 if self.cfg.triggers_rest_at_one else max(0.0, v)

    def update(self, axes: list[float], buttons: list[int]) -> Output:
        c = self.cfg
        out = Output()
        dead = self._bt(buttons, "lb")
        dx, dy = self._ax(axes, "dx"), self._ax(axes, "dy")
        dpad_edge = (dx if abs(dx) > 0.5 and abs(self._prev_dpad[0]) <= 0.5 else 0.0,
                     dy if abs(dy) > 0.5 and abs(self._prev_dpad[1]) <= 0.5 else 0.0)

        if self._pressed(buttons, "start"):
            out.toggle_enable = True
        if self._pressed(buttons, "guide"):
            out.request_autonomy = True
        if self._pressed(buttons, "back"):
            self.mode = "arm" if self.mode == "drive" else "drive"
            out.mode_changed = True

        if self.mode == "drive":
            if dpad_edge[1] > 0:
                self.level = min(len(c.speeds) - 1, self.level + 1)
            elif dpad_edge[1] < 0:
                self.level = max(0, self.level - 1)
            if dpad_edge[0] != 0:
                # en xpad la cruceta izquierda da +1
                self.lights = max(0, min(255, self.lights + (-1 if dpad_edge[0] > 0 else 1) * c.lights_step))
                out.lights = self.lights
            if dead:
                out.v = dz(self._ax(axes, "ly"), c.deadzone) * c.speeds[self.level]
                out.w = dz(self._ax(axes, "rx"), c.deadzone) * -c.turn_rate[self.level]
                if self._bt(buttons, "rb"):
                    out.flipper_vel = dz(self._ax(axes, "ry"), c.deadzone) * c.flipper_vel
                for b, ang in c.flipper_presets.items():
                    if self._pressed(buttons, b):
                        out.flipper_pos = ang
        else:  # brazo
            if dead:
                lx, ly = dz(self._ax(axes, "lx"), c.deadzone), dz(self._ax(axes, "ly"), c.deadzone)
                rx, ry = dz(self._ax(axes, "rx"), c.deadzone), dz(self._ax(axes, "ry"), c.deadzone)
                base = (1.0 if dx > 0.5 else -1.0 if dx < -0.5 else 0.0) * c.arm_ang * 0.5
                roll = (1.0 if dy > 0.5 else -1.0 if dy < -0.5 else 0.0) * c.arm_ang
                out.arm_jog = (ly * c.arm_lin, lx * c.arm_lin, ry * c.arm_lin, -rx * c.arm_ang, base, roll)
                close, opn = self._trigger(axes, "lt"), self._trigger(axes, "rt")
                if close > 0.1 or opn > 0.1:
                    self.grip = max(0.0, min(1.0, self.grip + (opn - close) * 0.04))
                    out.gripper = self.grip
                for b, name in c.arm_poses.items():
                    if self._pressed(buttons, b):
                        out.named_pose = name

        self._prev_buttons = list(buttons)
        self._prev_dpad = (dx, dy)
        return out
