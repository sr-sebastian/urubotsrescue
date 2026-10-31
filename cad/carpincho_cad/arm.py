"""Brazo manipulador C1: 5 GDL + pinza, servos Feetech STS3215 (bus serie TTL, 12 V).

Las piezas se modelan en "pose cero" (brazo vertical) en coordenadas del robot, y el
ensamble las ubica con una cadena cinemática (J1..J5) usando P.ARM_STOW.

Cadena: J1 giro base (Z) -> J2 hombro (Y, 2 servos + GT2 2:1) -> J3 codo (Y, GT2 2:1)
        -> J4 muñeca cabeceo (Y, directo) -> J5 muñeca giro (eje del antebrazo, directo)
        -> J6 pinza (servo, engranajes, apertura 0-105 mm).
"""

from __future__ import annotations

import cadquery as cq

from . import params as P
from .common import Part, Placement, rounded_box

AX = P.ARM_BASE_X
ZD = P.BODY_TOP_Z + P.DECK_T          # cara superior del deck
ZS = ZD + P.ARM_BASE_H                # eje del hombro (J2)
ZE = ZS + P.ARM_L1                    # eje del codo (J3)
ZW = ZE + P.ARM_L2                    # eje de la muñeca (J4)
SW, SD, SL = P.STS["w"], P.STS["d"], P.STS["l"]
CHEEK_Y = 32.0                        # cara interior de las mejillas del hombro
GT2_BIG_R = 40 * 2 / 3.14159 / 2      # radio primitivo GT2 40T (12.7 mm)
GT2_20_R = 20 * 2 / 3.14159 / 2


def servo_box(clear: float = 0.0) -> cq.Workplane:
    """STS3215 aprox. (45.2 x 24.7 x 35), horn en +Z a 11 mm de un extremo. Origen = eje del horn.
    Con clear > 0 devuelve el volumen a restar (bolsillo) con ese juego, sin el horn."""
    b = cq.Workplane("XY").box(SL + 2 * clear, SW + 2 * clear, SD + 2 * clear).translate((SL / 2 - 11.0, 0, -SD / 2))
    if clear:
        return b
    return b.union(cq.Workplane("XY").circle(10).extrude(4))


def servo_cut() -> cq.Workplane:
    """Bolsillo (0.4 mm de juego) + agujero para el horn y su tornillería (Ø24 x 12)."""
    b = servo_box(0.4)
    return b.union(cq.Workplane("XY").circle(12).extrude(12).translate((0, 0, -1)))


ZG = ZW + 85.0                        # centro de la base de la pinza (sobre el horn de J5)

# Ubicación de cada servo en pose cero: (nombre, nivel de la cadena, posición del horn, rotación)
# El nivel indica de qué articulación "cuelga" (0 fijo, 1 J1, 2 J2, 3 J3, 4 J4, 5 J5).
SERVOS = [
    ("J1", 0, (AX, 0.0, ZD + 36.5), (0.0, 0.0, 0.0)),
    ("J2a", 1, (AX - 25, 44.0, ZS - 30), (90.0, 0.0, 0.0)),      # horn hacia -Y (adentro), cuerpo afuera
    ("J2b", 1, (AX - 25, -44.0, ZS - 30), (-90.0, 0.0, 0.0)),
    ("J3", 2, (AX, 42.0, ZE - 55), (90.0, 0.0, 0.0)),
    ("J4", 3, (AX, SW / 2 + 0.5, ZW), (-90.0, 0.0, 0.0)),        # en línea con el antebrazo
    ("J5", 4, (AX, 0.0, ZW + 77), (0.0, 0.0, 0.0)),              # giro: horn hacia la pinza
    ("J6", 5, (AX + 34, 0.0, ZG + 4 + SD), (0.0, 0.0, 90.0)),    # pinza: al costado de los dedos
]


def _pocket(name: str, clear: float = 0.4) -> cq.Workplane:
    for n, _, pos, rot in SERVOS:
        if n == name:
            b = servo_cut() if clear == 0.4 else servo_box(clear)
            for axis, ang in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), rot):
                if ang:
                    b = b.rotate((0, 0, 0), axis, ang)
            return b.translate(pos)
    raise KeyError(name)


