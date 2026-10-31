# Software ROS 2

Workspace: [`ros2_ws/src/`](../../ros2_ws/src/). Probado con **ROS 2 Humble** (Jetson) y **Jazzy** (CI).

| Paquete | Tipo | Qué hace |
|---|---|---|
| `carpincho_interfaces` | msgs | `BaseStatus`, `Detection(Array)`, `Poi(Array)`, `LaneStatus`, `SetNamedPose` |
| `carpincho_description` | URDF | xacro del robot; dimensiones generadas desde el CAD; launch de visualización |
| `carpincho_base` | Python | `base_bridge` (serie con el ESP32, odometría, IMU, batería) y `odom_relay` (FAST-LIO → TF) |
| `carpincho_arm` | Python | `arm_driver` (STS3215, IK, poses con nombre, jog cartesiano), `feetech.py`, `kinematics.py` |
| `carpincho_teleop` | Python | `joy_teleop`: joystick → robot, con hombre muerto y modos manejo y brazo |
| `carpincho_perception` | Python | QR, hazmat (YOLO), movimiento, térmica, `poi_manager`, `mission_exporter` |
| `carpincho_autonomy` | Python | `lane_traverse` (carril autónomo + mux de comandos), `auto_flipper` |
| `carpincho_bringup` | launch | `robot`, `sensors`, `mapping`, `perception`, `operator` + config, udev, systemd, DDS |

## Compilar y probar

```bash
cd ros2_ws
colcon build --symlink-install
colcon test && colcon test-result --verbose      # protocolo, cinemática, IK, export RRL, teleop, carril, URDF
```

Los algoritmos están separados de ROS (`protocol.py`, `kinematics.py`, `mapping.py`, `lane_logic.py`,
`rrl_export.py`, `vision.py`, `poi_store.py`): se testean con `pytest` sin robot y sin ROS.

## Lanzar

```bash
# robot completo (lo hace el servicio systemd al encender)
ros2 launch carpincho_bringup robot.launch.py
# variantes
ros2 launch carpincho_bringup robot.launch.py lio:=false            # sin LiDAR: odometría de orugas + IMU
ros2 launch carpincho_bringup robot.launch.py arm:=false sensors:=false perception:=false   # banco de motores
ros2 launch carpincho_bringup robot.launch.py mission:=Semi2        # nombre de misión para los archivos
# notebook del operador
ros2 launch carpincho_bringup operator.launch.py
```

## Comandos útiles en la pista

```bash
ros2 service call /base/enable std_srvs/srv/SetBool "{data: true}"           # armar (o START)
ros2 service call /base/zero_flipper std_srvs/srv/Trigger                    # flipper horizontal = 0
ros2 service call /arm/set_named_pose carpincho_interfaces/srv/SetNamedPose "{name: stow}"
ros2 service call /mission/start std_srvs/srv/Trigger                        # al empezar el laberinto
ros2 service call /mission/export std_srvs/srv/Trigger                       # al terminar: TIFF + PLY + CSV
ros2 service call /autonomy/start std_srvs/srv/Trigger                       # carril autónomo
ros2 topic echo /base/status                                                  # batería, fallas, enlace
ros2 topic echo /autonomy/lane_status
```

## Convenciones

- Unidades SI y REP-103 (X adelante, Y izquierda, Z arriba). Ángulos en radianes en los tópicos y en grados
  solo en los YAML "para humanos" (las poses del brazo).
- Parámetros en `config/*.yaml` de cada paquete. Nada de números mágicos en el código.
- Cada nodo frena o se desarma solo si deja de recibir lo que necesita (watchdogs).
- Los nodos de percepción publican siempre una `DetectionArray`, aunque esté vacía, y la imagen anotada
  **solo si alguien la mira** (ahorra CPU y radio).
- Para agregar un detector nuevo: publicar `DetectionArray` en `/perception/detections` con un `type` del
  reglamento (`ar_code`, `hazmat_sign`, `real_object`, `heat_sig`). `poi_manager` lo ubica y deduplica solo.
