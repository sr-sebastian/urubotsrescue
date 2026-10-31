"""Exportación de resultados con el formato del reglamento RoboCup Rescue (2026).

- CSV de objetos identificados  (RoboCup[Año]-[Equipo]-[Misión]-[HH-MM-SS]-pois.csv)
- Nube de puntos PLY ASCII       (RoboCup[Año]-[Equipo]-[Misión]-[HH-MM-SS]-map.ply)
- Mapa 2D "GeoTIFF" con colores   (RoboCup[Año]-[Equipo]-[Misión].tiff)

Python puro + numpy (sin ROS ni OpenCV) para poder testearlo. El nodo mission_exporter guarda
la imagen con OpenCV.

Convenciones del reglamento:
  * Mapa 2D: X hacia ARRIBA en la imagen, Y hacia la IZQUIERDA (mano derecha), flecha verde en el
    inicio apuntando hacia arriba. Nuestro frame `map` arranca en el inicio con X adelante, así
    que coincide: fila = (x_max - x)/res, columna = (y_max - y)/res.
  * PLY: origen en el centro del FRENTE del robot a nivel del piso, el robot mira hacia +Y, Z arriba.
    Desde `map` (X adelante): p_ply = Rz(+90°) · (p_map - [front_offset, 0, 0]).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np

# ---------------------------------------------------------------- CSV
POI_TYPES = ("ar_code", "hazmat_sign", "real_object", "heat_sig")


@dataclass
class PoiRow:
    detection: int
    time: str          # HH:MM:SS
    type: str
    name: str
    x: float
    y: float
    z: float
    robot: str
    mode: str          # "A" | "T"


def _q(s: str) -> str:
    return '"' + str(s).replace('"', "'") + '"'


def pois_csv(rows: list[PoiRow], team: str, country: str, mission: str, start: datetime,
             version: str = "1.3") -> str:
    head = ["pois", version, team, country, start.strftime("%Y-%m-%d"), start.strftime("%H:%M:%S"), mission]
    lines = [_q(h) for h in head]
    lines.append("detection,time,type,name,x,y,z,robot,mode")
    seen = set()
    for r in rows:
        if r.type not in POI_TYPES:
            continue                       # QR y "motion" no van al CSV del laberinto
        key = (r.type, r.name)
        if key in seen:                    # el reglamento solo cuenta la primera instancia
            continue
        seen.add(key)
        lines.append(f"{r.detection},{r.time},{_q(r.type)},{_q(r.name)},{r.x:.4f},{r.y:.4f},{r.z:.4f},"
                     f"{_q(r.robot)},{r.mode}")
    return "\n".join(lines) + "\n"


def filenames(year: int, team: str, mission: str, start: datetime) -> dict:
    t = start.strftime("%H-%M-%S")
    team_c = team.replace(" ", "")
    base = f"RoboCup{year}-{team_c}-{mission}"
    return {"csv": f"{base}-{t}-pois.csv", "ply": f"{base}-{t}-map.ply", "tiff": f"{base}.tiff"}


# ---------------------------------------------------------------- PLY
def map_to_ply_frame(points: np.ndarray, front_offset: float) -> np.ndarray:
    """(N,3) en frame map -> frame del reglamento (origen frente del robot, robot mirando +Y)."""
    p = points.astype(np.float64).copy()
    p[:, 0] -= front_offset
    out = np.empty_like(p)
    out[:, 0] = -p[:, 1]
    out[:, 1] = p[:, 0]
    out[:, 2] = p[:, 2]
    return out


def voxel_downsample(points: np.ndarray, voxel: float, extra: np.ndarray | None = None):
    """Un punto por vóxel (el primero). Devuelve (puntos, extra filtrado)."""
    if voxel <= 0 or len(points) == 0:
        return points, extra
    keys = np.floor(points / voxel).astype(np.int64)
    _, idx = np.unique(keys, axis=0, return_index=True)
    idx.sort()
    return points[idx], (extra[idx] if extra is not None else None)


def ply_ascii(points: np.ndarray, team: str, start: str, mission: str, rgb: np.ndarray | None = None,
              temp: np.ndarray | None = None) -> str:
    n = len(points)
    hdr = ["ply", "format ascii 1.0", f"comment {team}", f"comment {start}", f"comment {mission}",
           f"element vertex {n}", "property float x", "property float y", "property float z"]
    if rgb is not None:
        hdr += ["property uchar red", "property uchar green", "property uchar blue"]
    if temp is not None:
        hdr += ["property float temp"]
    hdr.append("end_header")
    rows = []
    for i in range(n):
        x, y, z = points[i]
        s = f"{x:.4f} {y:.4f} {z:.4f}"
        if rgb is not None:
            r, g, b = (int(v) for v in rgb[i])
            s += f" {r} {g} {b}"
        if temp is not None:
            s += f" {float(temp[i]):.2f}"
        rows.append(s)
    return "\n".join(hdr + rows) + "\n"


# ---------------------------------------------------------------- mapa 2D
C_FILENAME = (0, 44, 207)
C_SCALE = (0, 50, 140)
C_UNEXP_A = (226, 226, 227)
C_UNEXP_B = (237, 237, 238)
C_GRID = (190, 190, 191)
C_START = (0, 240, 0)
C_WALL = (0, 40, 120)
C_TAG = (255, 200, 0)
C_HAZMAT = (255, 100, 30)
C_OBJECT = (240, 10, 10)
C_PATH = (120, 0, 140)


@dataclass
class GridMap:
    data: np.ndarray        # (H, W) int8: -1 desconocido, 0..100 ocupación (convención ROS)
    resolution: float       # m/celda
    origin_x: float         # posición (m) de la celda [0, 0] en el frame map
    origin_y: float


def render_map(grid: GridMap, path: list[tuple[float, float]], pois: list[PoiRow],
               start_yaw: float = 0.0, margin: float = 1.0, px_per_m: int = 50) -> tuple[np.ndarray, dict]:
    """Devuelve (imagen RGB uint8, transform) siguiendo los colores del reglamento.
    El texto (nombre de archivo, escala) lo agrega el nodo con OpenCV usando `transform`."""
    occ = grid.data
    h, w = occ.shape
    xs = grid.origin_x + (np.arange(w) + 0.5) * grid.resolution    # columnas ROS -> x
    ys = grid.origin_y + (np.arange(h) + 0.5) * grid.resolution    # filas ROS -> y
    known = occ >= 0
    if known.any():
        rr, cc = np.nonzero(known)
        x_min, x_max = xs[cc].min() - margin, xs[cc].max() + margin
        y_min, y_max = ys[rr].min() - margin, ys[rr].max() + margin
    else:
        x_min, x_max, y_min, y_max = -margin, margin, -margin, margin
    # extender a metros enteros para que el damero de 1 m quede alineado
    x_min, y_min = math.floor(x_min), math.floor(y_min)
    x_max, y_max = math.ceil(x_max), math.ceil(y_max)
    H = int((x_max - x_min) * px_per_m)
    W = int((y_max - y_min) * px_per_m)
    img = np.zeros((H, W, 3), np.uint8)

    def to_px(x, y):
        return int((x_max - x) * px_per_m), int((y_max - y) * px_per_m)   # (fila, col)

    # damero de 1 m (zona no explorada)
    rows = np.arange(H)[:, None]
    cols = np.arange(W)[None, :]
    cell = ((rows // px_per_m) + (cols // px_per_m)) % 2
    img[:] = np.where(cell[..., None] == 0, np.array(C_UNEXP_A, np.uint8), np.array(C_UNEXP_B, np.uint8))

    # muestrear la grilla ROS en cada píxel
    px_x = x_max - (rows + 0.5) / px_per_m              # (H,1)
    px_y = y_max - (cols + 0.5) / px_per_m              # (1,W)
    gi = np.floor((px_x - grid.origin_x) / grid.resolution).astype(int)   # columna ROS
    gj = np.floor((px_y - grid.origin_y) / grid.resolution).astype(int)   # fila ROS
    gi_b = np.broadcast_to(gi, (H, W))
    gj_b = np.broadcast_to(gj, (H, W))
    inside = (gi_b >= 0) & (gi_b < w) & (gj_b >= 0) & (gj_b < h)
    vals = np.full((H, W), -1, np.int16)
    vals[inside] = occ[gj_b[inside], gi_b[inside]]
    free = (vals >= 0) & (vals < 50)
    wall = vals >= 50
    # área explorada: gradiente de confianza (0 -> blanco, 49 -> gris 128)
    conf = np.clip(vals, 0, 49).astype(np.float32)
    shade = (255 - conf / 49.0 * 127).astype(np.uint8)
    img[free] = np.stack([shade[free]] * 3, axis=-1)
    # grilla de 50 cm solo en zona explorada
    gmask = free & (((rows % (px_per_m // 2)) == 0) | ((cols % (px_per_m // 2)) == 0))
    img[gmask] = C_GRID
    img[wall] = C_WALL

    # recorrido del robot (~2 cm)
    th = max(1, int(0.02 * px_per_m))
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        _line(img, to_px(x0, y0), to_px(x1, y1), C_PATH, th)

    # inicio: flecha verde apuntando hacia arriba (X)
    if path:
        r0, c0 = to_px(*path[0])
        _arrow_up(img, r0, c0, int(0.4 * px_per_m), C_START)

    marks = []
    for p in pois:
        r, c = to_px(p.x, p.y)
        size = int(0.15 * px_per_m)
        if p.type == "ar_code":
            _disk(img, r, c, int(0.175 * px_per_m), C_TAG)
        elif p.type == "hazmat_sign":
            _diamond(img, r, c, size, C_HAZMAT)
        else:
            _diamond(img, r, c, size, C_OBJECT)
        marks.append((r, c, p))
    tf = dict(x_max=x_max, y_max=y_max, px_per_m=px_per_m, marks=marks)
    return img, tf


def _line(img, p0, p1, color, th):
    (r0, c0), (r1, c1) = p0, p1
    n = max(abs(r1 - r0), abs(c1 - c0), 1)
    for i in range(n + 1):
        r = int(round(r0 + (r1 - r0) * i / n))
        c = int(round(c0 + (c1 - c0) * i / n))
        img[max(0, r - th // 2):r + th // 2 + 1, max(0, c - th // 2):c + th // 2 + 1] = color


def _disk(img, r, c, rad, color):
    H, W = img.shape[:2]
    rr, cc = np.ogrid[:H, :W]
    img[(rr - r) ** 2 + (cc - c) ** 2 <= rad * rad] = color


def _diamond(img, r, c, half, color):
    H, W = img.shape[:2]
    rr, cc = np.ogrid[:H, :W]
    img[np.abs(rr - r) + np.abs(cc - c) <= half] = color


def _arrow_up(img, r, c, length, color):
    _line(img, (r, c), (r - length, c), color, 3)
    for k in range(length // 3):
        img[max(0, r - length + k), max(0, c - k):c + k + 1] = color
