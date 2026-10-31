"""Soportes de electrónica y sensores + referencias de componentes comprados."""

from __future__ import annotations

import cadquery as cq

from . import params as P
from .common import Part, Placement, rounded_box

ZF = P.BODY_BOTTOM_Z + P.FLOOR_T          # cara superior del piso
ZD = P.BODY_TOP_Z + P.DECK_T              # cara superior del deck

# Layout de la bandeja de electrónica (x, y) en coordenadas del robot -> caja (lx, ly, lz)
TRAY_Z = P.ELECTRONICS_TRAY["pos"][2]
TRAY_X = P.ELECTRONICS_TRAY["pos"][0]
ELEC_LAYOUT = {
    # en la bandeja (z = TRAY_Z + 3)
    "jetson": dict(pos=(-30.0, 0.0), size=(103.0, 90.0, 35.0), name="Jetson Orin Nano Super (devkit)"),
    "esp32": dict(pos=(-105.0, 62.0), size=(46.0, 70.0, 18.0), name="ESP32-S3 DevKitC-1 + placa base (PCB-01)"),
    "buck_12v_pc": dict(pos=(40.0, 80.0), size=(50.0, 60.0, 22.0), name="Buck 24->12 V 10 A (Jetson)"),
    "buck_12v_arm": dict(pos=(-30.0, 80.0), size=(60.0, 50.0, 22.0), name="Buck 24->12 V 10 A (servos brazo)"),
    "buck_5v": dict(pos=(-30.0, -80.0), size=(50.0, 30.0, 15.0), name="Buck 24->5 V 5 A (lógica/USB/LEDs)"),
    # verticales, atornillados a la cara interior de las placas laterales
    "drv_traccion": dict(pos=(150.0, 103.0), z=118.0, size=(84.0, 22.0, 62.0),
                         name="Cytron MDD20A (tracción, 2 canales)"),
    "drv_flipper": dict(pos=(180.0, -103.0), z=118.0, size=(63.0, 22.0, 60.0),
                        name="Cytron MDD10A (flipper + canal libre)"),
}
FLOOR_LAYOUT = {
    "fusibles": dict(pos=(-200.0, -40.0, ZF), size=(60.0, 45.0, 30.0), name="Caja fusibles ATO 6 vías"),
    "rele_estop": dict(pos=(-200.0, 40.0, ZF), size=(40.0, 30.0, 30.0), name="Contactor/relé 40 A del E-stop"),
    "hub_usb": dict(pos=(-170.0, 0.0, ZF), size=(90.0, 30.0, 15.0), name="Hub USB 3.0 alimentado 7 puertos"),
}


def electronics_tray() -> cq.Workplane:
    """MT-01: bandeja de electrónica (PETG 3 mm o placa perforada de policarbonato)."""
    sx, sy, t = 196.0, P.BODY_INNER_W - 6, 3.0
    tray = cq.Workplane("XY").rect(sx, sy).extrude(t).translate((TRAY_X, 0, TRAY_Z))
    # grilla de agujeros M3 cada 15 mm (montaje flexible tipo "breadboard")
    pts = [(TRAY_X + x, y) for x in range(-90, 91, 15) for y in range(-105, 106, 15)]
    tray = tray.cut(cq.Workplane("XY").pushPoints(pts).circle(1.6).extrude(t).translate((0, 0, TRAY_Z)))
    # patas: 4 columnas a las escuadras laterales
    for x in (TRAY_X - 88, TRAY_X + 88):
        for y in (sy / 2 - 8, -sy / 2 + 8):
            col = cq.Workplane("XY").circle(5).circle(1.6).extrude(TRAY_Z - ZF).translate((x, y, ZF))
            tray = tray.union(col)
    return tray


def battery_box() -> cq.Workplane:
    """MT-02: cuna de batería (PETG) con ranuras para correa velcro y espuma."""
    bx, by, bz = P.BATTERY["size"]
    x, y, _ = P.BATTERY["pos"]
    w = 3.0
    box = rounded_box(bx + 2 * w + 6, by + 2 * w + 6, 30, 4).translate((x, y, ZF + 15))
    box = box.cut(rounded_box(bx + 6, by + 6, 30, 3).translate((x, y, ZF + 15 + w)))
    box = box.cut(cq.Workplane("XY").pushPoints([(x, y + 50), (x, y - 50)]).rect(bx + 20, 22).extrude(10)
                  .translate((0, 0, ZF + 20)))
    return box


def lidar_mast() -> cq.Workplane:
    """MT-03: mástil del LiDAR (base y plato impresos; tubo Al 25x2 en el medio)."""
    lx, ly, lz = P.LIDAR_POS
    h = lz - ZD - 8
    base = rounded_box(56, 56, 8, 6).translate((lx, ly, ZD + 4))
    base = base.cut(cq.Workplane("XY").pushPoints([(lx + dx, dy) for dx in (-20, 20) for dy in (-20, 20)])
                    .circle(2.7).extrude(8).translate((0, 0, ZD)))
    tube = cq.Workplane("XY").circle(12.5).circle(10.5).extrude(h - 8).translate((lx, ly, ZD + 8))
    top = cq.Workplane("XY").circle(36).extrude(8).translate((lx, ly, lz - 8))
    top = top.cut(cq.Workplane("XY").polarArray(23, 45, 360, 4).circle(1.7).extrude(8).translate((lx, ly, lz - 8)))
    return base.union(tube).union(top)


