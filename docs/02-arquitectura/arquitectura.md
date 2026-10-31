# Arquitectura del sistema

## 1. Vista general

```mermaid
flowchart LR
    subgraph OP["Estación de operador (notebook)"]
        JOY[Joystick] --> TELEOP[joy_teleop]
        FOX[Foxglove Studio<br/>cámaras · mapa · estado]
        AUD1[Audio PTT]
    end
    subgraph RADIO["Wi-Fi 5 GHz dedicado"]
        R1((router<br/>operador)) <--> R2((router<br/>robot))
    end
    subgraph JET["Jetson Orin Nano · ROS 2 Jazzy"]
        BB[base_bridge]
        ARM[arm_driver]
        LIO[FAST-LIO + odom_relay]
        OCT[octomap → /map]
        PER[QR · hazmat · movimiento · térmica · AprilTag]
        POI[poi_manager]
        EXP[mission_exporter]
        AUT[lane_traverse + mux<br/>auto_flipper]
        FB[foxglove_bridge]
    end
    subgraph MCU["ESP32-S3 · placa base"]
        FW[PI orugas 200 Hz<br/>flipper · IMU · batería<br/>watchdog · E-stop]
    end
    TELEOP -- DDS --> R1
    FOX -- WebSocket --> R1
    R2 --- JET
    BB <-- "USB CDC · COBS+CRC" --> FW
    ARM <-- "USB · bus TTL 1 Mbps" --> SERVOS[7× STS3215]
    FW --> DRV1[MDD20A] --> MT[2× motor 775 1:51]
    FW --> DRV2[MDD10A] --> MF[motor flipper 1:264]
    FW --- SENS[BNO055 · INA226 · AS5600 · Hall]
    LIDAR[Livox Mid-360] -- Ethernet --> LIO
    CAMS[RGB-D · térmica · 3× USB] -- USB --> PER
```

**Reparto de tareas**: el **ESP32** hace todo lo que necesita tiempo real y que tiene que seguir siendo
seguro aunque Linux se cuelgue (lazos de motor, watchdog, E-stop). El **Jetson** hace la percepción, el
mapeo, la autonomía y la comunicación. La **notebook** solo muestra y manda comandos del joystick: el robot
tiene que poder terminar una tarea autónoma aunque el enlace se caiga.

## 2. Módulos e interfaces (ICD)

| Módulo | Hardware | Entradas | Salidas | Interfaz |
|---|---|---|---|---|
| M1 Tracción | 2× 775 + MDD20A | velocidad por oruga [m/s] | encoders | PWM 20 kHz + DIR |
| M2 Flipper | 775 + planetaria 56 mm 1:264 + MDD10A + AS5600 | ángulo o velocidad | ángulo [rad] | PWM + DIR, ADC |
| M3 Placa base | ESP32-S3 | `CMD_*` | `MSG_STATE/IMU/AUX` | USB CDC, [protocolo](../05-software/firmware.md) |
| M4 Potencia | 6S + fusibles + contactor | E-stop | 24 V actuadores / 24 V lógica / 12 V / 5 V | XT60, ATO |
| M5 Cómputo | Jetson Orin Nano | sensores | ROS 2 | USB 3, Ethernet |
| M6 LiDAR 3D | Livox Mid-360 | — | `/livox/lidar`, `/livox/imu` | Ethernet 100 Mbps (IP fija) |
| M7 Visión | Orbbec/RealSense, térmica, 3× USB | — | imágenes | USB |
| M8 Brazo | 7× STS3215 + adaptador | objetivos articulares | posiciones | TTL half-duplex 1 Mbps |
| M9 Comunicaciones | 2 routers 5 GHz | — | — | Ethernet / Wi-Fi |
| M10 Audio | placa USB + micrófono + parlante | voz del operador | audio ambiente | GStreamer/Opus por UDP |

## 3. Grafo ROS 2 (tópicos principales)

```mermaid
flowchart TB
    joy[/joy/] --> joy_teleop
    joy_teleop -- /cmd_vel_teleop --> lane_traverse
    joy_teleop -- /autonomy/request --> lane_traverse
    lane_traverse -- /cmd_vel --> base_bridge
    lane_traverse -- /autonomy/active --> auto_flipper & poi_manager
    auto_flipper -- /flipper/position_cmd --> base_bridge
    joy_teleop -- /flipper/* --> base_bridge
    joy_teleop -- /arm/cartesian_jog · /arm/gripper --> arm_driver
    base_bridge -- /odom · /imu/data · /joint_states · /battery · /base/status --> X1((consumidores))
    arm_driver -- /arm/joint_states --> jsp[joint_state_publisher] --> rsp[robot_state_publisher]
    livox[/livox/lidar/] --> fast_lio --> odom_relay
    fast_lio -- /cloud_registered --> octomap -- /map --> mission_exporter
    fast_lio -- /Laser_map --> mission_exporter
    fast_lio -- /cloud_registered_body --> p2l[pointcloud_to_laserscan] -- /scan --> lane_traverse
    cams[/cámaras/] --> qr & hazmat & motion & thermal & apriltag
    qr & hazmat & thermal -- /perception/detections --> poi_manager -- /poi/list --> mission_exporter
    qr -- /qr/text --> lane_traverse
```

### Tópicos y servicios

