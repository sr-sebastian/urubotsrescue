"""Tren motriz: poleas de oruga, rodillos, correas, tacos, motores y transmisiones."""

from __future__ import annotations

import math

import cadquery as cq

from . import params as P
from .common import Part, Placement, htd5_pulley

X_REAR = -P.AXLE_DIST / 2
X_FRONT = P.AXLE_DIST / 2
Z_AX = P.AXLE_Z
ROT_Y = (-90.0, 0.0, 0.0)   # eje local Z -> eje global +Y

# Y donde arranca la polea (cara interior de la pestaña) del lado izquierdo
Y_PULLEY0 = P.Y_SIDE_OUT + P.GAP_PLATE_PULLEY
PULLEY_TOTAL_W = P.PULLEY_W + 2 * P.PULLEY_FLANGE_T


# ---------------------------------------------------------------------------
# Piezas fabricadas
# ---------------------------------------------------------------------------

def rear_drive_pulley() -> cq.Workplane:
    """DT-01: polea motriz trasera 60T, cubo con 2 prisioneros M4 y chavetero 4 mm."""
    p = htd5_pulley(P.TRACK_PULLEY_T, P.PULLEY_W, P.DRIVE_SHAFT_D)
    # alivianado: 6 agujeros
    r = P.htd5_od(P.TRACK_PULLEY_T) / 2 - 14
    cut = (cq.Workplane("XY").polarArray(r * 0.62, 0, 360, 6).circle(9).extrude(PULLEY_TOTAL_W))
    p = p.cut(cut)
    # chavetero 4x2 (eje con chaveta) + prisioneros radiales
    key = cq.Workplane("XY").center(P.DRIVE_SHAFT_D / 2, 0).rect(4.0, 4.0).extrude(PULLEY_TOTAL_W)
    p = p.cut(key)
    for z in (PULLEY_TOTAL_W * 0.3, PULLEY_TOTAL_W * 0.7):
        ss = (cq.Workplane("YZ", origin=(0, 0, z)).circle(1.65).extrude(40))
        p = p.cut(ss)
    return p


def front_compound_pulley() -> cq.Workplane:
    """DT-02: polea delantera compuesta (oruga principal + flipper) en una pieza.

    Gira libre sobre el tubo de flipper con 2 rodamientos 6804 (32 mm) en los extremos.
    """
    gap = P.GAP_PLATE_PULLEY
    a = htd5_pulley(P.TRACK_PULLEY_T, P.PULLEY_W, 32.0)
    b = htd5_pulley(P.TRACK_PULLEY_T, P.PULLEY_W, 32.0).translate((0, 0, PULLEY_TOTAL_W + gap))
    spacer = (cq.Workplane("XY").circle(P.htd5_od(P.TRACK_PULLEY_T) / 2 - 6).circle(16.0)
              .extrude(gap).translate((0, 0, PULLEY_TOTAL_W)))
    p = a.union(b).union(spacer)
    total = 2 * PULLEY_TOTAL_W + gap
    # interior: ø32 solo en los asientos de rodamiento (7 mm), resto ø24 para no tocar el tubo
    core = cq.Workplane("XY").circle(16.0).extrude(total)
    p = p.cut(core)
    ring = (cq.Workplane("XY").circle(16.0).circle(12.5).extrude(total - 2 * 7.0)
            .translate((0, 0, 7.0)))
    p = p.union(ring)
    r = P.htd5_od(P.TRACK_PULLEY_T) / 2 - 14
    p = p.cut(cq.Workplane("XY").polarArray(r * 0.62, 30, 360, 6).circle(8).extrude(total))
    return p


def flipper_tip_pulley() -> cq.Workplane:
    """DT-04: polea de punta de flipper 36T, 2 rodamientos 6900 (10x22x6)."""
    p = htd5_pulley(P.FLIP_TIP_T, P.PULLEY_W, 22.0)
    ring = (cq.Workplane("XY").circle(11.0).circle(8.0).extrude(PULLEY_TOTAL_W - 12.0)
            .translate((0, 0, 6.0)))
    return p.union(ring)


