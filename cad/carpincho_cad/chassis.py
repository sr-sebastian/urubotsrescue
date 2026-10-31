"""Chasis: placas laterales, placas exteriores de oruga, piso, deck, mamparos, asas."""

from __future__ import annotations

import cadquery as cq

from . import params as P
from .common import Part, Placement

XR, XF = -P.AXLE_DIST / 2, P.AXLE_DIST / 2
ZA = P.AXLE_Z
HALF = P.BODY_LEN / 2

# posiciones (x, z) de separadores entre placa lateral y placa exterior (dentro del lazo)
STANDOFFS_XZ = [(-150.0, 80.0), (-55.0, 82.0), (50.0, 82.0), (130.0, 80.0)]
# filas de agujeros M4 para escuadras de piso/deck
ANGLE_X = [-200.0, -120.0, -40.0, 40.0, 120.0, 200.0]
Z_FLOOR_HOLES = P.BODY_BOTTOM_Z + P.FLOOR_T + 7.0
Z_DECK_HOLES = P.BODY_TOP_Z - 7.0
KFL_SPACING = 48.0          # rodamiento con brida KFL001 (eje 12): 2 agujeros M6 a 48 mm
HOUSING_PCD = 46.0          # alojamiento 6804 (FL-05): 3x M4


def _side_outline():
    z0, z1 = P.BODY_BOTTOM_Z, P.BODY_TOP_Z
    c = 35.0   # chaflanes inferiores (ángulo de ataque)
    return [(-HALF, z0 + c), (-HALF + c, z0), (HALF - c, z0), (HALF, z0 + c), (HALF, z1), (-HALF, z1)]


def side_plate() -> cq.Workplane:
    """CH-01: placa lateral Al 4 mm (corte láser/agua). Modelada del lado izquierdo (y>0)."""
    t = P.SIDE_PLATE_T
    pl = cq.Workplane("XZ").polyline(_side_outline()).close().extrude(-t)

    def cut(pts, d):
        nonlocal pl
        pl = pl.cut(cq.Workplane("XZ").pushPoints(pts).circle(d / 2).extrude(-t))

    cut([(XR, ZA)], 30.0)                                                 # eje motriz
    cut([(XR, ZA + KFL_SPACING / 2), (XR, ZA - KFL_SPACING / 2)], 6.6)    # KFL001
    cut([(XF, ZA)], 34.0)                                                 # tubo flipper
    import math
    cut([(XF + HOUSING_PCD / 2 * math.cos(math.radians(a)), ZA + HOUSING_PCD / 2 * math.sin(math.radians(a)))
         for a in (90, 210, 330)], 4.4)
    cut([(x, P.ROLLER_Z) for x in P.ROLLER_X], 8.4)                       # ejes de rodillos M8
    cut(STANDOFFS_XZ, 5.4)                                                # separadores M5
    cut([(x, Z_FLOOR_HOLES) for x in ANGLE_X] + [(x, Z_DECK_HOLES) for x in ANGLE_X], 4.4)
    # bulkheads (M4 verticales)
    cut([(HALF - 10, z) for z in (80, 150)] + [(-HALF + 10, z) for z in (80, 150)], 4.4)
    # alivianado + pasacables
    pl = pl.cut(cq.Workplane("XZ").pushPoints([(-95, 140), (5, 140), (95, 140)])
                .slot2D(70, 34, 0).extrude(-t))
    return pl


def outer_plate() -> cq.Workplane:
    """CH-02: placa exterior de oruga Al 3 mm (lado izquierdo). Termina antes de la polea delantera."""
    t = P.OUTER_PLATE_T
    x_end = XF - P.TRACK_PD / 2 - 12
    pts = [(-HALF + 5, 45), (-HALF + 20, 30), (x_end - 20, 30), (x_end, 50),
           (x_end, 98), (x_end - 15, 112), (-HALF + 20, 112), (-HALF + 5, 98)]
    pl = cq.Workplane("XZ").polyline(pts).close().extrude(-t)
    pl = pl.cut(cq.Workplane("XZ").pushPoints([(XR, ZA)]).circle(15).extrude(-t))
    pl = pl.cut(cq.Workplane("XZ").pushPoints([(XR, ZA + 24), (XR, ZA - 24)]).circle(3.3).extrude(-t))
    pl = pl.cut(cq.Workplane("XZ").pushPoints([(x, P.ROLLER_Z) for x in P.ROLLER_X]).circle(4.2).extrude(-t))
    pl = pl.cut(cq.Workplane("XZ").pushPoints(STANDOFFS_XZ).circle(2.7).extrude(-t))
    pl = pl.cut(cq.Workplane("XZ").pushPoints([(-100, 75), (0, 60)]).slot2D(50, 20, 0).extrude(-t))
    return pl