| Nombre | Tipo | Publica → consume | Notas |
|---|---|---|---|
| `/cmd_vel_teleop` | Twist | joy_teleop → lane_traverse (mux) | Si el operador lo mueve, se cancela la autonomía |
| `/cmd_vel` | Twist | lane_traverse (mux) → base_bridge | Único comando que llega a las orugas |
| `/flipper/position_cmd` | Float64 [rad] | teleop, auto_flipper → base_bridge | 0 = horizontal, + = punta arriba |
| `/flipper/velocity_cmd` | Float64 [rad/s] | teleop → base_bridge | |
| `/odom` | Odometry | base_bridge | Orugas + yaw del IMU |
| `/Odometry` | Odometry | fast_lio | Base de la TF `odom→base_footprint` (odom_relay) |
| `/imu/data` | Imu | base_bridge | BNO055 en modo IMUPLUS (sin magnetómetro) |
| `/base/status` | BaseStatus | base_bridge | Batería, fallas, E-stop, enlace |
| `/arm/joint_states` | JointState | arm_driver | |
| `/arm/cartesian_jog` | Twist | teleop → arm_driver | lineal xyz, `angular.y` = cabeceo, `.z` = base, `.x` = giro |
| `/arm/set_named_pose` | SetNamedPose (srv) | → arm_driver | `stow`, `ready`, `inspect_front`... |
| `/perception/detections` | DetectionArray | detectores → poi_manager | |
| `/poi/list` | PoiArray | poi_manager → exporter | Confirmados (≥ 3 vistas) |
| `/qr/text` | String | qr_detector → operador / autonomía | |
| `/mission/start`, `/mission/export` | Trigger (srv) | → mission_exporter | Escribe TIFF, PLY y CSV |
| `/autonomy/start`, `/autonomy/stop` | Trigger (srv) | → lane_traverse | También con el botón GUIDE |
| `/base/enable` | SetBool (srv) | teleop (START) → base_bridge | Armar o desarmar |

## 4. Árbol de TF

```mermaid
flowchart TB
    map --> odom --> base_footprint --> base_link
    odom --> camera_init
    livox_frame --> body
    base_link --> track_left_link & track_right_link & flipper_link
    flipper_link --> flipper_left_link & flipper_right_link
    base_link --> imu_link & livox_frame
    base_link --> depth_cam_link --> depth_cam_optical_frame
    base_link --> thermal_link --> thermal_optical_frame
    base_link --> cam_front_link & cam_rear_link
    base_link --> arm_base_link --> arm_link1 --> arm_link2 --> arm_link3 --> arm_link4 --> arm_link5
    arm_link5 --> tool_tip & gripper_finger_link & gripper_cam_link
```

- `map→odom`: identidad, publicada por `odom_relay` (FAST-LIO ya da una odometría global sin deriva apreciable
  en recorridos de 20 min). Sin LiDAR, `base_bridge` publica `odom→base_footprint` con orugas + IMU.
- `odom→base_footprint`: **una sola fuente** (o `odom_relay` o `base_bridge`), nunca las dos. El bringup lo
  maneja con el argumento `lio:=true|false`.
- `camera_init` (origen de las nubes de FAST-LIO) y `body` (IMU del Mid-360) los publica `odom_relay` como TF
  estáticas, para que `/cloud_registered`, `/Laser_map` y `/cloud_registered_body` se puedan usar en `map`.
- Con FAST-LIO, el driver Livox publica `CustomMsg` (no `PointCloud2`): para ver el LiDAR en RViz/Foxglove usar
  `/cloud_registered` o `/cloud_registered_body`.
- `base_footprint` está en el piso, en el centro entre los ejes. El PLY del reglamento usa como origen el
  **frente** del robot: el exportador lo corrige con `front_offset`.

## 5. Estados del robot y seguridad

```mermaid
stateDiagram-v2
    [*] --> Desarmado
    Desarmado --> Armado: START (teleop) / base/enable
    Armado --> Desarmado: START / E-stop / batería crítica
    Armado --> Autonomo: GUIDE / autonomy/start
    Autonomo --> Armado: el operador mueve el joystick / fin / atasco
    Armado --> Frenado: sin comandos > 300 ms (watchdog del ESP32)
    Frenado --> Armado: vuelven los comandos
    Desarmado --> [*]
```

Capas de seguridad, de la más dura a la más blanda:

1. **E-stop físico**: abre el contactor y deja sin energía a drivers y servos (la Jetson sigue prendida).
2. **Firmware**: si el bus de motores no tiene tensión, desarma y exige volver a armar. Watchdog de 300 ms,
   batería crítica, sobrecorriente, atasco del flipper y límites del flipper.
3. **base_bridge**: deja de mandar `cmd_vel` si pasan 0.5 s sin comandos; se desarma al detectar el E-stop.
4. **joy_teleop**: hombre muerto (LB); si el joystick se desconecta, publica cero.
5. **lane_traverse**: cualquier movimiento del operador cancela la autonomía; si detecta un atasco, se recupera
   3 veces y después aborta.

LEDs de estado (tira WS2812): verde = armado · verde tenue = desarmado · **azul = autónomo** ·
naranja titilando = sin comandos · naranja fijo = batería baja · rojo = falla · rojo titilando = E-stop.
