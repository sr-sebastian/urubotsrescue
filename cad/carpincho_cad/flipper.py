"""Flippers delanteros: brazos, cubos, alojamientos de rodamiento y sensor de ángulo."""

from __future__ import annotations

import math

import cadquery as cq

from . import params as P
from .common import Part, Placement, gear_simple
from .drivetrain import flipper_tip_pulley

XF = P.AXLE_DIST / 2
ZA = P.AXLE_Z
L = P.FLIP_LEN
ROT_Y = (-90.0, 0.0, 0.0)
HUB_PCD = 50.0
SENSOR_Y = 40.0            # plano del engranaje del sensor sobre el tubo
GEAR_M = 1.0
GEAR_T = 40                # 1:1 -> el AS5600 lee el ángulo real del flipper


def flipper_arm() -> cq.Workplane:
    """FL-01: brazo de flipper Al 5 mm. Pivote en el origen, punta en +X (plano XZ)."""
    t = P.FLIP_PLATE_T
    sk = cq.Sketch().arc((0, 0), 42.0, 0, 360).arc((L, 0), 20.0, 0, 360).hull()
    pl = cq.Workplane("XZ").placeSketch(sk).extrude(-t)
    pl = pl.cut(cq.Workplane("XZ").circle(P.FLIP_TUBE_OD / 2 + 0.2).extrude(-t))
    pl = pl.cut(cq.Workplane("XZ").polarArray(HUB_PCD / 2, 45, 360, 4).circle(2.75).extrude(-t))
    # ranura de tensado del eje de punta (±5 mm)
    pl = pl.cut(cq.Workplane("XZ").center(L, 0).slot2D(10 + P.FLIP_TIP_AXLE_D + 0.4,
                                                    P.FLIP_TIP_AXLE_D + 0.4, 0).extrude(-t))
    # tornillo tensor M4 axial
    pl = pl.cut(cq.Workplane("YZ", origin=(L - 45, -t / 2, 0)).circle(1.7).extrude(30))
    # alivianado
    pl = pl.cut(cq.Workplane("XZ").pushPoints([(85, 0), (160, 0)]).slot2D(55, 22, 0).extrude(-t))
    return pl


def flipper_hub() -> cq.Workplane:
    """FL-02: cubo de flipper (Al 6061 torneado o PLA-CF 100%). Pasador M5 a través del tubo."""
    h = P.FLIP_HUB_T
    hub = cq.Workplane("XY").circle(36).extrude(h)
    hub = hub.cut(cq.Workplane("XY").circle(P.FLIP_TUBE_OD / 2 + 0.1).extrude(h))
    hub = hub.cut(cq.Workplane("XY").polarArray(HUB_PCD / 2, 45, 360, 4).circle(2.75).extrude(h))
    hub = hub.cut(cq.Workplane("YZ", origin=(-40, 0, h / 2)).circle(2.75).extrude(80))
    return hub


def bearing_housing() -> cq.Workplane:
    """FL-05: alojamiento de rodamiento 6804 (32x20x7) para la placa lateral. Eje en +Z."""
    fl = cq.Workplane("XY").circle(31).extrude(4)
    boss = cq.Workplane("XY").circle(21).extrude(9).translate((0, 0, 4))
    h = fl.union(boss)
    # bajo: el eje está a 58 mm del piso y el piso del cuerpo a 33 -> brida recortada abajo
    flat = -(P.AXLE_Z - P.BODY_BOTTOM_Z - P.FLOOR_T - 1.0)
    h = h.cut(cq.Workplane("XY").center(0, flat - 30).rect(80, 60).extrude(13))
    h = h.cut(cq.Workplane("XY").circle(16.0).extrude(13).translate((0, 0, 4 - 0.01)))   # asiento 7 + juego
    h = h.cut(cq.Workplane("XY").circle(12.0).extrude(4))
    h = h.cut(cq.Workplane("XY").polarArray(23, 90, 360, 3).circle(2.2).extrude(4))
    # el rodamiento se apoya en el escalón; luego retén con arandela M4 grande
    return h


def sensor_gear_tube() -> cq.Workplane:
    """FL-04a: engranaje 40T m1 partido (abrazadera) sobre el tubo de flipper."""
    g = gear_simple(GEAR_T, GEAR_M, 8.0, P.FLIP_TUBE_OD)
    g = g.cut(cq.Workplane("XY").center(0, 0).rect(1.5, 50).extrude(8).translate((0, 25 + 9, 0)))
    return g


def sensor_gear_magnet() -> cq.Workplane:
    """FL-04b: engranaje 40T m1 con eje integrado ø5 y alojamiento de imán diametral 6x2.5."""
    g = gear_simple(GEAR_T, GEAR_M, 8.0, 0.1)
    st = cq.Workplane("XY").circle(2.5).extrude(18).translate((0, 0, 8))
    head = cq.Workplane("XY").circle(5).extrude(3).translate((0, 0, 26))
    head = head.cut(cq.Workplane("XY").circle(3.05).extrude(2.6).translate((0, 0, 26.4)))
    return g.union(st).union(head)