def support_roller() -> cq.Workplane:
    """DT-03: rodillo de apoyo ø40 con rodamiento 608 (eje M8)."""
    w = P.PULLEY_W
    r = cq.Workplane("XY").circle(P.ROLLER_D / 2).extrude(w)
    fl = cq.Workplane("XY").circle(P.ROLLER_D / 2 + 3).extrude(1.5)
    r = r.union(fl).union(fl.translate((0, 0, w - 1.5)))
    r = r.cut(cq.Workplane("XY").circle(11.0).extrude(w))
    ring = cq.Workplane("XY").circle(11.0).circle(6.0).extrude(w - 14).translate((0, 0, 7))
    return r.union(ring)


def grouser() -> cq.Workplane:
    """DT-05: taco de TPU 95A (pegado + 2 remaches POP 3.2 al lomo de la correa)."""
    L, W, H = 10.0, P.TRACK_BELT_W, P.GROUSER_H
    g = (cq.Workplane("XZ").polyline([(-L / 2, 0), (L / 2, 0), (L / 2 - 2.5, H), (-L / 2 + 2.5, H)])
         .close().extrude(-W).translate((0, -0.0, 0)))
    g = g.cut(cq.Workplane("XY").pushPoints([(0, W * 0.25), (0, W * 0.75)]).circle(1.7).extrude(H))
    return g


def inner_pulley(teeth: int, bore: float, width: float = P.DRIVE_INNER_BELT_W + 1) -> cq.Workplane:
    return htd5_pulley(teeth, width, bore, flange=True, hub_d=P.htd5_od(teeth) * 0.7, hub_l=8)


def motor_bracket(axis_h: float, gear_d: float = P.GM42_D, pcd: float = P.GM42_BOLT_PCD,
                  pilot: float = P.GM42_PILOT_D, bolt: float = 4.4) -> cq.Workplane:
    """Soporte de motorreductor 42 mm (PLA-CF 60%). Cara del motor en y=0..8 (local),
    el motor queda del lado -Y; el pie apoya en el piso a `axis_h` bajo el eje y tiene
    ranuras M5 de 12 mm en X para tensar la correa interna."""
    t = 8.0
    h = axis_h
    w = max(70.0, gear_d + 28)
    top = gear_d / 2 + 6.0
    plate = cq.Workplane("XZ").center(0, (top - h) / 2).rect(w, h + top).extrude(-t)
    plate = plate.cut(cq.Workplane("XZ").circle(pilot / 2 + 0.4).extrude(-t))
    r = pcd / 2
    pts = [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in (45, 135, 225, 315)]
    plate = plate.cut(cq.Workplane("XZ").pushPoints(pts).circle(bolt / 2).extrude(-t))
    foot = cq.Workplane("XY").box(w, 60, t).translate((0, -60 / 2 + t, -h + t / 2))
    for x in (-24, 24):
        for y in (-12, -40):
            foot = foot.cut(cq.Workplane("XY").center(x, y).slot2D(12 + 5.5, 5.5, 0).extrude(t)
                            .translate((0, 0, -h)))
    rib = (cq.Workplane("YZ").polyline([(t, -h + t), (-50, -h + t), (t, -h + t + 0.8 * h)]).close()
           .extrude(5))
    body = plate.union(foot).union(rib.translate((-w / 2, 0, 0))).union(rib.translate((w / 2 - 5, 0, 0)))
    return body


def drive_motor_bracket() -> cq.Workplane:
    """DT-08: soporte de motor de tracción."""
    return motor_bracket(DRIVE_MOTOR_Z - (P.BODY_BOTTOM_Z + P.FLOOR_T))


def flipper_motor_bracket() -> cq.Workplane:
    """DT-11: soporte del motor de flipper (reductora de 56 mm, 4x M5)."""
    return motor_bracket(FLIP_MOTOR_Z - (P.BODY_BOTTOM_Z + P.FLOOR_T), P.GM56_D, P.GM56_BOLT_PCD,
                         P.GM56_PILOT_D, 5.5)