def _seat(name: str, wall: float = 3.0) -> cq.Workplane:
    """Caja que envuelve al servo con `wall` de pared (para unir a un soporte y después restar el bolsillo)."""
    return _pocket(name, clear=wall)


# ---------------------------------------------------------------------------
# Piezas (pose cero, coordenadas del robot)
# ---------------------------------------------------------------------------

def base() -> cq.Workplane:
    """AR-01: base fija atornillada al deck (6x M4 PCD 80). Aloja el servo J1 vertical."""
    h = 36.0
    b = cq.Workplane("XY").circle(55).extrude(h).translate((AX, 0, ZD))
    b = b.cut(cq.Workplane("XY").circle(47).extrude(h - 4).translate((AX, 0, ZD + 4)))
    b = b.union(_seat("J1").intersect(cq.Workplane("XY").circle(55).extrude(h).translate((AX, 0, ZD))))
    b = b.cut(_pocket("J1"))
    b = b.cut(cq.Workplane("XY").polarArray(40, 0, 360, 6).circle(2.2).extrude(4).translate((AX, 0, ZD)))
    b = b.cut(cq.Workplane("XY").center(AX - 30, 0).circle(10).extrude(4).translate((0, 0, ZD)))
    return b


def turret() -> cq.Workplane:
    """AR-02: torreta giratoria (J1) con mejillas del hombro y 2 servos J2 por fuera."""
    z0 = ZD + 38.0
    t = cq.Workplane("XY").circle(52).extrude(8).translate((AX, 0, z0))
    cheek = (cq.Workplane("XZ").center(AX, (z0 + 8 + ZS + 22) / 2).rect(70, ZS + 22 - z0 - 8)
             .extrude(-8).edges("|Y").fillet(6))
    for y0 in (CHEEK_Y, -CHEEK_Y - 8):
        t = t.union(cheek.translate((0, y0, 0)))
    t = t.cut(cq.Workplane("XZ").center(AX, ZS).circle(11).extrude(80, both=True))     # 608 del hombro
    for n in ("J2a", "J2b"):
        seat = _seat(n)
        # el asiento del servo baja hasta el disco de la torreta
        t = t.union(seat).cut(_pocket(n))
    t = t.cut(cq.Workplane("XY").circle(10.5).extrude(3).translate((AX, 0, z0)))          # rebaje del horn J1
    t = t.cut(cq.Workplane("XY").polarArray(7, 45, 360, 4).circle(1.6).extrude(8).translate((AX, 0, z0)))
    t = t.cut(cq.Workplane("XY").center(AX + 30, 0).rect(16, 30).extrude(8).translate((0, 0, z0)))
    return t


def shoulder_hub() -> cq.Workplane:
    """AR-03: cubo del hombro con 2 poleas GT2 40T integradas (por fuera de las mejillas)."""
    hub = cq.Workplane("XZ").center(AX, ZS).circle(16).extrude(CHEEK_Y - 1, both=True)
    for y0 in (CHEEK_Y + 8 + 1, -(CHEEK_Y + 8 + 1) - 7):
        hub = hub.union(cq.Workplane("XZ").center(AX, ZS).circle(GT2_BIG_R - 0.6).extrude(-7).translate((0, y0, 0)))
    # eje pasante de 8 mm: las poleas exteriores se fijan al eje con prisioneros, el eje al cubo con pasador
    sock = cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 4).extrude(35).translate((AX, 0, ZS + 8))
    hub = hub.union(sock)
    hub = hub.cut(cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 0.15).extrude(30).translate((AX, 0, ZS + 13)))
    hub = hub.cut(cq.Workplane("XZ").center(AX, ZS).circle(4.1).extrude(100, both=True))
    return hub


def tube(z0: float, z1: float) -> cq.Workplane:
    return (cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2).circle(P.ARM_TUBE_OD / 2 - 1).extrude(z1 - z0)
            .translate((AX, 0, z0)))


