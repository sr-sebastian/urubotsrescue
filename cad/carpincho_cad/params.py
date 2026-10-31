"""Parámetros maestros del robot Carpincho (URB-R1).

ÚNICA fuente de verdad geométrica. Todo lo demás (piezas CAD, URDF, cálculos,
documentación) se deriva de acá. Si cambiás un número, corré `python cad/build.py`
y se regeneran STEP/STL/DXF, el visor 3D y `params.xacro` del URDF.

Unidades: milímetros, grados, gramos.
Ejes (igual que ROS / REP-103): X adelante, Y izquierda, Z arriba.
Origen del ensamble: en el piso, bajo el punto medio entre eje delantero y trasero,
centrado en Y (= frame `base_footprint`).
"""

from dataclasses import dataclass, field
import math

# ---------------------------------------------------------------------------
# Correa dentada HTD 5M (usada como oruga y para transmisiones internas)
# ---------------------------------------------------------------------------
HTD5_PITCH = 5.0          # paso de la correa [mm]
HTD5_BELT_T = 3.8         # espesor total de la correa (dientes incluidos)
HTD5_PLD = 1.14           # distancia línea primitiva -> fondo de diente


def htd5_pd(teeth: int) -> float:
    """Diámetro primitivo de una polea HTD 5M."""
    return teeth * HTD5_PITCH / math.pi


def htd5_od(teeth: int) -> float:
    """Diámetro exterior (aprox.) de una polea HTD 5M."""
    return htd5_pd(teeth) - 2 * HTD5_PLD


def belt_length_open(c: float, d1: float, d2: float) -> float:
    """Largo primitivo de correa abierta entre dos poleas (fórmula estándar)."""
    return 2 * c + math.pi * (d1 + d2) / 2 + (d1 - d2) ** 2 / (4 * c)


def center_for_belt(length: float, d1: float, d2: float) -> float:
    """Distancia entre centros que da un largo de correa dado (Newton)."""
    c = (length - math.pi * (d1 + d2) / 2) / 2
    for _ in range(30):
        f = belt_length_open(c, d1, d2) - length
        df = 2 - (d1 - d2) ** 2 / (4 * c * c)
        c -= f / df
    return c


# ---------------------------------------------------------------------------
# Tren motriz principal (orugas)
# ---------------------------------------------------------------------------
TRACK_PULLEY_T = 60                 # dientes polea de oruga (delantera y trasera)
TRACK_PD = htd5_pd(TRACK_PULLEY_T)  # ~95.5 mm
TRACK_BELT_LEN = 1100.0             # correa HTD 1100-5M (220 dientes), ancho 25
TRACK_BELT_W = 25.0
AXLE_DIST = center_for_belt(TRACK_BELT_LEN, TRACK_PD, TRACK_PD)  # = 400 mm
GROUSER_H = 8.0                     # altura de los tacos de TPU
GROUSER_PITCH_TEETH = 4             # un taco cada 4 dientes (20 mm)

# altura del eje sobre el piso (piso = punta de los tacos)
AXLE_Z = TRACK_PD / 2 + (HTD5_BELT_T - HTD5_PLD) + GROUSER_H

# Polea de oruga: ancho del cubo y pestañas
PULLEY_W = TRACK_BELT_W + 2.0       # zona dentada
PULLEY_FLANGE_T = 2.0
PULLEY_FLANGE_EXTRA = 4.0           # cuánto sobresale la pestaña sobre el OD

# Rodillos de apoyo inferiores (dentro del lazo de la oruga)
ROLLER_D = 40.0
ROLLER_X = (-100.0, 0.0, 100.0)     # posiciones en X
ROLLER_Z = GROUSER_H + HTD5_BELT_T + ROLLER_D / 2  # apoyan sobre el tramo inferior

# ---------------------------------------------------------------------------
# Cuerpo / chasis
# ---------------------------------------------------------------------------
BODY_INNER_W = 230.0                # distancia interna entre placas laterales
SIDE_PLATE_T = 4.0                  # aluminio 5052/6061 4 mm (corte láser/CNC)
OUTER_PLATE_T = 3.0                 # placa exterior de oruga, aluminio 3 mm
BODY_BOTTOM_Z = 30.0                # despeje del piso del cuerpo
BODY_TOP_Z = 190.0                  # cara superior de las placas laterales
BODY_LEN = AXLE_DIST + 90.0         # largo de placas laterales (sobresale de ejes)
FLOOR_T = 3.0                       # piso de aluminio 3 mm
DECK_T = 4.0                        # tapa superior (policarbonato 4 mm o Al 3 mm)

GAP_PLATE_PULLEY = 3.0              # luz entre placa y polea