def floor_plate() -> cq.Workplane:
    """CH-03: piso Al 3 mm entre placas laterales."""
    t = P.FLOOR_T
    w = P.BODY_INNER_W - 1.0
    pl = cq.Workplane("XY").rect(P.BODY_LEN - 2 * 35 + 20, w).extrude(t)
    pl = pl.cut(cq.Workplane("XY").pushPoints([(x, y) for x in ANGLE_X[1:-1] for y in (w / 2 - 10, -w / 2 + 10)])
                .circle(2.2).extrude(t))
    # ranuras de correas de batería y drenaje
    bx = P.BATTERY["pos"][0]
    pl = pl.cut(cq.Workplane("XY").pushPoints([(bx, 50), (bx, -50)]).slot2D(30, 5, 0).extrude(t))
    pl = pl.cut(cq.Workplane("XY").pushPoints([(-180, 0), (180, 0)]).circle(4).extrude(t))
    return pl


def deck_plate() -> cq.Workplane:
    """CH-04: deck superior (Al 3 mm o policarbonato 4 mm) apoyado sobre las placas laterales."""
    t = P.DECK_T
    w = 2 * P.Y_SIDE_OUT
    pl = cq.Workplane("XY").rect(P.BODY_LEN, w).extrude(t)
    pl = pl.edges("|Z").fillet(8)
    # base del brazo (PCD 80, 6x M4) + paso de cables ø30
    import math
    ax = P.ARM_BASE_X
    pl = pl.cut(cq.Workplane("XY").pushPoints(
        [(ax + 40 * math.cos(math.radians(a)), 40 * math.sin(math.radians(a))) for a in range(0, 360, 60)])
        .circle(2.2).extrude(t))
    pl = pl.cut(cq.Workplane("XY").pushPoints([(ax, 0)]).circle(15).extrude(t))
    # mástil LiDAR (4x M5 cuadrado 40) + ø20 cables
    lx = P.LIDAR_POS[0]
    pl = pl.cut(cq.Workplane("XY").pushPoints([(lx + dx, dy) for dx in (-20, 20) for dy in (-20, 20)])
                .circle(2.7).extrude(t))
    pl = pl.cut(cq.Workplane("XY").pushPoints([(lx, 0)]).circle(10).extrude(t))
    # E-stop ø22.5 (botón hongo estándar)
    pl = pl.cut(cq.Workplane("XY").pushPoints([P.ESTOP_POS[:2]]).circle(11.25).extrude(t))
    # asas (2x M5 cada extremo)
    pl = pl.cut(cq.Workplane("XY").pushPoints(
        [(x, s * (w / 2 - 14)) for x in (-60, 60) for s in (1, -1)]).circle(2.7).extrude(t))
    # fijación a escuadras
    pl = pl.cut(cq.Workplane("XY").pushPoints(
        [(x, s * (P.Y_SIDE_IN - 10)) for x in ANGLE_X[1:-1] for s in (1, -1)]).circle(2.2).extrude(t))
    # ventilación sobre Jetson
    for i in range(6):
        pl = pl.cut(cq.Workplane("XY").center(P.JETSON["pos"][0] - 40 + 16 * i, 0).slot2D(60, 6, 90).extrude(t))
    return pl


def bulkhead(front: bool) -> cq.Workplane:
    """CH-05 (frente) / CH-06 (atrás): mamparo Al 3 mm en el plano YZ."""
    t = 3.0
    h = P.BODY_TOP_Z - P.BODY_BOTTOM_Z - P.FLOOR_T
    w = P.BODY_INNER_W - 1
    pl = cq.Workplane("YZ").center(0, h / 2).rect(w, h).extrude(t)
    if front:
        # ventana cámara frontal (cubierta con policarbonato) + paso de cables al cabezal
        pl = pl.cut(cq.Workplane("YZ").center(0, P.CAM_FRONT_POS[2] - P.BODY_BOTTOM_Z - P.FLOOR_T)
                    .rect(60, 40).extrude(t))
        pl = pl.cut(cq.Workplane("YZ").pushPoints([(-60, 120), (60, 120)]).circle(9).extrude(t))  # pasacables
    else:
        # panel de conectores: XT60 carga, RJ45 pasamuro, interruptor principal, USB-C debug
        pl = pl.cut(cq.Workplane("YZ").pushPoints([(-70, 110), (-20, 110), (35, 110), (80, 110)])
                    .rect(22, 16).extrude(t))
        pl = pl.cut(cq.Workplane("YZ").center(0, P.CAM_REAR_POS[2] - P.BODY_BOTTOM_Z - P.FLOOR_T)
                    .rect(40, 30).extrude(t))
    return pl


def angle_profile(length: float) -> cq.Workplane:
    """CH-07: escuadra Al 20x20x2 (comprada, cortada a medida). Ala vertical en y=18..20."""
    return (cq.Workplane("YZ").polyline([(0, 0), (20, 0), (20, 20), (18, 20), (18, 2), (0, 2)]).close()
            .extrude(length))


def standoff() -> cq.Workplane:
    """CH-08: separador placa lateral <-> exterior (tubo Al 10x1 o PETG), bulón M5 pasante."""
    L = P.Y_OUTER_PLATE_IN - P.Y_SIDE_OUT
    return cq.Workplane("XY").circle(6.0).circle(2.7).extrude(L)


