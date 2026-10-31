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


def servo_box() -> cq.Workplane:
    """STS3215 aprox. (45.2 x 24.7 x 35), horn en +Z a 11 mm de un extremo. Origen = eje del horn."""
    b = cq.Workplane("XY").box(SL, SW, SD).translate((SL / 2 - 11.0, 0, -SD / 2))
    horn = cq.Workplane("XY").circle(10).extrude(4)
    return b.union(horn)


def _servo_pocket(at, axis="Y"):
    """Volumen para restar donde va un servo (con 0.4 mm de juego)."""
    b = cq.Workplane("XY").box(SL + 0.8, SW + 0.8, SD + 0.8).translate((SL / 2 - 11.0, 0, -SD / 2))
    if axis == "Y":
        b = b.rotate((0, 0, 0), (1, 0, 0), -90)
    return b.translate(at)


# ---------------------------------------------------------------------------
# Piezas (pose cero, coordenadas del robot)
# ---------------------------------------------------------------------------

def base() -> cq.Workplane:
    """AR-01: base fija atornillada al deck (6x M4 PCD 80). Aloja el servo J1 vertical."""
    h = 36.0
    b = cq.Workplane("XY").circle(55).extrude(h).translate((AX, 0, ZD))
    b = b.cut(cq.Workplane("XY").circle(47).extrude(h - 4).translate((AX, 0, ZD + 4)))
    b = b.union(rounded_box(SL + 8, SW + 8, SD - 4, 3).translate((AX + SL / 2 - 11, 0, ZD + h - (SD - 4) / 2)))
    b = b.cut(_servo_pocket((AX, 0, ZD + h + 0.5), axis="Z"))
    b = b.cut(cq.Workplane("XY").polarArray(40, 0, 360, 6).circle(2.2).extrude(4).translate((AX, 0, ZD)))
    b = b.cut(cq.Workplane("XY").circle(14).extrude(4).translate((AX, 0, ZD)))
    return b


def turret() -> cq.Workplane:
    """AR-02: torreta giratoria (J1) con mejillas del hombro y 2 servos J2."""
    z0 = ZD + 38.0
    disc = cq.Workplane("XY").circle(52).extrude(8).translate((AX, 0, z0))
    cheek = (cq.Workplane("XZ").center(AX, (z0 + 8 + ZS + 22) / 2).rect(70, ZS + 22 - z0 - 8)
             .extrude(-8).edges("|Y").fillet(6))
    t = disc
    for s in (1, -1):
        c = cheek.translate((0, CHEEK_Y if s > 0 else -CHEEK_Y - 8, 8 * 0))
        t = t.union(c)
    # rodamientos 608 del eje del hombro en las mejillas
    t = t.cut(cq.Workplane("XZ").center(AX, ZS).circle(11).extrude(80, both=True))
    # bolsillos de servos J2 (horn hacia afuera, debajo y atrás del hombro)
    for s in (1, -1):
        t = t.union(rounded_box(SL + 8, SD + 6, SW + 8, 3).translate(
            (AX - 25 + SL / 2 - 11, s * (CHEEK_Y + 8 + SD / 2 - 2), ZS - 30)))
    # acople al horn de J1 (4x M3) + paso de cables
    t = t.cut(cq.Workplane("XY").polarArray(7, 45, 360, 4).circle(1.6).extrude(8).translate((AX, 0, z0)))
    t = t.cut(cq.Workplane("XY").center(AX - 30, 0).rect(16, 30).extrude(8).translate((0, 0, z0)))
    return t


def shoulder_hub() -> cq.Workplane:
    """AR-03: cubo del hombro con 2 poleas GT2 40T integradas y encastre del tubo de Ø20."""
    w = 2 * CHEEK_Y - 2
    hub = cq.Workplane("XZ").center(AX, ZS).circle(16).extrude(w / 2, both=True)
    for s in (1, -1):
        pul = (cq.Workplane("XZ").center(AX, ZS).circle(GT2_BIG_R - 0.6).extrude(7)
               .translate((0, s * (CHEEK_Y + 8 + 4) + (7 if s > 0 else 0) * 0, 0)))
        hub = hub.union(pul.translate((0, 3.5 if s > 0 else -3.5 + 7, 0)))
    sock = cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 4).extrude(35).translate((AX, 0, ZS + 8))
    hub = hub.union(sock)
    hub = hub.cut(cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 0.15).extrude(30).translate((AX, 0, ZS + 13)))
    hub = hub.cut(cq.Workplane("XZ").center(AX, ZS).circle(4.1).extrude(100, both=True))
    return hub


def tube(z0: float, z1: float) -> cq.Workplane:
    return (cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2).circle(P.ARM_TUBE_OD / 2 - 1).extrude(z1 - z0)
            .translate((AX, 0, z0)))


