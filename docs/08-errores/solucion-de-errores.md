# Solución de errores

Buscá el **síntoma** (Ctrl+F). Cada fila dice qué mirar primero, la causa probable y el arreglo.
Si resolvés algo que no estaba, **agregalo a esta tabla** con un PR.

## Diagnóstico rápido en 60 segundos

```bash
ros2 topic echo /base/status --once          # link_ok, battery_voltage, fault_names, estop_active
ros2 topic hz /odom /imu/data /livox/lidar   # ¿llegan los datos? (50 / 100 / 10 Hz)
ros2 node list                               # ¿están todos los nodos?
journalctl -u carpincho -n 100 --no-pager    # log del arranque automático
ls -l /dev/carpincho_* /dev/video_*          # ¿están los dispositivos?
```

Y mirá los **LEDs** del robot: verde = armado · verde tenue = desarmado · azul = autónomo ·
naranja titilando = sin comandos · naranja fijo = batería baja · rojo = falla · rojo titilando = E-stop.

## Movilidad y mecánica

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| Una oruga gira al revés | Motor o encoder invertido | `INVERT_LEFT/RIGHT` en `config.h` **y** `invert_*_encoder` en `base.yaml` (los dos coherentes) |
| La oruga gira pero el robot se desvía | Tacos faltantes, correa floja o PI mal ajustado | Revisar los tacos; `ros2 topic echo /base/status`; reajustar kp/ki ([calibración](../05-software/calibracion.md)) |
| La oruga "salta" dientes en la escalera | Correa interna (motor→eje) floja | Tensar en la ranura de DT-08 (flexión ≈ 4 mm) |
| La oruga se sale de la polea | Poleas desalineadas o pestaña rota | Alinear con una regla; reimprimir la polea con pestaña más alta |
| Se despegan los tacos | Adhesivo o remaches insuficientes | Lijar + PU + remache con arandela; probar la correa con tacos soldados de fábrica |
| El flipper no levanta el robot | Correa del flipper patina (fusible) o falta torque | Tensar la 300-5M del flipper; si salta con la correa tensa: correa de 25 mm de ancho (poleas más anchas) o reductora 1:369 |
| El flipper "tiembla" en una posición | `flip_kp` alto o banda muerta chica | Bajar `flip_kp` (3 → 2) o subir la banda muerta (0.02 → 0.04 rad) |
| `FLIP_STALL` | Pidió fuerza 1.5 s sin moverse (trabado) | Destrabar; cambiar de modo para limpiar el atasco; revisar si hay algo en los engranajes |
| `FLIP_SENSOR` / ángulo loco | Imán despegado, AS5600 lejos o cable cortado | Distancia imán-chip de 1-2 mm; medir OUT (0-3.3 V al girar) |
| El robot se vuelca hacia atrás en la escalera | CG atrás o flippers mal usados | Subir con los flippers apoyados adelante (−10°); bajar marcha atrás con los flippers de "patas" |
| Ruido de chirrido | Rodamiento seco o rozamiento de la correa con la placa | Revisar separación placa-polea (3 mm); cambiar rodamiento |
| Los motores calientan > 70 °C | Uso continuo en escalera o PWM mal ajustado | Pausas; verificar que `max_accel` no sea excesivo; ventilación del cuerpo |

## Electrónica y potencia

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| No enciende nada | Fusible principal, interruptor o BMS en protección | Medir la batería; cambiar el fusible de 40 A; algunos BMS se "despiertan" conectando el cargador |
| La Jetson se reinicia al acelerar | Caída de tensión: el buck del cómputo comparte la masa con los motores mal | Estrella de masas; buck de cómputo en el bus de **lógica**; capacitor de 1000 µF en la entrada del buck |
| E-stop apretado pero los motores siguen | Contactor pegado o cableado al revés (NO en vez de NC) | **Parar todo**. Revisar W22; cambiar el contactor. No competir así |
| Al soltar el E-stop el robot no anda | Comportamiento correcto: hay que volver a armar | Apretar **START** |
| `BATT_LOW` con la batería cargada | INA226 mal calibrado o caída en los cables | Comparar con el multímetro; revisar el shunt; cables de 12 AWG |
| `OVERCURRENT` en la escalera | Pico > 38 A | Subir más despacio; revisar si una oruga está trabada; considerar el límite del BMS |
| Chispa al cerrar el contactor | Carga de los capacitores de los drivers | Resistencia de precarga de 47 Ω 5 W en paralelo con el contactor |
| Errores de CRC que suben | Ruido en el USB del ESP32 | Cable USB corto con ferrite; separar de los cables de motor; masa común bien hecha |