def handle() -> cq.Workplane:
    """CH-09: asa de transporte (PETG 100% o PLA-CF), 2 bulones M5."""
    L, H, s = 160.0, 45.0, 16.0
    path = cq.Workplane("XZ").polyline([(-L / 2, 0), (-L / 2, H), (L / 2, H), (L / 2, 0)])
    outer = (cq.Workplane("XZ").polyline([(-L / 2 - s / 2, 0), (-L / 2 - s / 2, H + s / 2),
                                          (L / 2 + s / 2, H + s / 2), (L / 2 + s / 2, 0),
                                          (L / 2 - s / 2, 0), (L / 2 - s / 2, H - s / 2),
                                          (-L / 2 + s / 2, H - s / 2), (-L / 2 + s / 2, 0)]).close()
             .extrude(s / 2, both=True))
    outer = outer.edges("|Y").fillet(3)
    outer = outer.cut(cq.Workplane("XY").pushPoints([(-60, 0), (60, 0)]).circle(2.7).extrude(H))
    del path
    return outer


def roller_spacer() -> cq.Workplane:
    """CH-10: separador de rodillo (PETG), ø14 / ø8.4."""
    L = P.Y_TRACK_C - P.PULLEY_W / 2 - P.Y_SIDE_OUT
    return cq.Workplane("XY").circle(7).circle(4.2).extrude(L)


def parts() -> list[Part]:
    lr = lambda pos, rot=(0, 0, 0): [Placement(pos, rot, tag="L"), Placement(pos, rot, mirror_y=True, tag="R")]
    ang_len = P.BODY_LEN - 2 * 40
    standoffs = []
    for x, z in STANDOFFS_XZ:
        standoffs += lr((x, P.Y_SIDE_OUT, z), (-90, 0, 0))
    spacers = []
    for x in P.ROLLER_X:
        spacers += lr((x, P.Y_SIDE_OUT, P.ROLLER_Z), (-90, 0, 0))
    return [
        Part("CH-01", "Placa lateral", "chasis", side_plate, "Al", "Corte láser/agua Al 5052 4 mm",
             lr((0, P.Y_SIDE_IN, 0)), dxf=True, notes="Espejo para el lado derecho (misma pieza girada)."),
        Part("CH-02", "Placa exterior de oruga", "chasis", outer_plate, "Al", "Corte láser Al 5052 3 mm",
             lr((0, P.Y_OUTER_PLATE_IN, 0)), dxf=True),
        Part("CH-03", "Piso", "chasis", floor_plate, "Al", "Corte láser Al 5052 3 mm",
             [Placement((0, 0, P.BODY_BOTTOM_Z))], dxf=True),
        Part("CH-04", "Deck superior", "chasis", deck_plate, "PC", "Policarbonato 4 mm (CNC/láser CO2 no!) o Al 3 mm",
             [Placement((0, 0, P.BODY_TOP_Z))], dxf=True,
             notes="El policarbonato NO se corta con láser CO2 (amarillea y es tóxico): router CNC o sierra."),
        Part("CH-05", "Mamparo delantero", "chasis", lambda: bulkhead(True), "Al", "Corte láser Al 3 mm",
             [Placement((HALF - 3.0 - 6, 0, P.BODY_BOTTOM_Z + P.FLOOR_T))], dxf=True),
        Part("CH-06", "Mamparo trasero (panel de conectores)", "chasis", lambda: bulkhead(False), "Al",
             "Corte láser Al 3 mm", [Placement((-HALF + 6, 0, P.BODY_BOTTOM_Z + P.FLOOR_T))], dxf=True),
        Part("CH-07", "Escuadra Al 20x20x2", "chasis", lambda: angle_profile(ang_len), "Al",
             "Perfil comprado, cortar y agujerear con plantilla", [
                 Placement((-ang_len / 2, P.Y_SIDE_IN - 20, P.BODY_BOTTOM_Z + P.FLOOR_T), (0, 0, 0), tag="LB"),
                 Placement((-ang_len / 2, P.Y_SIDE_IN - 20, P.BODY_BOTTOM_Z + P.FLOOR_T), (0, 0, 0),
                           mirror_y=True, tag="RB"),
                 Placement((ang_len / 2, P.Y_SIDE_IN - 20, P.BODY_TOP_Z), (0, 180, 0), tag="LT"),
                 Placement((ang_len / 2, P.Y_SIDE_IN - 20, P.BODY_TOP_Z), (0, 180, 0), mirror_y=True, tag="RT")],
             export=False, notes="La pieza se modela con la cara contra la placa lateral; ver guía de armado."),
        Part("CH-08", "Separador placa lateral-exterior", "chasis", standoff, "Al",
             "Tubo Al 12x2 cortado o PETG 100%", standoffs),
        Part("CH-09", "Asa de transporte", "chasis", handle, "PLA-CF", "Impresión 3D PLA-CF/PETG 100% relleno",
             [Placement((0, s * (P.Y_SIDE_OUT - 14), P.BODY_TOP_Z + P.DECK_T)) for s in (1, -1)],
             notes="Obligatoria por reglamento (asas seguras para mover el robot)."),
        Part("CH-10", "Separador de rodillo", "traccion", roller_spacer, "PETG", "Impresión 3D PETG 100%", spacers),
    ]