# Coordenadas Y (cara interior de placa lateral y centros de oruga)
Y_SIDE_IN = BODY_INNER_W / 2
Y_SIDE_OUT = Y_SIDE_IN + SIDE_PLATE_T
Y_TRACK_C = Y_SIDE_OUT + GAP_PLATE_PULLEY + PULLEY_FLANGE_T + PULLEY_W / 2
Y_TRACK_OUT = Y_TRACK_C + PULLEY_W / 2 + PULLEY_FLANGE_T
Y_OUTER_PLATE_IN = Y_TRACK_OUT + GAP_PLATE_PULLEY

# ---------------------------------------------------------------------------
# Flippers delanteros (pivotan en el eje delantero)
# ---------------------------------------------------------------------------
FLIP_TUBE_OD = 20.0                 # tubo Al 6061 20x2 (eje de flippers)
FLIP_TUBE_ID = 16.0
FLIP_BEARING = "6804-2RS"           # 20x32x7 (en placas y dentro de poleas)
FLIP_TIP_T = 36
FLIP_TIP_PD = htd5_pd(FLIP_TIP_T)   # ~57.3 mm
FLIP_BELT_LEN = 760.0               # HTD 760-5M, ancho 25
FLIP_LEN = center_for_belt(FLIP_BELT_LEN, TRACK_PD, FLIP_TIP_PD)  # ~259 mm
FLIP_PLATE_T = 5.0                  # brazo de flipper: Al 5 mm
FLIP_TIP_AXLE_D = 10.0
# Y del tramo de flipper (por fuera de la oruga principal, misma polea compuesta)
Y_FLIP_C = Y_TRACK_OUT + GAP_PLATE_PULLEY + PULLEY_FLANGE_T + PULLEY_W / 2
Y_FLIP_OUT = Y_FLIP_C + PULLEY_W / 2 + PULLEY_FLANGE_T
Y_FLIP_PLATE_IN = Y_FLIP_OUT + GAP_PLATE_PULLEY
FLIP_HUB_T = 12.0                   # cubo del flipper por fuera de la placa
Y_TOTAL = Y_FLIP_PLATE_IN + FLIP_PLATE_T + FLIP_HUB_T
FLIP_ANGLE_STOW = 15.0              # [deg] pose de manejo normal (punta levantada)
FLIP_RANGE = (-100.0, 190.0)        # [deg] rango mecánico permitido (0 = horizontal adelante)

# Reducción del flipper: motor -> tubo por correa HTD 5M 15 mm.
# La polea del tubo NO puede ser grande: el tubo está a 58 mm del piso y el piso del cuerpo a 33 mm.
# 30T (Ø ext. ≈ 53 con pestañas) pasa por una ranura de alivio en el piso (CH-03).
FLIP_RED_SMALL_T = 14
FLIP_RED_BIG_T = 30

# ---------------------------------------------------------------------------
# Transmisión de tracción: motor (adentro, escalonado) -> eje trasero por correa
# ---------------------------------------------------------------------------
DRIVE_SHAFT_D = 12.0                # eje acero 12 mm (rodamientos KFL001 / 6001)
DRIVE_RED_SMALL_T = 20
DRIVE_RED_BIG_T = 30                # 1.5:1
DRIVE_INNER_BELT_W = 15.0

# Motores (775 + reductora planetaria 42 mm). Medidas típicas: VERIFICAR con el motor real.
DRIVE_GEARBOX = 51                  # reductora planetaria de tracción (1:51)
FLIP_GEARBOX = 264                  # reductora del flipper (1:264, planetaria de 56 mm: par nominal ≥ 20 N·m)
MOTOR_RPM_24V = 6000.0              # 775 a 24 V en vacío (VERIFICAR: hay 775 de 6000 a 12000 rpm)
MOTOR_T_NOM = 0.10                  # N·m nominal del 775 (continuo)
GM42_D = 42.0
GM42_GEAR_L = 52.0
GM42_MOTOR_D = 44.5
GM42_MOTOR_L = 67.0
GM42_ENC_L = 18.0
GM42_SHAFT_D = 8.0
GM42_SHAFT_L = 30.0                 # pedir eje de salida >= 30 mm (o extensión)
GM42_BOLT_PCD = 32.0                # 4x M4 en PCD 32 (algunos son M3 / PCD 31)
GM42_PILOT_D = 22.0
GM56_D = 56.0                       # reductora planetaria 56 mm para 775 (flipper). VERIFICAR con la real
GM56_GEAR_L = 72.0
GM56_BOLT_PCD = 40.0                # 4x M5 en PCD 40 (típico; hay variantes)
GM56_PILOT_D = 32.0
GM56_SHAFT_D = 12.0

# ---------------------------------------------------------------------------
# Ubicación de componentes internos (x, y, z del centro) para el CG y el visor
# ---------------------------------------------------------------------------
BATTERY = dict(size=(70.0, 150.0, 50.0), pos=(25.0, 0.0, BODY_BOTTOM_Z + FLOOR_T + 25.0),
               mass=1300.0, name="Batería 6S Li-ion 21700 6S2P (≈10 Ah)")