def sensor_bracket() -> cq.Workplane:
    """FL-04c: soporte de sensor AS5600 (PETG). Va atornillado al piso."""
    t = 5.0
    zc = 2 * GEAR_T * GEAR_M / 2          # distancia entre centros 40 mm
    zfloor = -(ZA - P.BODY_BOTTOM_Z - P.FLOOR_T)
    plate = cq.Workplane("XZ").polyline([(-30, zfloor), (30, zfloor), (25, zc + 15), (-25, zc + 15)]).close() \
        .extrude(-t)
    plate = plate.cut(cq.Workplane("XZ").circle(P.FLIP_TUBE_OD / 2 + 6).extrude(-t))
    plate = plate.cut(cq.Workplane("XZ").center(0, zc).circle(5.0).extrude(-t))           # 2x MR105 (5x10x4)
    plate = plate.cut(cq.Workplane("XZ").center(0, zc).circle(2.6).extrude(-t))
    foot = cq.Workplane("XY").box(60, 30, t).translate((0, t + 15 - t, zfloor + t / 2))
    foot = foot.cut(cq.Workplane("XY").pushPoints([(-20, 15), (20, 15)]).circle(2.2).extrude(t)
                    .translate((0, 0, zfloor)))
    # postes para el PCB del AS5600 (agujeros M2 a 16 mm, típico del módulo)
    posts = cq.Workplane("XZ").pushPoints([(-8, zc - 8), (8, zc + 8)]).circle(2.5).extrude(-(t + 9))
    posts = posts.cut(cq.Workplane("XZ").pushPoints([(-8, zc - 8), (8, zc + 8)]).circle(0.9).extrude(-(t + 9)))
    return plate.union(foot).union(posts)


def tip_axle() -> cq.Workplane:
    return cq.Workplane("XY").circle(P.FLIP_TIP_AXLE_D / 2).extrude(50)


def _tip(angle):
    a = math.radians(angle)
    return XF + L * math.cos(a), ZA + L * math.sin(a)


def parts(angle: float = P.FLIP_ANGLE_STOW) -> list[Part]:
    lr = lambda pos, rot=(0, 0, 0): [Placement(pos, rot, tag="L"), Placement(pos, rot, mirror_y=True, tag="R")]
    tx, tz = _tip(angle)
    y_tip0 = P.Y_TRACK_OUT + P.GAP_PLATE_PULLEY
    return [
        Part("FL-01", "Brazo de flipper", "flipper", flipper_arm, "Al", "Corte láser/agua Al 6061 5 mm",
             lr((XF, P.Y_FLIP_PLATE_IN, ZA), (0, -angle, 0)), dxf=True),
        Part("FL-02", "Cubo de flipper", "flipper", flipper_hub, "Al",
             "Torno Al 6061 (o PLA-CF 100% para prototipo)",
             lr((XF, P.Y_FLIP_PLATE_IN + P.FLIP_PLATE_T, ZA), ROT_Y),
             notes="Pasador: bulón M5x80 12.9 a través de cubo y tubo; 4x M5x20 al brazo."),
        Part("DT-04", "Polea punta de flipper 36T", "flipper", flipper_tip_pulley, "PLA-CF",
             "Impresión 3D PLA-CF, 5 perímetros, 50%", lr((tx, y_tip0, tz), ROT_Y),
             notes="2x rodamiento 6900-2RS, eje bulón M10x60 8.8."),
        Part("FL-05", "Alojamiento rodamiento 6804", "flipper", bearing_housing, "PLA-CF",
             "Impresión 3D PLA-CF 100%", lr((XF, P.Y_SIDE_IN, ZA), (90, 0, 0))),
        Part("FL-04a", "Engranaje 40T sensor (sobre tubo)", "flipper", sensor_gear_tube, "PETG",
             "Impresión 3D PETG 100%, abrazadera M3", [Placement((XF, SENSOR_Y, ZA), ROT_Y)]),
        Part("FL-04b", "Engranaje 40T con imán (AS5600)", "flipper", sensor_gear_magnet, "PETG",
             "Impresión 3D PETG 100%", [Placement((XF, SENSOR_Y, ZA + 40.0), ROT_Y)],
             notes="Imán diametral 6x2.5 mm (viene con el módulo AS5600)."),
        Part("FL-04c", "Soporte sensor de ángulo", "flipper", sensor_bracket, "PETG", "Impresión 3D PETG 40%",
             [Placement((XF, SENSOR_Y + 10, ZA))]),
        Part("REF-F1", "Eje de punta M10", "flipper", tip_axle, "steel", "Bulón M10x60 8.8",
             lr((tx, y_tip0 - 3, tz), ROT_Y), export=False, bought=True),
    ]