def sensor_head() -> cq.Workplane:
    """MT-04: cabezal frontal: cámara de profundidad + térmica + LEDs, sobre el deck."""
    x, y, z = P.DEPTH_CAM_POS
    bracket = rounded_box(40, 160, 6, 4).translate((x - 5, 0, ZD + 3))
    post = rounded_box(10, 120, 30, 3).translate((x - 18, 0, ZD + 6 + 15))
    shelf = rounded_box(36, 150, 5, 3).translate((x - 8, 0, z - 17))
    leds = rounded_box(6, 150, 14, 2).translate((x + 6, 0, z + 25))
    return bracket.union(post).union(shelf).union(leds)


def estop_mount() -> cq.Workplane:
    """MT-05: anillo/protección del E-stop (evita golpes accidentales, deja el hongo accesible)."""
    x, y, z = P.ESTOP_POS
    ring = cq.Workplane("XY").circle(30).circle(26).extrude(22).translate((x, y, z))
    ring = ring.cut(cq.Workplane("XY").center(x + 30, y).rect(20, 20).extrude(22).translate((0, 0, z)))
    return ring


def front_cam_mount() -> cq.Workplane:
    """MT-06: soporte cámara gran angular frontal (detrás del mamparo)."""
    x, y, z = P.CAM_FRONT_POS
    m = rounded_box(8, 50, 50, 3).translate((x - 20, y, z))
    m = m.union(rounded_box(30, 50, 6, 2).translate((x - 33, y, z - 22)))
    return m.cut(cq.Workplane("YZ").center(y, z).circle(8).extrude(8).translate((x - 24, 0, 0)))


# ---- referencias compradas (cajas de color) ---------------------------------

def box_ref(size, center_bottom) -> cq.Workplane:
    sx, sy, sz = size
    x, y, z = center_bottom
    return rounded_box(sx, sy, sz, 2).translate((x, y, z + sz / 2))


def lidar_ref() -> cq.Workplane:
    x, y, z = P.LIDAR_POS
    return cq.Workplane("XY").circle(32.5).extrude(65).translate((x, y, z))   # Livox Mid-360 ø65x65


def parts() -> list[Part]:
    out = [
        Part("MT-01", "Bandeja de electrónica", "electronica", electronics_tray, "PETG",
             "Impresión 3D PETG (2 mitades) o policarbonato 3 mm + columnas", [Placement()]),
        Part("MT-02", "Cuna de batería", "electronica", battery_box, "PETG", "Impresión 3D PETG 30%", [Placement()]),
        Part("MT-03", "Mástil del LiDAR", "sensores", lidar_mast, "PLA-CF",
             "Base y plato impresos + tubo Al 25x2", [Placement()]),
        Part("MT-04", "Cabezal de sensores frontal", "sensores", sensor_head, "PLA-CF", "Impresión 3D PLA-CF 40%",
             [Placement()]),
        Part("MT-05", "Protección del E-stop", "electronica", estop_mount, "PETG", "Impresión 3D PETG rojo",
             [Placement()]),
        Part("MT-06", "Soporte cámara frontal", "sensores", front_cam_mount, "PETG", "Impresión 3D PETG",
             [Placement()]),
        Part("REF-BAT", P.BATTERY["name"], "referencia", lambda: box_ref(P.BATTERY["size"], (
            P.BATTERY["pos"][0], P.BATTERY["pos"][1], ZF + 3)), "elec", "Comprado", [Placement()],
             export=False, bought=True, color="yellow"),
        Part("REF-LID", "Livox Mid-360 (LiDAR 3D)", "referencia", lidar_ref, "sensor", "Comprado", [Placement()],
             export=False, bought=True),
        Part("REF-DEP", "Cámara de profundidad (Orbbec Gemini 2 / RealSense D435i)", "referencia",
             lambda: box_ref((26.0, 90.0, 25.0), (P.DEPTH_CAM_POS[0] - 5, 0, P.DEPTH_CAM_POS[2] - 14)), "sensor",
             "Comprado", [Placement()], export=False, bought=True),
        Part("REF-THM", "Cámara térmica USB 256x192", "referencia",
             lambda: box_ref((20.0, 26.0, 26.0), (P.DEPTH_CAM_POS[0] - 5, 62.0, P.DEPTH_CAM_POS[2] - 14)), "sensor",
             "Comprado", [Placement()], export=False, bought=True),
        Part("REF-ESTOP", "E-stop hongo 22 mm NC", "referencia",
             lambda: cq.Workplane("XY").circle(20).extrude(18).translate(
                 (P.ESTOP_POS[0], P.ESTOP_POS[1], P.ESTOP_POS[2] + 6)), "red", "Comprado", [Placement()],
             export=False, bought=True, color="red"),
    ]
    for key, d in ELEC_LAYOUT.items():
        x, y = d["pos"]
        out.append(Part(f"REF-{key}", d["name"], "referencia",
                        (lambda d=d, x=x, y=y: box_ref(d["size"], (x, y, d.get("z", TRAY_Z + 3)))), "elec",
                        "Comprado",
                        [Placement()], export=False, bought=True))
    for key, d in FLOOR_LAYOUT.items():
        out.append(Part(f"REF-{key}", d["name"], "referencia", (lambda d=d: box_ref(d["size"], d["pos"])), "elec",
                        "Comprado", [Placement()], export=False, bought=True))
    return out