def elbow_lower() -> cq.Workplane:
    """AR-04: horquilla del codo (extremo del eslabón 1) con servo J3 y rodamientos 608."""
    zb = ZE - 70
    block = rounded_box(48, 2 * CHEEK_Y + 12, 30, 4).translate((AX, 0, zb + 15))
    block = block.cut(cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 0.15).extrude(30).translate((AX, 0, zb - 5)))
    fork = cq.Workplane("XZ").center(AX, ZE - 20).rect(44, 60).extrude(-6).edges("|Y").fillet(5)
    for s in (1, -1):
        block = block.union(fork.translate((0, (CHEEK_Y - 2) if s > 0 else -(CHEEK_Y + 4), 0)))
    block = block.cut(cq.Workplane("XZ").center(AX, ZE).circle(11).extrude(80, both=True))
    # servo J3 a un costado, horn hacia +Y
    block = block.union(rounded_box(SL + 6, SD + 4, SW + 6, 3).translate(
        (AX + SL / 2 - 11, CHEEK_Y + 4 + SD / 2, zb + 15)))
    return block


def elbow_hub() -> cq.Workplane:
    """AR-05a: cubo del codo con polea GT2 40T, encastre del tubo del eslabón 2."""
    w = 2 * CHEEK_Y - 6
    hub = cq.Workplane("XZ").center(AX, ZE).circle(15).extrude(w / 2, both=True)
    pul = cq.Workplane("XZ").center(AX, ZE).circle(GT2_BIG_R - 0.6).extrude(-7).translate((0, CHEEK_Y + 6, 0))
    hub = hub.union(pul)
    sock = cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 4).extrude(32).translate((AX, 0, ZE + 8))
    hub = hub.union(sock)
    hub = hub.cut(cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 0.15).extrude(28).translate((AX, 0, ZE + 12)))
    hub = hub.cut(cq.Workplane("XZ").center(AX, ZE).circle(4.1).extrude(100, both=True))
    return hub


def wrist_mount() -> cq.Workplane:
    """AR-05b: soporte del servo J4 en el extremo del eslabón 2."""
    zb = ZW - 45
    m = rounded_box(34, 40, 34, 4).translate((AX, 0, zb))
    m = m.cut(cq.Workplane("XY").circle(P.ARM_TUBE_OD / 2 + 0.15).extrude(25).translate((AX, 0, zb - 17)))
    m = m.union(rounded_box(SD + 6, SW + 6, SL + 6, 3).translate((AX, 0, ZW - 11 + SL / 2 - SL / 2 - 4)))
    m = m.cut(_servo_pocket((AX, -SW / 2 - 0.5 + 12.5, ZW), axis="Y").rotate((AX, 0, ZW), (AX, 1, ZW), 90))
    return m


def wrist_bracket() -> cq.Workplane:
    """AR-06: horquilla de muñeca (J4) que lleva el servo de giro J5 alineado con la herramienta."""
    u = cq.Workplane("XY").box(46, 6, 40).translate((AX, SW / 2 + 10, ZW + 8))
    u = u.union(cq.Workplane("XY").box(46, 6, 40).translate((AX, -SW / 2 - 10, ZW + 8)))
    u = u.union(cq.Workplane("XY").box(46, SW + 26, 6).translate((AX, 0, ZW + 31)))
    u = u.union(rounded_box(SW + 6, SD + 6, 18, 3).translate((AX, 0, ZW + 43)))
    return u


def gripper() -> cq.Workplane:
    """AR-07: pinza de 2 dedos engranados (servo J6), apertura máx. 105 mm, cámara y Hall."""
    zg = ZW + 55
    base_p = rounded_box(60, 40, 8, 4).translate((AX, 0, zg))
    servo_mount = rounded_box(SL + 6, SW + 6, 12, 3).translate((AX, 0, zg + 10))
    fingers = None
    for s in (1, -1):
        f = (cq.Workplane("XZ").polyline([(0, 0), (8, 0), (6, 80), (-2, 80)]).close()
             .extrude(9, both=True).translate((AX + s * 12 - (0 if s > 0 else 6), 0, zg + 4)))
        pad = cq.Workplane("XY").box(4, 16, 40).translate((AX + s * 9, 0, zg + 60))
        f = f.union(pad)
        fingers = f if fingers is None else fingers.union(f)
    cam = rounded_box(26, 26, 14, 3).translate((AX - 32, 0, zg + 20))      # cámara de pinza
    hall = cq.Workplane("XY").box(6, 10, 14).translate((AX, 0, zg + 84))    # sensor Hall en la punta
    return base_p.union(servo_mount).union(fingers).union(cam).union(hall)


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
             [Placement(pos=(AX, 0, ZD + 36.5), chain=chain_for(0, pose)),
              Placement(pos=(AX - 25, CHEEK_Y + 8 + 2, ZS - 30), rot=(-90, 0, 0), chain=chain_for(1, pose)),
              Placement(pos=(AX - 25, -(CHEEK_Y + 8 + 2), ZS - 30), rot=(90, 0, 0), chain=chain_for(1, pose)),
              Placement(pos=(AX, CHEEK_Y + 6, ZE - 55), rot=(-90, 0, 0), chain=chain_for(2, pose)),
              Placement(pos=(AX, SW / 2 + 0.5, ZW), rot=(-90, 0, 0), chain=chain_for(3, pose)),
              Placement(pos=(AX, 0, ZW + 52), rot=(180, 0, 0), chain=chain_for(4, pose)),
              Placement(pos=(AX, 0, ZW + 72), rot=(0, 0, 90), chain=chain_for(5, pose))],
             export=False, bought=True),
    ]
