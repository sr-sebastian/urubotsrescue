#!/usr/bin/env python3
"""Genera las tablas de la documentación a partir de las fuentes de verdad:

  cad/carpincho_cad/params.py + cad/out/parts.json  ->  docs/03-mecanica/piezas.md
                                                    ->  docs/03-mecanica/calculos.md
  hardware/bom.csv                                  ->  hardware/bom.md

Uso:  python3 tools/gen_docs.py      (correr después de `python cad/build.py`)
No necesita CadQuery: solo lee params.py y parts.json.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("params", ROOT / "cad/carpincho_cad/params.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

G = 9.81


def gen_parts() -> None:
    data = json.loads((ROOT / "cad/out/parts.json").read_text(encoding="utf-8"))
    out = ["# Catálogo de piezas", "",
           "_Generado por `tools/gen_docs.py` desde `cad/out/parts.json`. No editar a mano._", "",
           f"Robot **{data['robot']} {data['code']}** · masa estimada **{data['mass_total_kg']} kg** · "
           f"CG = {data['cg_mm']} mm (en `base_footprint`).", "",
           "Los archivos están en `cad/out/` (STEP para editar/inspeccionar, STL para imprimir, DXF para cortar). "
           "Las piezas marcadas *L/R* se usan a ambos lados: la del lado derecho es la misma pieza espejada "
           "(en placas planas, la misma pieza dada vuelta).", ""]
    for g, gname in data["groups"].items():
        items = [p for p in data["parts"] if p["group"] == g]
        if not items:
            continue
        out += [f"## {gname}", "", "| Código | Pieza | Cant. | Material | Fabricación | Medidas (mm) | g/u | Archivos | Notas |",
                "|---|---|---:|---|---|---|---:|---|---|"]
        for p in items:
            files = " ".join(f"[{k.upper()}](../../{v})" for k, v in p.get("files", {}).items()) or "—"
            dims = " × ".join(str(round(v)) for v in p["bbox_mm"])
            out.append(f"| {p['code']} | {p['name']} | {p['qty']} | {p['material']} | {p['process']} | {dims} | "
                       f"{p['mass_g_unit']:.0f} | {files} | {p['notes'] or ''} |")
        out.append("")
    out += ["## Parámetros de impresión 3D recomendados", "",
            "| Material | Uso | Boquilla | Capa | Perímetros | Relleno | Notas |",
            "|---|---|---|---|---:|---|---|",
            "| PLA-CF | poleas, soportes de motor, brazo | 0.6 mm acero endurecido | 0.24 | 5-6 | 50-60 % gyroid | secar el filamento 6 h a 50 °C |",
            "| PETG | rodillos, separadores, cajas | 0.4/0.6 | 0.2-0.28 | 4 | 30-40 % | |",
            "| TPU 95A | tacos de oruga | 0.4 | 0.2 | — | 100 % | imprimir lento (20-25 mm/s), sin retracción |",
            "", "**Insertos térmicos M3/M4** en vez de tuercas cautivas siempre que se pueda."]
    (ROOT / "docs/03-mecanica/piezas.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def gen_bom() -> None:
    rows = list(csv.DictReader(open(ROOT / "hardware/bom.csv", encoding="utf-8")))
    tot = 0.0
    by: dict[str, float] = {}
    lines = ["# Lista de materiales (BOM)", "", "_Generado desde `hardware/bom.csv` por `tools/gen_docs.py`._", "",
             "Precios **orientativos en USD** (oct. 2026, sin envío ni impuestos). Antes de comprar, "
             "confirmar disponibilidad y tiempos de envío a Uruguay: lo importado puede tardar 4-8 semanas.", "",
             "| Subsistema | Ítem | Especificación | Cant. | USD c/u | USD total | Notas |",
             "|---|---|---|---:|---:|---:|---|"]
    for r in rows:
        t = float(r["cantidad"]) * float(r["usd_unit"])
        tot += t
        by[r["subsistema"]] = by.get(r["subsistema"], 0) + t
        lines.append(f"| {r['subsistema']} | {r['item']} | {r['especificacion']} | {r['cantidad']} | "
                     f"{float(r['usd_unit']):.0f} | {t:.0f} | {r['notas']} |")
    lines += ["", "## Resumen por subsistema", "", "| Subsistema | USD |", "|---|---:|"]
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {k} | {v:.0f} |")
    lines += [f"| **Total** | **{tot:.0f}** |", "",
              "## Si el presupuesto no alcanza", "",
              "- **LiDAR**: un LiDAR 2D barato (≈ 100-200 USD) + la cámara de profundidad para la nube 3D "
              "(RTAB-Map). Se pierde calidad en el PLY del laberinto y FAST-LIO deja de servir en rampas.",
              "- **Térmica**: MLX90640 (32x24, ≈60 USD) por I2C. Alcanza para la firma de calor, "
              "pero es justo para los anillos concéntricos de la prueba de agudeza térmica.",
              "- **Cómputo**: no bajar de la clase Orin Nano: FAST-LIO + YOLO + cámaras a la vez necesitan GPU y "
              "8 GB. Para desarrollar sirve cualquier PC con Ubuntu 24.04 + `tools/fake_base.py`.",
              "- **Brazo**: imprimir un SO-101 (también usa STS3215) para empezar a practicar destreza mientras se "
              "fabrica el C1."]
    (ROOT / "hardware/bom.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def gen_calcs() -> None:
    m = 20.0                                    # kg, masa de diseño (con margen sobre la estimada)
    r = (P.TRACK_PD / 2) / 1000                 # radio primitivo
    stair = math.radians(45)
    f_climb = m * G * math.sin(stair) * 1.3     # 30 % de pérdidas (correa, rodillos, tacos)
    t_side = f_climb * r / 2                    # por oruga
    belt = P.DRIVE_RED_BIG_T / P.DRIVE_RED_SMALL_T
    rpm_motor_out = P.MOTOR_RPM_24V / P.DRIVE_GEARBOX
    v_max = rpm_motor_out / belt * 2 * math.pi / 60 * r
    t_gear_nom = P.MOTOR_T_NOM * P.DRIVE_GEARBOX * 0.80   # η 80 %
    t_side_avail = t_gear_nom * belt
    t_stall_side = 1.0 * P.DRIVE_GEARBOX * 0.8 * belt

    flip_l = P.FLIP_LEN / 1000
    t_flip_need = 0.5 * m * G * flip_l          # levantar la mitad delantera con la punta del flipper
    flip_red = P.FLIP_RED_BIG_T / P.FLIP_RED_SMALL_T
    t_flip_avail = P.MOTOR_T_NOM * P.FLIP_GEARBOX * 0.70 * flip_red
    flip_speed = P.MOTOR_RPM_24V / P.FLIP_GEARBOX / flip_red * 6      # deg/s

    riser, going = 0.20, 0.20
    nosing = math.hypot(riser, going)
    contact = (P.AXLE_DIST + P.FLIP_LEN) / 1000

    p_avg = {"Jetson Orin Nano (modo 25 W, promedio)": 18, "Livox Mid-360": 6.5, "Cámara de profundidad": 2.5,
             "Térmica + 3 cámaras USB": 4, "Router 5 GHz": 6, "ESP32 + sensores + LEDs": 4,
             "Brazo (promedio en tareas)": 15, "Tracción (promedio en carriles)": 60, "Flipper (promedio)": 8}
    e_batt = 21.6 * 10.0 * 0.85                 # Wh útiles (85 % DoD)
    p_tot = sum(p_avg.values())

    L = ["# Cálculos de diseño", "", "_Generado por `tools/gen_docs.py` desde `params.py`. Valores de diseño: "
         "validarlos midiendo en el prototipo (ver docs/07-pruebas)._", "",
         "## 1. Geometría principal", "",
         "| Magnitud | Valor |", "|---|---:|"]
    for k, v in P.summary().items():
        L.append(f"| {k} | {v:.1f} mm |")
    L += ["", "Las correas son de largo comercial y las distancias entre ejes se **calculan** para que calcen "
          "(`params.center_for_belt`):", "",
          f"- Oruga principal: HTD 1100-5M sobre 2 poleas de 60T → distancia entre ejes {P.AXLE_DIST:.1f} mm.",
          f"- Flipper: HTD 760-5M sobre 60T + 36T → largo de flipper {P.FLIP_LEN:.1f} mm.",
          f"- Altura de eje sobre el piso (con tacos de {P.GROUSER_H:.0f} mm): {P.AXLE_Z:.1f} mm.",
          "", "## 2. Tracción (subir escalera de 45° con 20 kg)", "",
          f"- Fuerza para subir: m·g·sen45°·1.3 = **{f_climb:.0f} N**",
          f"- Torque por oruga en la polea (r = {r * 1000:.1f} mm): **{t_side:.2f} N·m**",
          f"- Disponible por oruga (775 + 1:{P.DRIVE_GEARBOX}, η 80 %, correa {belt:.1f}:1): nominal ≈ **{t_side_avail:.1f} N·m**, "
          f"arranque ≈ {t_stall_side:.0f} N·m → margen nominal {t_side_avail / t_side:.1f}×",
          f"- Velocidad máxima sin carga: **{v_max:.2f} m/s** (el firmware limita a 0.4 m/s)",
          "- Historia: la v0 usaba 1:27 (0.74 m/s) y daba solo 0.8× del torque nominal necesario: se pasó a 1:51.",
          "- Corriente: en escalera cada motor tira ≈ 6-9 A (MDD20A soporta 20 A continuos por canal).",
          "", "## 3. Flipper", "",
          f"- Torque para levantar la mitad delantera (palanca {flip_l * 1000:.0f} mm): **{t_flip_need:.1f} N·m**",
          f"- Disponible (775 + 1:{P.FLIP_GEARBOX}, η 70 %, correa {flip_red:.2f}:1): ≈ **{t_flip_avail:.0f} N·m** nominal",
          f"- Velocidad: ≈ {flip_speed:.0f} °/s (90° en ≈ {90 / flip_speed:.1f} s)",
          "- Protección: la correa HTD 15 mm salta antes de romper la reductora, y el firmware corta por atasco "
          "(1.5 s sin moverse con >50 % de PWM).",
          "", "## 4. Escaleras del reglamento (45°, contrahuella 20 cm)", "",
          f"- Distancia entre narices de escalón sobre la pendiente: {nosing * 1000:.0f} mm",
          f"- Largo de apoyo con flippers extendidos: {contact * 1000:.0f} mm → apoya en "
          f"**{contact / nosing:.1f} narices** a la vez (≥ 2 = no se hamaca).",
          "- Ver `cad/out/masa_cg.md` para el ángulo de vuelco con el CG actual.",
          "", "## 5. Autonomía eléctrica", "",
          "| Consumo | W |", "|---|---:|"]
    for k, v in p_avg.items():
        L.append(f"| {k} | {v} |")
    L += [f"| **Total promedio** | **{p_tot:.0f}** |", "",
          f"Batería 6S2P 21700 (21.6 V × 10 Ah, 85 % útil) = {e_batt:.0f} Wh → **≈ {e_batt / p_tot * 60:.0f} min** "
          "de uso continuo. Una prueba dura 20 min: con 3 baterías alcanza para todo el día rotando la carga.",
          "", "Picos: tracción en escalera ≈ 2 × 9 A + flipper 6 A + brazo 4 A + electrónica 3 A ≈ **31 A** "
          "→ fusible principal de 40 A y BMS de ≥ 40 A continuos.",
          "", "## 6. Brazo (STS3215 a 12 V: 2.9 N·m de arranque)", ""]
    import sys
    sys.path.insert(0, str(ROOT / "ros2_ws/src/carpincho_arm"))
    from carpincho_arm.kinematics import ArmGeometry, fk, static_torques   # noqa: E402
    g = ArmGeometry()
    t2, t3 = static_torques([0, math.pi / 2, 0, 0, 0], g)
    reach = fk([0, math.pi / 2, 0, 0, 0], g)[0]
    L += [f"- Brazo horizontal extendido con 200 g en la punta: hombro **{t2:.1f} N·m**, codo **{t3:.1f} N·m**.",
          f"- Hombro: 2 servos × 2.9 N·m × {P.ARM_SHOULDER_RED:.0f}:1 = {2 * 2.9 * P.ARM_SHOULDER_RED:.1f} N·m "
          f"de arranque ({t2 / (2 * 2.9 * P.ARM_SHOULDER_RED) * 100:.0f} % usado).",
          f"- Codo: 1 servo × 2.9 × {P.ARM_ELBOW_RED:.0f}:1 = {2.9 * P.ARM_ELBOW_RED:.1f} N·m "
          f"({t3 / (2.9 * P.ARM_ELBOW_RED) * 100:.0f} % usado).",
          "- Regla práctica: no sostener el brazo totalmente horizontal más de ~30 s (los STS se calientan); "
          "trabajar con el codo flexionado.",
          f"- Alcance horizontal desde el eje J1: {reach * 1000:.0f} mm. Altura máxima de la punta sobre el piso: "
          f"{(P.BODY_TOP_Z + P.DECK_T + P.ARM_BASE_H + P.ARM_L1 + P.ARM_L2 + P.ARM_L3) / 1000:.2f} m "
          "(carriles lineales a 0.60 m: OK; picaportes a 0.9-1.2 m: solo en el límite).",
          "- Carga útil máxima recomendada: 300 g (el desafío de carga del reglamento con objetos de varios kg "
          "**no** es objetivo de esta versión)."]
    (ROOT / "docs/03-mecanica/calculos.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    (ROOT / "docs/03-mecanica").mkdir(parents=True, exist_ok=True)
    gen_parts()
    gen_bom()
    gen_calcs()
    print("docs generadas: docs/03-mecanica/piezas.md, docs/03-mecanica/calculos.md, hardware/bom.md")