def flip_big_pulley() -> cq.Workplane:
    """DT-10: polea 30T sobre el tubo de flipper, fijada con pasador M5 pasante."""
    p = htd5_pulley(P.FLIP_RED_BIG_T, P.DRIVE_INNER_BELT_W + 1, P.FLIP_TUBE_OD,
                    hub_d=34, hub_l=14)
    zc = P.DRIVE_INNER_BELT_W + 1 + 2 * P.PULLEY_FLANGE_T + 7
    p = p.cut(cq.Workplane("YZ", origin=(-30, 0, zc)).circle(2.75).extrude(60))
    return p


# ---------------------------------------------------------------------------
# Referencias compradas (solo visual + masa)
# ---------------------------------------------------------------------------

def gearmotor_42(gear_d: float = P.GM42_D, gear_l: float = P.GM42_GEAR_L,
                 shaft_d: float = P.GM42_SHAFT_D) -> cq.Workplane:
    """Motor 775 + reductora planetaria + encoder (referencia). Eje en +Z, cara de la reductora en z=gear_l."""
    g = cq.Workplane("XY").circle(gear_d / 2).extrude(gear_l)
    m = (cq.Workplane("XY").circle(P.GM42_MOTOR_D / 2).extrude(P.GM42_MOTOR_L)
         .translate((0, 0, -P.GM42_MOTOR_L)))
    e = (cq.Workplane("XY").circle(P.GM42_MOTOR_D / 2 - 4).extrude(P.GM42_ENC_L)
         .translate((0, 0, -P.GM42_MOTOR_L - P.GM42_ENC_L)))
    s = (cq.Workplane("XY").circle(shaft_d / 2).extrude(P.GM42_SHAFT_L)
         .translate((0, 0, gear_l)))
    return g.union(m).union(e).union(s)


def belt_loop(c1, r1, c2, r2, thickness, width) -> cq.Workplane:
    """Correa cerrada alrededor de dos poleas (círculos en XZ), extruida en +Y."""
    def hull(rr1, rr2):
        sk = cq.Sketch().arc(c1, rr1, 0, 360).arc(c2, rr2, 0, 360).hull()
        return cq.Workplane("XZ").placeSketch(sk).extrude(-width)
    outer = hull(r1 + thickness, r2 + thickness)
    inner = hull(r1, r2)
    return outer.cut(inner)


def main_belt() -> cq.Workplane:
    r = P.TRACK_PD / 2 - P.HTD5_PLD
    return belt_loop((X_REAR, Z_AX), r, (X_FRONT, Z_AX), r, P.HTD5_BELT_T, P.TRACK_BELT_W)


def loop_points(c1, r1, c2, r2, step):
    """Puntos (x, z, ángulo normal) a lo largo del exterior de un lazo de 2 círculos."""
    (x1, z1), (x2, z2) = c1, c2
    dx, dz = x2 - x1, z2 - z1
    d = math.hypot(dx, dz)
    base = math.atan2(dz, dx)
    phi = math.acos((r1 - r2) / d)
    # tangente superior: ángulo normal = base + phi ; inferior: base - phi
    segs = []
    a_top, a_bot = base + phi, base - phi
    # arco en c2 desde a_top hasta a_bot (sentido horario pasando por base)
    segs.append(("arc", c2, r2, a_top, a_bot - 2 * math.pi if a_bot > a_top else a_bot))
    segs.append(("line", (x2 + r2 * math.cos(a_bot), z2 + r2 * math.sin(a_bot)),
                 (x1 + r1 * math.cos(a_bot), z1 + r1 * math.sin(a_bot)), a_bot))
    segs.append(("arc", c1, r1, a_bot, a_top - 2 * math.pi))
    segs.append(("line", (x1 + r1 * math.cos(a_top), z1 + r1 * math.sin(a_top)),
                 (x2 + r2 * math.cos(a_top), z2 + r2 * math.sin(a_top)), a_top))
    lengths = []
    for s in segs:
        if s[0] == "arc":
            lengths.append(abs(s[4] - s[3]) * s[2])
        else:
            lengths.append(math.dist(s[1], s[2]))
    total = sum(lengths)
    out = []
    t = 0.0
    while t < total - 1e-6:
        acc = t
        for s, L in zip(segs, lengths):
            if acc <= L:
                f = acc / L
                if s[0] == "arc":
                    a = s[3] + (s[4] - s[3]) * f
                    out.append((s[1][0] + s[2] * math.cos(a), s[1][1] + s[2] * math.sin(a), a))
                else:
                    x = s[1][0] + (s[2][0] - s[1][0]) * f
                    z = s[1][1] + (s[2][1] - s[1][1]) * f
                    out.append((x, z, s[3]))
                break
            acc -= L
        t += step
    return out


