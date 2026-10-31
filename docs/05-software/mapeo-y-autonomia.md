# Mapeo y autonomía

## 1. Mapeo 3D y 2D

- **FAST-LIO** (LiDAR-inercial) con el Livox Mid-360. Robusto en rampas, escaleras y grava, donde la
  odometría de orugas no sirve (patina). Publica `/Odometry`, `/cloud_registered` y `/Laser_map`.
- **`odom_relay`** convierte la pose de FAST-LIO (frame del LiDAR) en `odom→base_footprint` y publica las TF
  estáticas `odom→camera_init` y `livox_frame→body`. `/scan` sale de `/cloud_registered_body`.
- **octomap_server** proyecta la nube registrada a una grilla 2D → `/map` (5 cm) para el GeoTIFF y Nav2.
- Config: [`carpincho_bringup/config/fast_lio_mid360.yaml`](../../ros2_ws/src/carpincho_bringup/config/fast_lio_mid360.yaml).
  Lo más importante: `blind: 0.30` (que no mapee el propio robot) y los extrínsecos LiDAR↔IMU del Mid-360.

### Entregables del laberinto

```bash
ros2 service call /mission/start std_srvs/srv/Trigger     # en la posición de inicio, ANTES de mover
# ... exploración (teleop o autónoma) ...
ros2 service call /mission/export std_srvs/srv/Trigger    # genera los 3 archivos
./operator/fetch_mission.sh                              # los copia a la notebook (hay 5 min)
```

| Archivo | Contenido | Detalle |
|---|---|---|
| `RoboCup2027-UruBots-<Misión>.tiff` | mapa 2D | Damero de 1 m, grilla de 50 cm, paredes azul oscuro, recorrido magenta, flecha verde, POIs con sus colores, escala de 1 m, ejes X↑ Y← |
| `...-<HH-MM-SS>-map.ply` | nube 3D ASCII | Origen en el **frente** del robot al inicio (`front_offset: 0.26`), robot mirando +Y, Z arriba, vóxel de 3 cm |
| `...-<HH-MM-SS>-pois.csv` | objetos | Encabezado del reglamento, una fila por objeto único, modo A/T |

> **Bonus del PLY**: color ×1.25 y temperatura ×1.6 (×2 con los dos). Próximo paso: colorear la nube
> proyectando los puntos en la cámara RGB-D y la térmica (está en el backlog).

## 2. Autonomía en carriles (`lane_traverse`)

Cada tramo autónomo vale **15 puntos**. La estrategia es deliberadamente simple:

1. El operador pone el robot en la zona de inicio, mirando a lo largo del carril, y aprieta **GUIDE**
   (o `/autonomy/start`). Desde ahí, **manos afuera**.
2. **OUTBOUND**: se mantiene en el centro del pasillo con el LiDAR (paredes laterales) y el rumbo con el IMU.
   Velocidad 0.30 m/s, que baja a 0.15 m/s si hay pendiente (> 10°). Los flippers los maneja `auto_flipper`
   según el cabeceo.
3. Llega a la zona final cuando: recorrió `lane_length` (medido antes, se permite pre-mapear), **o** vio un QR
   (`end_qr_text`), **o** tiene una pared adelante (después del 60 % del recorrido).
4. **TURN**: gira 180° en el lugar con el IMU y vuelve (**INBOUND**). Cada tramo suma 1 a `traverses_done`.
5. **Atasco**: si no avanza 5 cm en 4 s, retrocede 1.5 s y reintenta. Después de 3 intentos, **ABORT** y le
   devuelve el control al operador.
6. **Si el operador toca el joystick, la autonomía se corta al instante** (y ese tramo cuenta como teleoperado).

Los LEDs se ponen **azules** en modo autónomo (sirve para que los jueces lo vean).

Parámetros: [`carpincho_autonomy/config/autonomy.yaml`](../../ros2_ws/src/carpincho_autonomy/config/autonomy.yaml).
**`lane_length` hay que medirlo en cada carril** (con el mapa del pre-mapeo o con cinta métrica).

### Flippers automáticos (`auto_flipper`)

| Estado | Condición | Flippers |
|---|---|---|
| PLANO | \|pitch\| < 8° | +20° (listos para encarar) |
| SUBIENDO | pitch > 8° | −10° (alargan la base de apoyo) |
| CORONANDO | la trompa cae rápido (> 15°/s) | −35° (amortiguan la caída) |
| BAJANDO | pitch < −8° | −25° |

Con histéresis para que no oscile. Se activa en modo autónomo o con `/flipper/auto` (Bool).

## 3. Destreza autónoma (TA ×10, AA ×20) — plan

1. **Inspect TA** (primero): el operador deja el robot frente al carril lineal y aprieta un botón. El brazo
   sale de `stow` a `inspect_high`, barre de izquierda a derecha con J1 mientras `qr_detector`/`hazmat`
   miran la cámara de la pinza, guarda la imagen anotada y vuelve a `stow`.
2. **Touch TA**: AprilTag o detección del agujero → pose 3D → IK con la herramienta perpendicular
   (pitch = π/2) → aproximación a 5 cm → avance lineal lento hasta tocar (corriente o carga del STS).
3. **AA**: igual, pero la aproximación la hace Nav2 a una pose relativa al tag o a la tarea.

La IK y el jog cartesiano ya están en `carpincho_arm/kinematics.py`; falta el "orquestador" de la tarea
(ver backlog: *Destreza TA*).

## 4. Laberinto autónomo (×5) — plan

- Nav2 con el `/map` de octomap (o slam_toolbox 2D sobre `/scan`) + exploración por fronteras
  (`m-explore-ros2` / `explore_lite`). Controlador Regulated Pure Pursuit, robot de 0.42 × 0.52 m.
- Retorno al inicio con la posición guardada en `/mission/start`.
- Mientras explora, `poi_manager` va confirmando objetos. Al volver, llamar `/mission/export` automáticamente.
- **No se puede pre-mapear el laberinto**: probar en laberintos de la arena casera que cambien de forma.