## Firmware / ESP32

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| `pio run -t upload` no encuentra la placa | Usaste el puerto "UART" o la placa no entra en modo boot | Puerto **"USB"**; BOOT + RESET; `ls /dev/ttyACM*` |
| `/dev/carpincho_base` no existe | Regla udev sin instalar o VID/PID distinto | `udevadm info -a -n /dev/ttyACM0 \| grep idVendor` y ajustar la regla |
| `link_ok: false` pero el puerto abre | Firmware viejo (otro protocolo) o la placa se reinicia en bucle | `MSG_INFO` en el log de `base_bridge`; monitor serie; reflashear |
| `CMD_TIMEOUT` permanente | No llegan comandos: `base_bridge` caído o el puerto está tomado por otro proceso | `ros2 node list`; `sudo lsof /dev/carpincho_base` |
| `IMU` en las fallas | BNO055 no responde por I2C | Revisar SDA=12/SCL=13, pull-ups, dirección 0x28 (ADR a GND) |
| El robot "cabecea" al arrancar | Rampa muy agresiva | Bajar `max_accel` (1.0 → 0.6) |

## ROS 2, red y operador

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| La notebook no ve los tópicos del robot | `ROS_DOMAIN_ID` o RMW distintos, o los peers de Cyclone mal | Mismas variables en las dos máquinas; IPs en `cyclonedds.xml`; `ros2 multicast` no sirve (lo desactivamos) |
| El joystick no hace nada | Falta el hombre muerto (LB) o el robot está desarmado | Mantener **LB**; START para armar; `ros2 topic echo /joy` |
| Los índices del joystick no coinciden | Otro modelo de joystick | `ros2 topic echo /joy` y corregir `axes`/`buttons` en `teleop.yaml` |
| El video se congela | Radio saturada | Usar `/compressed`, bajar la resolución y los FPS, cerrar los paneles que no se miran |
| `/odom` y la TF "saltan" | Dos nodos publican `odom→base_footprint` | `lio:=true` → `base_bridge` con `publish_tf: false` (el launch lo hace solo) |
| RViz: "No transform from X to map" | FAST-LIO no arrancó o falta `odom_relay` | `ros2 topic hz /Odometry`; ver el log de FAST-LIO (IP del Livox) |
| FAST-LIO diverge (el mapa "explota") | Movimientos bruscos al arrancar, IMU sin `time_sync` o `blind` chico | Arrancar quieto 3 s; `blind: 0.30`; revisar que `lidar_type` coincida con `xfer_format` del driver |
| El Livox no publica | IP de la Jetson no está en la subred del Livox | Alias 192.168.1.50/24 y `MID360_config.json` con esa IP de host |
| `Package 'carpincho_xxx' not found` | No hiciste `source install/setup.bash`, o el package.xml tiene XML inválido | `source`; `colcon list` tiene que mostrar `(ros.ament_python)` y no `(python)` |
| El brazo no responde | Sin 12 V en los servos, IDs mal o baudrate | `tools/arm_tool.py scan`; E-stop liberado (los servos están en el bus de actuadores) |
| Dos servos del hombro calientan quietos | Signos o ceros mal: se pelean | Recalibrar los `zeros` con el brazo vertical; verificar `signs: [1, -1]` |
| El brazo no llega a una pose ("no se mueve") | Fuera de alcance o de límites en la IK | Probar con una pose con el codo más flexionado; ver `limits` en `arm.yaml` |

## Percepción

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| No detecta hazmat con la luz de la sede | Dataset sin esa iluminación | Fotos en la sede → *fine-tune* de 20 épocas; bajar `conf` a 0.4 |
| Hazmat a < 5 FPS | Corre en PyTorch y no en TensorRT, o el Jetson está en modo de bajo consumo | Exportar `.engine`; `nvpmodel -m 0` |
| QR chicos no se leen | Poca resolución o desenfoque | Cámara de la pinza a 15-25 cm, `upscale: 1.5`, buena luz (focos) |
| Térmica en gris o sin temperatura | La cámara no entrega Y16 | Ver [percepcion.md](../05-software/percepcion.md#térmica-thermal_viewer); el modo depende del modelo |
| POIs ubicados lejos de su lugar real | TF de la cámara mal (URDF) o profundidad no alineada | Verificar con un AprilTag a 1 m; `depth_registration: true` |
| POIs duplicados | Cambia el nombre de la clase entre cuadros | Subir `min_hits`; unificar los nombres del modelo |
| Movimiento detecta todo | El robot o la cámara se están moviendo | Robot quieto; `/motion/reset`; subir `threshold` |

## Autonomía

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| Zigzaguea en el carril | `k_lat`/`k_head` altos o paredes que no se ven | Bajar las ganancias; revisar `/scan` (alturas `min/max_height` en `scan.yaml`) |
| Termina antes o después | `lane_length` mal medido u odometría que patina | Medir el carril; usar `/Odometry` de FAST-LIO (no `/odom`) |
| Aborta por atasco en un obstáculo que se pasa | `stuck_time` corto | Subir a 6 s en carriles difíciles; mejorar los flippers automáticos |
| No arranca con GUIDE | `lane_traverse` no corre o el robot no está armado | `ros2 node list`; START primero |
| Se corta solo | El joystick manda ruido > zona muerta | Subir la `deadzone`; calibrar el joystick |