def grousers_on_loop(c1, r1, c2, r2) -> cq.Workplane:
    g0 = grouser()
    step = P.HTD5_PITCH * P.GROUSER_PITCH_TEETH
    shapes = None
    for x, z, a in loop_points(c1, r1, c2, r2, step):
        rot_deg = -math.degrees(a) + 90.0   # el taco "mira" hacia afuera (+Z local)
        g = g0.rotate((0, 0, 0), (0, 1, 0), rot_deg - 180.0).translate((x, 0, z))
        shapes = g if shapes is None else shapes.union(g, clean=False)
    return shapes


def main_grousers() -> cq.Workplane:
    r = P.TRACK_PD / 2 - P.HTD5_PLD + P.HTD5_BELT_T
    return grousers_on_loop((X_REAR, Z_AX), r, (X_FRONT, Z_AX), r)


def flipper_belt(angle_deg: float = P.FLIP_ANGLE_STOW) -> cq.Workplane:
    a = math.radians(angle_deg)
    tip = (X_FRONT + P.FLIP_LEN * math.cos(a), Z_AX + P.FLIP_LEN * math.sin(a))
    r1 = P.TRACK_PD / 2 - P.HTD5_PLD
    r2 = P.FLIP_TIP_PD / 2 - P.HTD5_PLD
    return belt_loop((X_FRONT, Z_AX), r1, tip, r2, P.HTD5_BELT_T, P.TRACK_BELT_W)


def flipper_grousers(angle_deg: float = P.FLIP_ANGLE_STOW) -> cq.Workplane:
    a = math.radians(angle_deg)
    tip = (X_FRONT + P.FLIP_LEN * math.cos(a), Z_AX + P.FLIP_LEN * math.sin(a))
    r1 = P.TRACK_PD / 2 - P.HTD5_PLD + P.HTD5_BELT_T
    r2 = P.FLIP_TIP_PD / 2 - P.HTD5_PLD + P.HTD5_BELT_T
    return grousers_on_loop((X_FRONT, Z_AX), r1, tip, r2)


def shaft(d: float, length: float) -> cq.Workplane:
    return cq.Workplane("XY").circle(d / 2).extrude(length)


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Transmisiones internas (se calculan para usar correas de largo estándar)
# ---------------------------------------------------------------------------
Y_INNER_BELT_C = 90.0          # plano de las correas internas (lado de cada motor)
Y_MOTOR_FACE = 70.0            # cara de montaje de la reductora (contra DT-08)
INNER_PULLEY_W = P.DRIVE_INNER_BELT_W + 1 + 2 * P.PULLEY_FLANGE_T   # 20 mm
DRIVE_MOTOR_Z = 85.0
FLIP_MOTOR_Z = 110.0
DRIVE_BELT_L = (300.0, 425.0)  # HTD 300-5M-15 (izq.) y 425-5M-15 (der.)
FLIP_BELT_L = 300.0            # HTD 300-5M-15


def _motor_x(belt_len, t_small, t_big, x_axle, dz, sign):
    c = P.center_for_belt(belt_len, P.htd5_pd(t_small), P.htd5_pd(t_big))
    return x_axle + sign * math.sqrt(c * c - dz * dz), c


DRIVE_MOTOR_X = tuple(_motor_x(L, P.DRIVE_RED_SMALL_T, P.DRIVE_RED_BIG_T, X_REAR,
                               DRIVE_MOTOR_Z - Z_AX, +1)[0] for L in DRIVE_BELT_L)
