"""Utilidades comunes del CAD: registro de piezas, perfiles de poleas, patrones."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import cadquery as cq

from . import params as P

# ---------------------------------------------------------------------------
# Registro de piezas
# ---------------------------------------------------------------------------

# colores (r, g, b) 0..1 por material / función, usados en el GLB del visor
COLORS = {
    "Al": (0.72, 0.74, 0.78),
    "Al_dark": (0.35, 0.37, 0.42),
    "PETG": (0.95, 0.55, 0.10),     # naranja UruBots-ish
    "PLA-CF": (0.18, 0.18, 0.20),
    "TPU": (0.10, 0.10, 0.10),
    "PC": (0.75, 0.85, 0.95),
    "steel": (0.55, 0.56, 0.58),
    "belt": (0.08, 0.08, 0.08),
    "elec": (0.10, 0.45, 0.25),
    "motor": (0.25, 0.27, 0.30),
    "sensor": (0.15, 0.30, 0.65),
    "red": (0.85, 0.10, 0.10),
    "yellow": (0.95, 0.80, 0.10),
}

GROUPS = {
    "chasis": "Chasis y estructura",
    "traccion": "Tren motriz y orugas",
    "flipper": "Flippers",
    "brazo": "Brazo manipulador",
    "electronica": "Electrónica y potencia",
    "sensores": "Sensores",
    "referencia": "Componentes comprados (referencia)",
}


@dataclass
class Placement:
    """Ubicación de una instancia en el ensamble: rotaciones (grados) y traslación."""

    pos: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rot: tuple[float, float, float] = (0.0, 0.0, 0.0)  # Rx, Ry, Rz aplicados en ese orden
    mirror_y: bool = False
    tag: str = ""                                         # ej. "L", "R"
    # cadena cinemática aplicada DESPUÉS: [(punto, eje, ángulo_grados), ...] en orden de aplicación
    chain: tuple = ()


@dataclass
class Part:
    code: str                    # ej. "CH-01"
    name: str                    # nombre en castellano
    group: str                   # clave de GROUPS
    make: Callable[[], cq.Workplane]
    material: str                # clave de COLORS / DENSITY
    process: str                 # cómo se fabrica
    placements: list[Placement] = field(default_factory=list)
    notes: str = ""
    export: bool = True          # exportar STL/STEP de fabricación
    dxf: bool = False            # además exportar DXF 2D (placas para láser)
    bought: bool = False         # componente comprado (solo referencia visual)
    color: str | None = None
    qty_override: int | None = None

    @property
    def qty(self) -> int:
        if self.qty_override is not None:
            return self.qty_override
        return max(1, len(self.placements))


def place(shape: cq.Workplane, pl: Placement) -> cq.Workplane:
    s = shape
    rx, ry, rz = pl.rot
    if rx:
        s = s.rotate((0, 0, 0), (1, 0, 0), rx)
    if ry:
        s = s.rotate((0, 0, 0), (0, 1, 0), ry)
    if rz:
        s = s.rotate((0, 0, 0), (0, 0, 1), rz)
    s = s.translate(pl.pos)
    for pt, axis, ang in pl.chain:
        if ang:
            s = s.rotate(pt, (pt[0] + axis[0], pt[1] + axis[1], pt[2] + axis[2]), ang)
    if pl.mirror_y:          # espejo de la instancia ya ubicada (lado derecho)
        s = s.mirror("XZ")
    return s


# ---------------------------------------------------------------------------
# Geometría auxiliar
# ---------------------------------------------------------------------------

def htd5_pulley(teeth: int, width: float, bore: float, flange: bool = True,
                hub_d: float = 0.0, hub_l: float = 0.0) -> cq.Workplane:
    """Polea HTD 5M aproximada, eje a lo largo de Z, cara inferior en z=0.

    Ranura de diente aproximada por un arco (r=1.55 mm). Para piezas impresas
    sirve; para competencia conviene comprar poleas de aluminio y adaptar el cubo.
    """
    od = P.htd5_od(teeth)
    r_groove = 1.55
    c_r = od / 2 - 2.06 + r_groove
    body = cq.Workplane("XY").circle(od / 2).extrude(width)
    grooves = (cq.Workplane("XY").polarArray(c_r, 0, 360, teeth)
               .circle(r_groove).extrude(width))
    body = body.cut(grooves)
    z0 = 0.0
    if flange:
        fl = cq.Workplane("XY").circle(od / 2 + P.PULLEY_FLANGE_EXTRA).extrude(P.PULLEY_FLANGE_T)
        body = (body.translate((0, 0, P.PULLEY_FLANGE_T))
                .union(fl)
                .union(fl.translate((0, 0, width + P.PULLEY_FLANGE_T))))
        z0 = width + 2 * P.PULLEY_FLANGE_T
    else:
        z0 = width
    if hub_d and hub_l:
        hub = cq.Workplane("XY").circle(hub_d / 2).extrude(hub_l).translate((0, 0, z0))
        body = body.union(hub)
    total = z0 + (hub_l if hub_d else 0)
    body = body.cut(cq.Workplane("XY").circle(bore / 2).extrude(total))
    return body


def lightening_holes(wp: cq.Workplane, pts, d: float, depth: float) -> cq.Workplane:
    return wp.cut(cq.Workplane("XY").pushPoints(pts).circle(d / 2).extrude(depth))


def plate_xz(outline_pts, thickness: float) -> cq.Workplane:
    """Placa en el plano XZ (espesor hacia +Y). outline_pts en (x, z)."""
    return (cq.Workplane("XZ").polyline(outline_pts).close().extrude(-thickness))


def holes_xz(plate: cq.Workplane, pts_xz, d: float, thickness: float, y0: float = 0.0) -> cq.Workplane:
    cutters = (cq.Workplane("XZ", origin=(0, y0, 0)).pushPoints(pts_xz)
               .circle(d / 2).extrude(-thickness))
    return plate.cut(cutters)


def rounded_box(x: float, y: float, z: float, r: float = 2.0) -> cq.Workplane:
    b = cq.Workplane("XY").box(x, y, z)
    try:
        b = b.edges("|Z").fillet(r)
    except Exception:  # pragma: no cover - fillet puede fallar en cajas chicas
        pass
    return b


def gear_simple(teeth: int, module: float, width: float, bore: float) -> cq.Workplane:
    """Engranaje recto simplificado (dientes trapezoidales) para impresión 3D."""
    rp = teeth * module / 2
    ra = rp + module
    rf = rp - 1.25 * module
    pts = []
    for i in range(teeth):
        a0 = 2 * math.pi * i / teeth
        da = 2 * math.pi / teeth
        for frac, r in ((0.0, rf), (0.18, rf), (0.32, ra), (0.68, ra), (0.82, rf)):
            a = a0 + frac * da
            pts.append((r * math.cos(a), r * math.sin(a)))
    g = cq.Workplane("XY").polyline(pts).close().extrude(width)
    return g.cut(cq.Workplane("XY").circle(bore / 2).extrude(width))
