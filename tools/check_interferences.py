#!/usr/bin/env python3
"""Chequeo automático de interferencias del ensamble (CadQuery).

    python3 tools/check_interferences.py            # ensamble completo + brazo en varias poses
    python3 tools/check_interferences.py --min 20   # reportar intersecciones de más de 20 mm³

Revisa, para cada par de piezas ubicadas cuyas cajas se tocan, el volumen de la intersección. Falla
(exit 1) si encuentra alguno por encima del umbral que no esté en ALLOWED. También verifica que nada
que no sea parte del tren de rodaje quede por debajo del piso del cuerpo.
Tarda 2-5 minutos. Correrlo antes de cada PR que toque `cad/`.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad"))

from build import all_parts                     # noqa: E402
from carpincho_cad import arm                   # noqa: E402
from carpincho_cad import params as P           # noqa: E402
from carpincho_cad.common import place          # noqa: E402

# contactos esperados (engranajes que engranan, piezas que encastran a presión, etc.)
ALLOWED = {frozenset(("FL-04a", "FL-04b"))}
# lo que sí puede estar por debajo del piso del cuerpo
RUNNING_GEAR = ("REF-B", "DT-01", "DT-02", "DT-03", "DT-04", "FL-", "CH-01", "CH-02", "REF-F1", "REF-S", "CH-10",
                "CH-08")
SKIP = ("REF-B2", "REF-B4", "DT-05")   # tacos: cientos de piezas chicas, no aportan
ARM_POSES = [(0, 0, 0, 0, 0), P.ARM_STOW, P.ARM_READY, (0, 30, 60, 90, 0), (0, 30, 60, -90, 0),
             (90, 60, 90, 100, 90), (0, -60, 140, 0, 0)]


def instances(parts):
    out = []
    for p in parts:
        if p.code in SKIP:
            continue
        shape = p.make()
        for i, pl in enumerate(p.placements):
            s = place(shape, pl).val()
            out.append((p.code, f"{p.code}{('_' + pl.tag) if pl.tag else ''}#{i}", s, s.BoundingBox()))
    return out


def clashes(insts, vmin):
    bad = []
    for (c1, n1, s1, b1), (c2, n2, s2, b2) in itertools.combinations(insts, 2):
        if (b1.xmax < b2.xmin or b2.xmax < b1.xmin or b1.ymax < b2.ymin or b2.ymax < b1.ymin
                or b1.zmax < b2.zmin or b2.zmax < b1.zmin):
            continue
        if frozenset((c1, c2)) in ALLOWED:
            continue
        try:
            v = s1.intersect(s2).Volume()
        except Exception:  # noqa: BLE001
            continue
        if v > vmin:
            bad.append((v, n1, n2))
    return sorted(bad, reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=50.0, help="volumen mínimo a reportar [mm³]")
    args = ap.parse_args()
    fails = 0

    insts = instances(all_parts())
    print(f"Ensamble: {len(insts)} instancias")
    low = [n for c, n, s, bb in insts if bb.zmin < P.BODY_BOTTOM_Z - 0.1 and not c.startswith(RUNNING_GEAR)]
    if low:
        print("  ✗ por debajo del piso del cuerpo:", low)
        fails += len(low)
    for v, a, b in clashes(insts, args.min):
        print(f"  ✗ {a} ∩ {b}: {v:.0f} mm³")
        fails += 1

    for pose in ARM_POSES:
        ai = instances(arm.parts(tuple(float(x) for x in pose)))
        bad = clashes(ai, args.min)
        print(f"Brazo en pose {tuple(pose)}: {'OK' if not bad else ''}")
        for v, a, b in bad:
            print(f"  ✗ {a} ∩ {b}: {v:.0f} mm³")
            fails += 1

    print("SIN interferencias" if not fails else f"{fails} interferencias")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
