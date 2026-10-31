# Calibraciones (hacerlas en este orden)

Anotá cada valor medido en el **registro de pruebas** (fecha, quién, valor viejo y valor nuevo) y subilo al YAML
correspondiente con un PR.

## 1. Sentido de motores y encoders (firmware)

1. Robot sobre un soporte, con las orugas en el aire. Armar y mandar `v = +0.1` con el joystick.
2. Las dos orugas tienen que ir **hacia adelante**. Si una va al revés: invertir `INVERT_LEFT/RIGHT` en `config.h`.
3. `ros2 topic echo /base/status` y `/odom`: con avance positivo, `twist.linear.x > 0`. Si una velocidad da
   negativa: invertir `invert_*_encoder` en `base.yaml` (y en el firmware, para el lazo de velocidad).

## 2. counts_per_m

1. Marcar 5.00 m en el piso. Avanzar en línea recta, teleoperado, despacio.
2. `counts_per_m_nuevo = counts_per_m × (distancia_odom / 5.00)`.
3. Repetir 3 veces y promediar. Con tacos de TPU, el valor efectivo puede diferir un 5-10 % del teórico.

## 3. slip_factor (giro)

1. Girar en el lugar 10 vueltas (contar con el IMU: `ros2 topic echo /imu/data`).
2. `slip_factor_nuevo = slip_factor × (vueltas_odometría_sin_IMU / vueltas_reales)`. Para medirlo, poner
   `use_imu_yaw: false` temporalmente.
3. En alfombra vs madera cambia mucho. Para la competencia, se usa el yaw del IMU (`use_imu_yaw: true`).

## 4. Feed-forward y PI de velocidad

1. Mandar PWM 100 % con las orugas en el aire (`CMD_CONFIG` con kp = ki = 0 y kff = 1/v) y medir la velocidad máxima.
   `kff = 1 / v_max`.
2. En el piso: escalón de 0 a 0.3 m/s. Subir `kp` hasta que haya sobrepico chico; `ki` para que el error se
   anule en < 0.5 s. Valores iniciales: kp 0.8, ki 4.
3. Se cambia en caliente en `base.yaml` → reiniciar `base_bridge` (manda `CMD_CONFIG` al conectar).

## 5. Cero y rango del flipper

1. Poner el flipper **horizontal hacia adelante** (nivel de burbuja sobre el brazo FL-01).
2. `ros2 service call /base/zero_flipper std_srvs/srv/Trigger` → el firmware guarda el offset (en RAM: se
   pierde al reiniciar. Pendiente: guardarlo en NVS; mientras tanto, se hace al encender).
3. Con `+0.5 rad`, la punta tiene que **subir**. Si baja: `INVERT_FLIP_MOTOR`; si el ángulo crece al revés:
   `INVERT_FLIP_SENSOR`.
4. Verificar los límites (−100°/+190°) moviendo despacio con RB + stick derecho.

## 6. Brazo: IDs y ceros

```bash
python3 tools/arm_tool.py scan                 # cada servo nuevo viene con ID 1
python3 tools/arm_tool.py setid 1 4            # de a uno: 1 base, 2-3 hombro, 4 codo, 5 muñeca, 6 giro, 7 pinza
python3 tools/arm_tool.py zeros                # torque OFF → brazo VERTICAL (pose cero) → Enter
```

Copiar los `zeros` a `carpincho_arm/config/arm.yaml`. Después, probar cada articulación de a poco con
`/arm/joint_command`: con un valor positivo, J2/J3/J4 tienen que inclinar **hacia adelante**. Si van al revés,
cambiar el signo (`signs`). En el hombro, los dos servos tienen signos opuestos: **verificar que no peleen**
(si se calientan sin carga, uno de los signos o zeros está mal).

> ⚠ Con la reducción 2:1, J2 y J3 cubren 180° de articulación con los 360° del servo. El "zero" tiene que quedar
> de forma que todo el rango (`min`..`max`) caiga dentro de 0..4095 ticks. `arm.yaml` trae valores calculados
> para eso: si medís otros, revisá que `zero + ratio × ángulo × 651.9` no se salga.

## 7. Cámaras

- Intrínsecos de las cámaras USB: `ros2 run camera_calibration cameracalibrator` con un tablero de 8×6.
  La RGB-D ya viene calibrada de fábrica.
- Extrínsecos (posición en el robot): vienen del CAD (URDF). Verificar con un AprilTag a 1 m: la posición en
  `map` tiene que coincidir con la cinta métrica a ±3 cm.

## 8. IMU

- BNO055 en modo IMUPLUS: dejar el robot **quieto 5 s** al encender (calibra el giróscopo). El estado de
  calibración viaja en `MSG_IMU.calib`.
- Si el montaje real no está alineado con el robot, corregir el `rpy` de `imu_joint` en el URDF.