def elbow_lower() -> cq.Workplane:
    """AR-04: horquilla del codo (extremo del eslabón 1) con el servo J3 al costado."""
    zb = ZE - 70
    block = rounded_box(48, 2 * CHEEK_Y + 12, 30, 4).translate((AX, 0, zb + 15))
    block = block.cut(cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 0.15).extrude(25).translate((AX, 0, zb)))
    fork = cq.Workplane("XZ").center(AX, ZE - 20).rect(44, 60).extrude(-6).edges("|Y").fillet(5)
    for y0 in (CHEEK_Y - 10, -(CHEEK_Y - 10) - 6):      # horquilla angosta: la polea 40T va por fuera
        block = block.union(fork.translate((0, y0, 0)))
    block = block.cut(cq.Workplane("XZ").center(AX, ZE).circle(11).extrude(80, both=True))
    block = block.union(_seat("J3")).cut(_pocket("J3"))
    return block


def elbow_hub() -> cq.Workplane:
    """AR-05a: cubo del codo con polea GT2 40T (en el plano del horn de J3)."""
    hub = cq.Workplane("XZ").center(AX, ZE).circle(15).extrude(20, both=True)
    hub = hub.union(cq.Workplane("XZ").center(AX, ZE).circle(8).extrude(-12).translate((0, 20.0, 0)))   # eje a la polea
    hub = hub.union(cq.Workplane("XZ").center(AX, ZE).circle(GT2_BIG_R - 0.6).extrude(-6).translate((0, 32.0, 0)))
    sock = cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 4).extrude(32).translate((AX, 0, ZE + 8))
    hub = hub.union(sock)
    hub = hub.cut(cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 0.15).extrude(28).translate((AX, 0, ZE + 12)))
    hub = hub.cut(cq.Workplane("XZ").center(AX, ZE).circle(4.1).extrude(100, both=True))
    return hub


def wrist_mount() -> cq.Workplane:
    """AR-05b: soporte del servo J4 en el extremo del eslabón 2."""
    zb = ZW - 50
    m = rounded_box(34, 40, 24, 4).translate((AX, 0, zb))
    m = m.cut(cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 0.15).extrude(20).translate((AX, 0, zb - 12)))
    m = m.union(_seat("J4")).cut(_pocket("J4"))
    return m


def wrist_bracket() -> cq.Workplane:
    """AR-06: horquilla de muñeca (gira con J4) que lleva el servo de giro J5."""
    y_horn = SW / 2 + 0.5 + 4.0 + 1.0                     # lado del horn de J4 (+Y)
    y_idle = SD - (SW / 2 + 0.5) + 3.0 + 1.5              # lado opuesto: por fuera del asiento de J4
    side = rounded_box(50, 5, 64, 3)
    u = side.translate((AX, y_horn + 2.5, ZW + 18)).union(side.translate((AX, -(y_idle + 2.5), ZW + 18)))
    u = u.union(rounded_box(50, y_horn + y_idle + 5, 6, 3).translate((AX, (y_horn - y_idle) / 2, ZW + 47)))
    u = u.union(_seat("J5")).cut(_pocket("J5"))
    return u


def gripper() -> cq.Workplane:
    """AR-07: pinza de 2 dedos engranados (servo J6 al costado), apertura máx. 105 mm, cámara y Hall."""
    base_p = rounded_box(60, 44, 8, 4).translate((AX + 5, 0, ZG))
    fingers = None
    for s in (1, -1):
        f = (cq.Workplane("XZ").polyline([(0, 0), (8, 0), (6, 66), (-2, 66)]).close()
             .extrude(9, both=True).translate((AX + s * 12 - (0 if s > 0 else 6), 0, ZG + 4)))
        f = f.union(cq.Workplane("XY").box(4, 16, 36).translate((AX + s * 9, 0, ZG + 46)))
        fingers = f if fingers is None else fingers.union(f)
    j6 = _seat("J6").cut(_pocket("J6"))
    cam = rounded_box(26, 26, 14, 3).translate((AX - 32, 0, ZG + 18))      # cámara de pinza
    hall = cq.Workplane("XY").box(6, 10, 10).translate((AX, 0, ZW + P.ARM_L3 - 5))
    return base_p.union(fingers).union(j6).union(cam).union(hall)


