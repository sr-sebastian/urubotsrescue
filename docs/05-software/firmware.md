# Firmware de la placa base (ESP32-S3)

Código: [`firmware/carpincho_base/`](../../firmware/carpincho_base/). PlatformIO + Arduino (core 2.0.x).

## Compilar, flashear y probar

```bash
pip install platformio
cd firmware/carpincho_base
pio run                      # compila (≈2 min la primera vez)
pio run -t upload            # conectar al puerto "USB" del DevKit (no al "UART")
# tests de PC (sin placa): protocolo, PI, flipper, desenrollado de ángulo
g++ -std=c++17 -Wall -I include test_host/test_protocol.cpp -o /tmp/tp && /tmp/tp
```

Si la placa no aparece después de flashear: mantener **BOOT**, tocar **RESET**, soltar BOOT y volver a subir.

## Qué hace

| Lazo | Frecuencia | Detalle |
|---|---:|---|
| Control de orugas | 200 Hz | Encoders por PCNT → velocidad [m/s] → rampa (1 m/s²) → PI + feed-forward → PWM 20 kHz |
| Flipper | 200 Hz | AS5600 (ADC) → ángulo desenrollado → P con límite de velocidad, límites blandos y detección de atasco |
| Telemetría | 50 Hz | `MSG_STATE`: encoders, velocidades, flipper, batería, fallas |
| IMU | 100 Hz | `MSG_IMU`: cuaternión, giróscopo y acelerómetro del BNO055 (modo IMUPLUS) |
| Auxiliar | 10 Hz | `MSG_AUX`: Hall, temperatura y peor tiempo de lazo; actualiza los LEDs |

**Seguridad**: si pasan más de 300 ms sin comandos, frena. Si se aprieta el E-stop (bus sin tensión), frena **y
se desarma**. Con batería crítica (< 19.8 V) se bloquea hasta reiniciar. Con sobrecorriente (> 38 A) frena.

## Protocolo serie

Trama: `COBS( id | seq | payload | crc16 ) 0x00`, con CRC-16/CCITT-FALSE sobre `id+seq+payload`, en
little-endian. La implementación espejo en Python (`carpincho_base/protocol.py`) se prueba contra el
**mismo vector de referencia** que el test del firmware: si alguien cambia un lado y no el otro, la CI falla.

| ID | Nombre | Sentido | Payload |
|---|---|---|---|
| 0x01 | CMD_DRIVE | → MCU | `float v_left, v_right` [m/s] |
| 0x02 | CMD_FLIPPER | → MCU | `u8 mode` (0 libre, 1 posición, 2 velocidad), `float valor` |
| 0x03 | CMD_AUX | → MCU | `u8 luces, u8 modo_led, u8 flags` (bit0 armar, bit1 buzzer) |
| 0x04 | CMD_CONFIG | → MCU | `float kp, ki, kff, max_accel, flip_kp, flip_max_vel` |
| 0x05 | CMD_HEARTBEAT | → MCU | `u32 ms` |
| 0x06 | CMD_ZERO_FLIPPER | → MCU | — (el ángulo actual pasa a ser 0) |
| 0x07 | CMD_GET_INFO | → MCU | — |
| 0x81 | MSG_STATE | ← MCU | `u32 t, i32 encL, i32 encR, f vL, f vR, f flip, f flipVel, u16 mV, i16 cA, u8 fallas, u8 flags` (34 B) |
| 0x82 | MSG_IMU | ← MCU | `f qw,qx,qy,qz, gx,gy,gz, ax,ay,az, u8 calib` (41 B) |
| 0x83 | MSG_AUX | ← MCU | `f hall_mT, u16 hall_raw, i16 temp×10, u16 loop_us_max` (10 B) |
| 0x84 | MSG_LOG | ← MCU | texto |
| 0x85 | MSG_INFO | ← MCU | `u8 versión` + texto |

Bits de falla: `0x01` sin comandos · `0x02` batería baja · `0x04` batería crítica · `0x08` sensor de flipper ·
`0x10` atasco de flipper · `0x20` IMU · `0x40` sobrecorriente · `0x80` E-stop.

## Constantes a ajustar (`include/config.h`)

| Constante | Valor inicial | Cómo se ajusta |
|---|---|---|
| `ENCODER_CPR_MOTOR` | 7 × 4 | Pulsos por vuelta del motor (antes de la reductora) × 4. Ver la hoja de datos del encoder |
| `GEARBOX_RATIO` | 51 | La reductora real |
| `INVERT_*` | — | Para que "adelante" sea adelante en los dos lados y el flipper suba con valores positivos |
| `MAX_TRACK_SPEED` | 0.40 m/s | Velocidad medida a PWM 100 % sin carga, menos un 5 % |
| `kff` (en `control.h` o por `CMD_CONFIG`) | 1/0.42 | 1 / velocidad a PWM 100 % |

Después de cambiar algo: `pio run -t upload` y el procedimiento de [calibracion.md](calibracion.md).