JETSON = dict(size=(103.0, 90.0, 35.0), pos=(-30.0, 0.0, 140.0), mass=280.0,
              name="Jetson Orin Nano Super 8GB (devkit)")
ELECTRONICS_TRAY = dict(size=(200.0, 200.0, 3.0), pos=(-30.0, 0.0, 118.0))

# ---------------------------------------------------------------------------
# Brazo (Feetech STS3215 12 V)
# ---------------------------------------------------------------------------
STS = dict(w=24.7, d=35.0, l=45.2, mass=55.0, stall_nm=2.9)   # dims aprox servo
ARM_BASE_X = 150.0                  # posición del eje J1 sobre el deck
ARM_BASE_H = 85.0                   # altura del eje J2 sobre el deck
ARM_L1 = 260.0                      # hombro -> codo
ARM_L2 = 240.0                      # codo -> muñeca
ARM_L3 = 155.0                      # muñeca -> punta de herramienta
ARM_SHOULDER_RED = 2.0              # GT2 20T -> 40T, 2 servos en paralelo (rango 180°)
ARM_ELBOW_RED = 2.0                 # GT2 20T -> 40T (rango 175°)
ARM_TUBE_OD = 20.0                  # tubo de fibra de carbono 20x18 (o Al 20x1)
GRIPPER_OPEN = 105.0                # apertura máxima (regla RRL: 10 cm)

# ---------------------------------------------------------------------------
# Sensores (posición del origen óptico en base_footprint)
# ---------------------------------------------------------------------------
LIDAR_POS = (-170.0, 0.0, BODY_TOP_Z + 190.0)       # Livox Mid-360 sobre mástil
CAM_FRONT_POS = (BODY_LEN / 2 - 15.0, 0.0, BODY_TOP_Z - 25.0)
DEPTH_CAM_POS = (BODY_LEN / 2 - 15.0, 0.0, BODY_TOP_Z + 45.0)
THERMAL_POS = (BODY_LEN / 2 - 15.0, 62.0, BODY_TOP_Z + 45.0)
CAM_REAR_POS = (-BODY_LEN / 2 + 15.0, 0.0, BODY_TOP_Z - 25.0)
ESTOP_POS = (-BODY_LEN / 2 + 45.0, -75.0, BODY_TOP_Z + DECK_T)
# pose de guardado del brazo (grados): J1 yaw, J2 hombro, J3 codo, J4 muñeca, J5 giro
ARM_STOW = (0.0, -90.0, 140.0, 50.0, 0.0)
ARM_READY = (0.0, 20.0, 60.0, 10.0, 0.0)

# ---------------------------------------------------------------------------
# Presupuesto de masa (g). Se completa en masses.py con los volúmenes del CAD.
# ---------------------------------------------------------------------------
COMPONENT_MASSES = {
    "motor_traccion_x2": 2 * 750.0,
    "motor_flipper": 750.0,
    "bateria": 1300.0,
    "jetson_orin_nano": 280.0,
    "livox_mid360": 265.0,
    "camara_profundidad": 300.0,
    "camara_termica": 60.0,
    "camaras_usb_x3": 3 * 40.0,
    "electronica_varios": 900.0,     # drivers, buck, ESP32, fusibles, cables
    "correas_oruga": 4 * 160.0,
    "tacos_tpu": 4 * 180.0,
    "rodamientos_ejes_buloneria": 1200.0,
    "brazo_completo": 1600.0,
}

DENSITY = {"Al": 2.70e-3, "PETG": 1.27e-3, "PLA-CF": 1.30e-3, "TPU": 1.21e-3,
           "steel": 7.85e-3, "PC": 1.20e-3}   # g/mm^3

ROBOT_NAME = "Carpincho"
ROBOT_CODE = "URB-R1"


def summary() -> dict:
    """Resumen de dimensiones principales (para docs y el URDF)."""
    return {
        "axle_dist": AXLE_DIST,
        "axle_z": AXLE_Z,
        "track_pd": TRACK_PD,
        "body_len": BODY_LEN,
        "length_tracks": AXLE_DIST + TRACK_PD + 2 * (HTD5_BELT_T + GROUSER_H),
        "length_flippers_ext": AXLE_DIST / 2 + FLIP_LEN + FLIP_TIP_PD / 2 + HTD5_BELT_T + GROUSER_H
        + AXLE_DIST / 2 + TRACK_PD / 2 + HTD5_BELT_T + GROUSER_H,
        "width_total": 2 * Y_TOTAL,
        "height_deck": BODY_TOP_Z + DECK_T,
        "flip_len": FLIP_LEN,
        "y_track_c": Y_TRACK_C,
        "y_flip_c": Y_FLIP_C,
    }


if __name__ == "__main__":
    for k, v in summary().items():
        print(f"{k:22s} {v:8.1f} mm")