# ---------------------------------------------------------------------------
# Ensamble
# ---------------------------------------------------------------------------

def chain_for(level: int, pose=P.ARM_STOW) -> tuple:
    """Rotaciones (distal primero) que se aplican a una pieza que cuelga del joint `level`.

    level: 0 base fija, 1 torreta (J1), 2 eslabón 1 (J2), 3 eslabón 2 (J3),
           4 muñeca (J4), 5 pinza (J5).
    """
    j1, j2, j3, j4, j5 = pose
    joints = [
        ((AX, 0, ZD), (0, 0, 1), j1),
        ((AX, 0, ZS), (0, 1, 0), j2),
        ((AX, 0, ZE), (0, 1, 0), j3),
        ((AX, 0, ZW), (0, 1, 0), j4),
        ((AX, 0, ZW), (0, 0, 1), j5),
    ]
    used = joints[:level]
    return tuple(reversed(used))


def parts(pose=P.ARM_STOW) -> list[Part]:
    pl = lambda lvl, tag="": [Placement(chain=chain_for(lvl, pose), tag=tag)]
    return [
        Part("AR-01", "Base del brazo", "brazo", base, "PLA-CF", "Impresión 3D PLA-CF 6 per. 50%", pl(0),
             notes="Rodamiento lazy-susan 4\" (100 mm) entre base y torreta."),
        Part("AR-02", "Torreta + mejillas del hombro", "brazo", turret, "PLA-CF", "Impresión 3D PLA-CF 6 per. 60%",
             pl(1), notes="2x 608-2RS eje hombro. 2 servos J2 en paralelo, GT2 20T->40T (2:1), correa cerrada GT2-6 de 140 mm."),
        Part("AR-03", "Cubo del hombro (2x GT2 40T)", "brazo", shoulder_hub, "PLA-CF",
             "Impresión 3D PLA-CF 100%", pl(2), notes="Eje 8 mm acero; tubo pegado con epoxi + pasador M3."),
        Part("AR-08", "Tubo eslabón 1 (CF 20x18)", "brazo", lambda: tube(ZS + 13, ZE - 70 + 25), "PLA-CF",
             "Tubo fibra de carbono 20x18 cortado (o Al 20x1)", pl(2), export=False, bought=True),
        Part("AR-04", "Codo inferior + servo J3", "brazo", elbow_lower, "PLA-CF", "Impresión 3D PLA-CF 6 per. 60%",
             pl(2), notes="GT2 20T (horn) -> 40T (cubo codo), correa cerrada GT2-6 ≈172 mm: ajustar la posición del servo al largo comercial que consigas."),
        Part("AR-05a", "Cubo del codo (GT2 40T)", "brazo", elbow_hub, "PLA-CF", "Impresión 3D PLA-CF 100%", pl(3)),
        Part("AR-09", "Tubo eslabón 2 (CF 20x18)", "brazo", lambda: tube(ZE + 12, ZW - 45 - 8), "PLA-CF",
             "Tubo fibra de carbono 20x18 cortado", pl(3), export=False, bought=True),
        Part("AR-05b", "Soporte servo muñeca J4", "brazo", wrist_mount, "PLA-CF", "Impresión 3D PLA-CF 50%", pl(3)),
        Part("AR-06", "Horquilla de muñeca + servo J5", "brazo", wrist_bracket, "PLA-CF",
             "Impresión 3D PLA-CF 50%", pl(4)),
        Part("AR-07", "Pinza (dedos engranados) + cámara + Hall", "brazo", gripper, "PETG",
             "Impresión 3D PETG 40%; almohadillas TPU", pl(5),
             notes="Ranura en V en los dedos para tomar el eje de 6 mm de la herramienta (tarea INSERT)."),
        Part("REF-SV", "Servo Feetech STS3215 12 V (x7)", "referencia", servo_box, "motor", "Comprado",
             [Placement(pos=pos, rot=rot, chain=chain_for(lvl, pose), tag=n) for n, lvl, pos, rot in SERVOS],
             export=False, bought=True),
    ]
