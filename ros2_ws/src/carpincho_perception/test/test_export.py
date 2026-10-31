from datetime import datetime

import numpy as np

from carpincho_perception.poi_store import PoiStore
from carpincho_perception.rrl_export import (C_START, C_WALL, GridMap, PoiRow, filenames, map_to_ply_frame,
                                             ply_ascii, pois_csv, render_map, voxel_downsample)
from carpincho_perception.vision import MotionDetector, bbox_to_point, hot_bbox, largest_blob_bbox

START = datetime(2027, 7, 15, 14, 37, 3)


def test_csv_format_and_dedupe():
    rows = [PoiRow(1, "14:28:01", "ar_code", "2", -8.2992, -2.2904, 0.49, "Carpincho", "A"),
            PoiRow(2, "14:28:02", "ar_code", "2", 0, 0, 0, "Carpincho", "T"),          # repetido
            PoiRow(3, "14:28:05", "hazmat_sign", "poison", -5.7452, -7.0849, 0.213, "Carpincho", "A"),
            PoiRow(4, "14:28:06", "qr_code", "hola", 0, 0, 0, "Carpincho", "T")]       # no va al CSV
    txt = pois_csv(rows, "UruBots", "Uruguay", "Prelim1", START)
    lines = txt.strip().split("\n")
    assert lines[:7] == ['"pois"', '"1.3"', '"UruBots"', '"Uruguay"', '"2027-07-15"', '"14:37:03"', '"Prelim1"']
    assert lines[7] == "detection,time,type,name,x,y,z,robot,mode"
    assert lines[8] == '1,14:28:01,"ar_code","2",-8.2992,-2.2904,0.4900,"Carpincho",A'
    assert len(lines) == 10 and "poison" in lines[9]


def test_filenames():
    n = filenames(2027, "Uru Bots", "Prelim1", START)
    assert n["csv"] == "RoboCup2027-UruBots-Prelim1-14-37-03-pois.csv"
    assert n["ply"].endswith("-14-37-03-map.ply")


def test_ply_frame_convention():
    # robot en el inicio mirando +X en map; un punto 1 m adelante del FRENTE debe quedar en +Y
    p = map_to_ply_frame(np.array([[0.26 + 1.0, 0.0, 0.5]]), front_offset=0.26)
    assert np.allclose(p, [[0.0, 1.0, 0.5]])
    # un punto a la izquierda del robot (+Y map) queda en -X (mano derecha, robot hacia +Y)
    q = map_to_ply_frame(np.array([[0.26, 1.0, 0.0]]), front_offset=0.26)
    assert np.allclose(q, [[-1.0, 0.0, 0.0]])


def test_ply_header():
    txt = ply_ascii(np.zeros((2, 3)), "UruBots", "14:37:03", "Prelim1", rgb=np.array([[1, 2, 3], [4, 5, 6]]))
    head = txt.split("end_header")[0]
    assert "element vertex 2" in head and "property uchar red" in head
    assert txt.strip().split("\n")[-1] == "0.0000 0.0000 0.0000 4 5 6"


def test_voxel():
    pts = np.array([[0, 0, 0], [0.01, 0.01, 0.0], [1, 1, 1]], float)
    out, _ = voxel_downsample(pts, 0.05)
    assert len(out) == 2


def test_render_map_orientation():
    occ = np.full((100, 100), -1, np.int8)     # 5 m x 5 m a 5 cm
    occ[40:60, 40:60] = 0                      # zona libre central
    occ[40:60, 75] = 100                       # pared en x = +1.25 m (adelante)
    grid = GridMap(occ, 0.05, -2.5, -2.5)
    img, tf = render_map(grid, [(0.0, 0.0), (0.5, 0.0)], [])
    ppm, x_max, y_max = tf["px_per_m"], tf["x_max"], tf["y_max"]
    r_wall, c_wall = int((x_max - 1.27) * ppm), int((y_max - 0.0) * ppm)
    assert tuple(img[r_wall, c_wall]) == C_WALL           # la pared está ARRIBA (X hacia arriba)
    r0, c0 = int((x_max - 0.0) * ppm), int((y_max - 0.0) * ppm)
    assert tuple(img[r0 - 3, c0]) == C_START             # flecha verde en el inicio


def test_poi_store_confirms_after_hits():
    s = PoiStore(min_hits=3, radius=0.5)
    assert s.add("hazmat_sign", "poison", 1, 1, 0, 0.9, 0) is None
    assert s.add("hazmat_sign", "poison", 1.1, 1, 0, 0.8, 1) is None
    c = s.add("hazmat_sign", "poison", 0.9, 1, 0, 0.7, 2)
    assert c is not None and c.id == 1 and abs(c.x - 1.0) < 1e-9
    assert s.add("hazmat_sign", "poison", 1, 1, 0, 0.9, 3) is None    # ya confirmado: no se repite


def test_vision_helpers():
    mask = np.zeros((80, 80), bool)
    mask[16:40, 24:48] = True
    assert largest_blob_bbox(mask) == (24, 16, 24, 24)
    md = MotionDetector(alpha=0.5, threshold=20, min_area_frac=0.001)
    a = np.zeros((64, 64), np.uint8)
    b = a.copy()
    b[10:30, 10:30] = 200
    assert md.update(a) is None
    assert md.update(b) is not None
    depth = np.full((100, 100), 1.5, np.float32)
    x, y, z = bbox_to_point(depth, (40, 40, 20, 20), 100, 100, 50, 50)
    assert abs(z - 1.5) < 1e-6 and abs(x) < 1e-6
    t = np.full((24, 32), 22.0, np.float32)
    t[10:16, 10:16] = 36.0
    assert hot_bbox(t) is not None