FLIP_MOTOR_X = _motor_x(FLIP_BELT_L, P.FLIP_RED_SMALL_T, P.FLIP_RED_BIG_T, X_FRONT,
                        FLIP_MOTOR_Z - Z_AX, -1)[0]
SHAFT_Y0 = Y_INNER_BELT_C - INNER_PULLEY_W / 2 - 2.0
SHAFT_LEN = (P.Y_OUTER_PLATE_IN + P.OUTER_PLATE_T + 12.0) - SHAFT_Y0


def parts() -> list[Part]:
    yL = Y_PULLEY0
    track_y = P.Y_TRACK_C - P.TRACK_BELT_W / 2
    flip_y = P.Y_FLIP_C - P.TRACK_BELT_W / 2
    lr = lambda pos, rot=ROT_Y: [Placement(pos, rot, tag="L"), Placement(pos, rot, mirror_y=True, tag="R")]

    rollers = []
    for x in P.ROLLER_X:
        rollers += lr((x, P.Y_TRACK_C - P.PULLEY_W / 2, P.ROLLER_Z))

    out = [
        Part("DT-01", "Polea motriz trasera 60T HTD5M", "traccion", rear_drive_pulley, "PLA-CF",
             "Impresión 3D PLA-CF/PETG, 5 perímetros, 50% gyroid. Competencia: Al 60-5M-25 + cubo",
             lr((X_REAR, yL, Z_AX)), notes="Chavetero 4 mm + 2 prisioneros M4 a 90°."),
        Part("DT-02", "Polea delantera compuesta 60T+60T", "traccion", front_compound_pulley, "PLA-CF",
             "Impresión 3D PLA-CF, 5 perímetros, 50% gyroid", lr((X_FRONT, yL, Z_AX)),
             notes="2x rodamiento 6804-2RS. Gira libre sobre el tubo de flipper."),
        Part("DT-03", "Rodillo de apoyo ø40", "traccion", support_roller, "PETG",
             "Impresión 3D PETG, 4 perímetros, 40%", rollers, notes="Rodamiento 608-2RS, eje bulón M8."),
        Part("DT-05", "Taco de oruga (grouser) TPU", "traccion", grouser, "TPU",
             "Impresión 3D TPU 95A, 100% relleno", [], qty_override=2 * (55 + 38) + 20,
             notes="2x55 (orugas) + 2x38 (flippers) + 20 de repuesto"),
        Part("DT-06", "Polea 20T motor de tracción (HTD5M 15)", "traccion", lambda: inner_pulley(20, P.GM42_SHAFT_D),
             "PLA-CF", "Impresión 3D o Al comercial 20-5M-15", [
                 Placement((DRIVE_MOTOR_X[0], Y_INNER_BELT_C - INNER_PULLEY_W / 2, DRIVE_MOTOR_Z), ROT_Y, tag="L"),
                 Placement((DRIVE_MOTOR_X[1], Y_INNER_BELT_C - INNER_PULLEY_W / 2, DRIVE_MOTOR_Z), ROT_Y,
                           mirror_y=True, tag="R")],
             notes="Eje de motor 8 mm con D-flat: prisionero M4."),
        Part("DT-07", "Polea 30T eje trasero (HTD5M 15)", "traccion", lambda: inner_pulley(30, P.DRIVE_SHAFT_D),
             "PLA-CF", "Impresión 3D o Al comercial 30-5M-15",
             lr((X_REAR, Y_INNER_BELT_C - INNER_PULLEY_W / 2, Z_AX))),
        Part("DT-08", "Soporte motor de tracción (tensable)", "traccion", drive_motor_bracket, "PLA-CF",
             "Impresión 3D PLA-CF 6 perímetros 60%", [
                 Placement((DRIVE_MOTOR_X[0], Y_MOTOR_FACE, DRIVE_MOTOR_Z), (0, 0, 0), tag="L"),
                 Placement((DRIVE_MOTOR_X[1], Y_MOTOR_FACE, DRIVE_MOTOR_Z), (0, 0, 0), mirror_y=True, tag="R")]),
        Part("DT-09", "Polea 14T motor de flipper (HTD5M 15)", "flipper", lambda: inner_pulley(14, P.GM56_SHAFT_D),
             "Al", "Al comercial 14-5M-15 (14T impresa no aguanta), bore 12 + chavetero",
             [Placement((FLIP_MOTOR_X, Y_INNER_BELT_C - INNER_PULLEY_W / 2, FLIP_MOTOR_Z), ROT_Y, mirror_y=True)]),
        Part("DT-10", "Polea 30T tubo de flipper (HTD5M 15)", "flipper", flip_big_pulley, "PLA-CF",
             "Impresión 3D PLA-CF 6 perímetros 60%",
             [Placement((X_FRONT, Y_INNER_BELT_C + INNER_PULLEY_W / 2, Z_AX), (90.0, 0.0, 0.0), mirror_y=True)],
             notes="Cubo hacia el centro del robot. Pasador M5 pasante por el tubo (agujero ø5.2)."),
        Part("DT-11", "Soporte motor de flipper", "flipper", flipper_motor_bracket, "PLA-CF",
             "Impresión 3D PLA-CF 6 perímetros 60%",
             [Placement((FLIP_MOTOR_X, Y_MOTOR_FACE, FLIP_MOTOR_Z), (0, 0, 0), mirror_y=True)]),
        # ---- referencias
        Part("REF-M1", "Motorreductor 775 24V planetario 42mm (tracción)", "referencia", gearmotor_42, "motor",
             "Comprado", [Placement((DRIVE_MOTOR_X[0], Y_MOTOR_FACE - P.GM42_GEAR_L, DRIVE_MOTOR_Z), ROT_Y, tag="L"),
                          Placement((DRIVE_MOTOR_X[1], Y_MOTOR_FACE - P.GM42_GEAR_L, DRIVE_MOTOR_Z), ROT_Y,
                                    mirror_y=True, tag="R")],
             export=False, bought=True),
        Part("REF-M2", "Motorreductor 775 24V planetario 56mm 1:264 (flipper)", "referencia",
             lambda: gearmotor_42(P.GM56_D, P.GM56_GEAR_L, P.GM56_SHAFT_D), "motor",
             "Comprado", [Placement((FLIP_MOTOR_X, Y_MOTOR_FACE - P.GM56_GEAR_L, FLIP_MOTOR_Z), ROT_Y, mirror_y=True)],
             export=False, bought=True),
        Part("REF-B1", "Correa HTD 1100-5M-25 (oruga)", "traccion", main_belt, "belt", "Comprado",
             lr((0, track_y, 0), (0, 0, 0)), export=False, bought=True),
        Part("REF-B2", "Tacos montados (oruga principal)", "traccion", main_grousers, "TPU", "Ver DT-05",
             lr((0, track_y, 0), (0, 0, 0)), export=False, bought=True),
        Part("REF-B3", "Correa HTD 760-5M-25 (flipper)", "flipper", flipper_belt, "belt", "Comprado",
             lr((0, flip_y, 0), (0, 0, 0)), export=False, bought=True),
        Part("REF-B4", "Tacos montados (flipper)", "flipper", flipper_grousers, "TPU", "Ver DT-05",
             lr((0, flip_y, 0), (0, 0, 0)), export=False, bought=True),
        Part("REF-S1", "Eje motriz acero 12 mm (largo según params)", "traccion", lambda: shaft(P.DRIVE_SHAFT_D, SHAFT_LEN), "steel",
             "Acero plata 12 mm h7, 2 chaveteros 4x2.5 (tornería)",
             lr((X_REAR, SHAFT_Y0, Z_AX), ROT_Y), export=False, bought=True),
        Part("REF-S2", "Tubo de flipper Al 6061 20x2 x 400", "flipper", lambda: shaft(P.FLIP_TUBE_OD, 2 * P.Y_TOTAL - 4),
             "Al", "Tubo Al 20x2 cortado a medida, 2 agujeros ø5.2 por extremo",
             [Placement((X_FRONT, -(P.Y_TOTAL - 2), Z_AX), ROT_Y)], export=False, bought=True),
    ]
    return out
