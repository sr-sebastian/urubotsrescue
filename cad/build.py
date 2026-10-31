#!/usr/bin/env python3
"""Genera todos los archivos de fabricación y el ensamble del robot Carpincho.

Uso:
    pip install -r cad/requirements.txt
    python cad/build.py            # todo
    python cad/build.py --fast     # sin STEP del ensamble completo (más rápido)

Salida en cad/out/:
    step/<código>.step      piezas individuales (para Fusion/Onshape/SolidWorks/FreeCAD)
    stl/<código>.stl        piezas imprimibles
    dxf/<código>.dxf        contornos 2D de placas (corte láser / agua / router)
    carpincho.glb           ensamble con colores (lo usa el visor web /visor)
    carpincho_ensamble.step ensamble completo
    parts.json              catálogo de piezas (lo usan el visor, la BOM y la guía)
    masa_cg.md              presupuesto de masa y centro de gravedad
y además regenera ros2_ws/src/carpincho_description/urdf/carpincho_params.xacro
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from carpincho_cad import params as P                     # noqa: E402
from carpincho_cad import arm, chassis, drivetrain, flipper, mounts   # noqa: E402
from carpincho_cad.common import COLORS, GROUPS, Part, place          # noqa: E402

OUT = HERE / "out"
REPO = HERE.parent
XACRO = REPO / "ros2_ws/src/carpincho_description/urdf/carpincho_params.xacro"

# masas de componentes comprados por instancia [g]
BOUGHT_MASS = {
    "REF-M1": 750, "REF-M2": 750, "REF-SV": 55, "REF-BAT": 1300, "REF-LID": 265, "REF-DEP": 300,
    "REF-THM": 60, "REF-ESTOP": 80, "REF-jetson": 280, "REF-esp32": 60, "REF-buck_12v_pc": 120,
    "REF-buck_12v_arm": 120, "REF-buck_5v": 50, "REF-drv_traccion": 120, "REF-drv_flipper": 80,
    "REF-fusibles": 80, "REF-rele_estop": 100, "REF-hub_usb": 120,
}
PRINT_INFILL_FACTOR = 0.6     # masa real / masa sólida para piezas impresas típicas
EXTRA_MASS = [                # cosas que no están modeladas: cables, bulonería, rodamientos
    ("Cableado y conectores", 900.0, (-40.0, 0.0, 110.0)),
    ("Bulonería, rodamientos, escuadras", 1100.0, (0.0, 0.0, 80.0)),
    ("Cámaras USB (x3) + parlante + micrófono", 250.0, (100.0, 0.0, 170.0)),
]


def all_parts() -> list[Part]:
    parts = []
    for mod in (chassis, drivetrain, flipper, arm, mounts):
        parts += mod.parts()
    codes = [p.code for p in parts]
    dup = {c for c in codes if codes.count(c) > 1}
    if dup:
        raise SystemExit(f"Códigos de pieza duplicados: {dup}")
    return parts


def to_flat_for_dxf(shape: cq.Workplane) -> cq.Workplane:
    """Rota una placa para que su espesor quede en Z y devuelve la cara inferior."""
    bb = shape.val().BoundingBox()
    dims = {"x": bb.xlen, "y": bb.ylen, "z": bb.zlen}
    thin = min(dims, key=dims.get)
    s = shape
    if thin == "x":                      # placa en YZ (mamparos): primero llevarla a XZ
        s = s.rotate((0, 0, 0), (0, 0, 1), 90)
        thin = "y"
    if thin == "y":                      # placa en XZ: Z del robot queda "arriba" en el DXF
        s = s.rotate((0, 0, 0), (1, 0, 0), -90)
    bb = s.val().BoundingBox()
    s = s.translate((-bb.xmin, -bb.ymin, -bb.zmin))
    # Workplane NUEVO en XY: el exportador DXF proyecta sobre el plano del Workplane, y una placa
    # creada en "XZ" arrastra ese plano (saldría proyectada de canto, como una línea)
    return cq.Workplane("XY").add(s.faces("<Z").val())


def mass_of(part: Part, shape: cq.Workplane) -> float:
    if part.code in BOUGHT_MASS:
        return float(BOUGHT_MASS[part.code])
    vol = shape.val().Volume()
    dens = P.DENSITY.get(part.material, P.DENSITY.get("PETG"))
    if part.material in ("belt",):
        dens = 1.25e-3
    if part.material in ("motor", "elec", "sensor", "red"):
        dens = 1.5e-3
    m = vol * dens
    if not part.bought and part.material in ("PETG", "PLA-CF", "TPU") and part.code != "DT-05":
        m *= PRINT_INFILL_FACTOR
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="no exportar el STEP del ensamble")
    ap.add_argument("--only", default="", help="solo estas piezas (códigos separados por coma)")
    args = ap.parse_args()
    t0 = time.time()
    for sub in ("step", "stl", "dxf"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)

    parts = all_parts()
    only = {c.strip() for c in args.only.split(",") if c.strip()}
    assy = cq.Assembly(name="carpincho")
    catalog = []
    mass_rows = []
    tot_m, mx, my, mz = 0.0, 0.0, 0.0, 0.0
    used_names: set[str] = set()

    for part in parts:
        if only and part.code not in only:
            continue
        print(f"  {part.code:10s} {part.name}", flush=True)
        shape = part.make()
        bb = shape.val().BoundingBox()
        entry = dict(code=part.code, name=part.name, group=part.group, group_name=GROUPS[part.group],
                     material=part.material, process=part.process, qty=part.qty, notes=part.notes,
                     bought=part.bought, bbox_mm=[round(bb.xlen, 1), round(bb.ylen, 1), round(bb.zlen, 1)],
                     files={})
        if part.export and not part.bought:
            stp = OUT / "step" / f"{part.code}.step"
            stl = OUT / "stl" / f"{part.code}.stl"
            cq.exporters.export(shape, str(stp))
            cq.exporters.export(shape, str(stl), tolerance=0.05, angularTolerance=0.2)
            entry["files"]["step"] = f"cad/out/step/{part.code}.step"
            entry["files"]["stl"] = f"cad/out/stl/{part.code}.stl"
            if part.dxf:
                dxf = OUT / "dxf" / f"{part.code}.dxf"
                cq.exporters.export(to_flat_for_dxf(shape), str(dxf))
                entry["files"]["dxf"] = f"cad/out/dxf/{part.code}.dxf"

        m_unit = mass_of(part, shape)
        entry["mass_g_unit"] = round(m_unit, 1)
        color = COLORS[part.color or part.material] if (part.color or part.material) in COLORS else COLORS["PETG"]
        instances = []
        for i, pl in enumerate(part.placements):
            inst = place(shape, pl)
            name = f"{part.code}{('_' + pl.tag) if pl.tag else ''}"
            if name in used_names or (not pl.tag and len(part.placements) > 1):
                name = f"{part.code}_{pl.tag + '_' if pl.tag else ''}{i}"
            used_names.add(name)
            assy.add(inst, name=name, color=cq.Color(*color))
            c = inst.val().Center() if part.bought else cq.Shape.centerOfMass(inst.val())
            tot_m += m_unit
            mx += m_unit * c.x
            my += m_unit * c.y
            mz += m_unit * c.z
            instances.append(dict(node=name, center=[round(c.x, 1), round(c.y, 1), round(c.z, 1)]))
        if not part.placements:
            # piezas sin ubicación en el ensamble (p. ej. tacos sueltos): solo cuentan si no están ya dibujadas
            pass
        entry["instances"] = instances
        mass_rows.append((part.code, part.name, len(part.placements), m_unit))
        catalog.append(entry)

    for name, m, (x, y, z) in EXTRA_MASS:
        tot_m += m
        mx += m * x
        my += m * y
        mz += m * z
        mass_rows.append(("—", name, 1, m))

    cg = (mx / tot_m, my / tot_m, mz / tot_m) if tot_m else (0, 0, 0)

    if not only:
        print("  ensamble GLB…", flush=True)
        assy.export(str(OUT / "carpincho.glb"), tolerance=0.4, angularTolerance=0.35)
        if not args.fast:
            print("  ensamble STEP…", flush=True)
            assy.export(str(OUT / "carpincho_ensamble.step"))

        summary = P.summary()
        meta = dict(robot=P.ROBOT_NAME, code=P.ROBOT_CODE,
                    summary={k: round(v, 1) for k, v in summary.items()},
                    mass_total_kg=round(tot_m / 1000, 2), cg_mm=[round(v, 1) for v in cg],
                    groups=GROUPS, parts=catalog)
        (OUT / "parts.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        write_mass_report(mass_rows, tot_m, cg, summary)
        write_xacro(summary, tot_m, cg)

    print(f"listo en {time.time() - t0:.0f} s — masa estimada {tot_m / 1000:.2f} kg, "
          f"CG = ({cg[0]:.0f}, {cg[1]:.0f}, {cg[2]:.0f}) mm")


def write_mass_report(rows, tot_m, cg, summary) -> None:
    lines = ["# Presupuesto de masa y centro de gravedad", "",
             "_Archivo generado por `cad/build.py`: no editar a mano._", "",
             f"**Masa total estimada: {tot_m / 1000:.2f} kg**  ",
             f"**CG (base_footprint): x = {cg[0]:.0f} mm, y = {cg[1]:.0f} mm, z = {cg[2]:.0f} mm**", "",
             "| Código | Pieza | Cant. | g/u | g total |", "|---|---|---:|---:|---:|"]
    for code, name, n, m in sorted(rows, key=lambda r: -r[2] * r[3]):
        if n == 0:
            continue
        lines.append(f"| {code} | {name} | {n} | {m:.0f} | {n * m:.0f} |")
    # margen de vuelco estático en escalera
    half_base = P.AXLE_DIST / 2
    ang_tip = math.degrees(math.atan2(half_base - cg[0], cg[2]))   # vuelco hacia atrás subiendo de frente
    lines += ["", "## Estabilidad estática (solo orugas, flippers sin apoyar)", "",
              f"- Ángulo de vuelco hacia atrás subiendo de frente: **{ang_tip:.0f}°** "
              f"(escalera del reglamento: hasta 45°; con flippers apoyados el margen crece).",
              f"- Ángulo de vuelco lateral: **{math.degrees(math.atan2(P.Y_TRACK_C, cg[2])):.0f}°**.",
              "", "Si cambiás posiciones de batería/electrónica en `params.py`, volvé a correr el build."]
    (OUT / "masa_cg.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_xacro(s, tot_m, cg) -> None:
    XACRO.parent.mkdir(parents=True, exist_ok=True)
    m = lambda v: f"{v / 1000:.4f}"
    props = {
        "axle_dist": m(s["axle_dist"]), "axle_z": m(s["axle_z"]), "track_pd": m(s["track_pd"]),
        "track_w": m(P.TRACK_BELT_W), "track_y": m(s["y_track_c"]), "flip_y": m(s["y_flip_c"]),
        "flip_len": m(s["flip_len"]), "flip_tip_pd": m(P.FLIP_TIP_PD), "body_len": m(P.BODY_LEN),
        "body_w": m(2 * P.Y_SIDE_OUT), "body_bottom_z": m(P.BODY_BOTTOM_Z), "body_top_z": m(P.BODY_TOP_Z),
        "deck_t": m(P.DECK_T), "grouser_h": m(P.GROUSER_H),
        "mass_total": f"{tot_m / 1000:.3f}", "cg_x": m(cg[0]), "cg_y": m(cg[1]), "cg_z": m(cg[2]),
        "arm_x": m(P.ARM_BASE_X), "arm_base_h": m(P.ARM_BASE_H), "arm_l1": m(P.ARM_L1), "arm_l2": m(P.ARM_L2),
        "arm_l3": m(P.ARM_L3),
        "lidar_x": m(P.LIDAR_POS[0]), "lidar_y": m(P.LIDAR_POS[1]), "lidar_z": m(P.LIDAR_POS[2]),
        "depth_x": m(P.DEPTH_CAM_POS[0]), "depth_y": m(P.DEPTH_CAM_POS[1]), "depth_z": m(P.DEPTH_CAM_POS[2]),
        "thermal_x": m(P.THERMAL_POS[0]), "thermal_y": m(P.THERMAL_POS[1]), "thermal_z": m(P.THERMAL_POS[2]),
        "cam_front_x": m(P.CAM_FRONT_POS[0]), "cam_front_z": m(P.CAM_FRONT_POS[2]),
        "cam_rear_x": m(P.CAM_REAR_POS[0]), "cam_rear_z": m(P.CAM_REAR_POS[2]),
        "flip_min": f"{math.radians(P.FLIP_RANGE[0]):.4f}", "flip_max": f"{math.radians(P.FLIP_RANGE[1]):.4f}",
    }
    body = "\n".join(f'  <xacro:property name="{k}" value="{v}"/>' for k, v in props.items())
    XACRO.write_text(
        '<?xml version="1.0"?>\n<!-- GENERADO por cad/build.py a partir de cad/carpincho_cad/params.py. '
        'No editar a mano. Unidades SI (m, kg, rad). -->\n'
        '<robot xmlns:xacro="http://www.ros.org/wiki/xacro">\n' + body + "\n</robot>\n", encoding="utf-8")


if __name__ == "__main__":
    main()
