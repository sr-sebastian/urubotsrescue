// Configuración de hardware de la placa base (ESP32-S3-DevKitC-1 N8R8).
// Pines elegidos evitando: strapping (0, 3, 45, 46), USB nativo (19, 20), PSRAM octal (35-37)
// y el LED RGB de la placa (38 en v1.1 / 48 en v1.0).
#pragma once
#include <stdint.h>

#define FW_VERSION "carpincho-base 0.1.0"

// ---- Tracción: Cytron MDD20A (modo PWM + DIR, jumper en "PWM") ------------
constexpr int PIN_DRV_L_PWM = 4;
constexpr int PIN_DRV_L_DIR = 5;
constexpr int PIN_DRV_R_PWM = 6;
constexpr int PIN_DRV_R_DIR = 7;
// ---- Flipper: Cytron MDD10A canal 1 (canal 2 libre) ------------------------
constexpr int PIN_FLIP_PWM = 15;
constexpr int PIN_FLIP_DIR = 16;
constexpr int PIN_AUX2_PWM = 17;   // canal 2 libre (p. ej. cabrestante de cable / reserva)
constexpr int PIN_AUX2_DIR = 18;
// ---- Encoders de cuadratura de los motores de tracción (vía divisor/level shifter si son 5 V)
constexpr int PIN_ENC_L_A = 8;
constexpr int PIN_ENC_L_B = 9;
constexpr int PIN_ENC_R_A = 10;
constexpr int PIN_ENC_R_B = 11;
// ---- Analógicas (ADC1) ----------------------------------------------------
constexpr int PIN_FLIP_ANGLE = 1;  // AS5600 salida OUT (analógica 0..VDD)
constexpr int PIN_HALL = 2;        // SS49E / DRV5053 en la punta del brazo
// ---- I2C: BNO055 (0x28) + INA226 (0x40) ------------------------------------
constexpr int PIN_SDA = 12;
constexpr int PIN_SCL = 13;
// ---- Varios -------------------------------------------------------------------
constexpr int PIN_ESTOP_SENSE = 14;   // alto = bus de motores energizado (divisor 100k/15k desde 24 V)
constexpr int PIN_LEDS = 21;          // tira WS2812 de estado (8 LEDs)
constexpr int PIN_LIGHTS = 39;        // MOSFET de los focos LED blancos (PWM)
constexpr int PIN_BUZZER = 40;

// ---- Mecánica (debe coincidir con cad/carpincho_cad/params.py) ------------
constexpr float TRACK_PD_M = 0.09549f;                 // polea 60T HTD5M
constexpr float TRACK_EFF_RADIUS_M = TRACK_PD_M / 2;   // radio en la línea primitiva de la correa
constexpr float DRIVE_BELT_RATIO = 30.0f / 20.0f;      // motor -> eje trasero
constexpr float ENCODER_CPR_MOTOR = 7 * 4;             // pulsos/vuelta del motor x4 (ajustar a tu encoder)
constexpr float GEARBOX_RATIO = 51.0f;                 // reductora planetaria (params.DRIVE_GEARBOX)
constexpr float COUNTS_PER_M =
    ENCODER_CPR_MOTOR * GEARBOX_RATIO * DRIVE_BELT_RATIO / (2.0f * 3.14159265f * TRACK_EFF_RADIUS_M);
constexpr bool INVERT_LEFT = false;
constexpr bool INVERT_RIGHT = true;     // el motor derecho está espejado
constexpr bool INVERT_FLIP_MOTOR = false;
constexpr bool INVERT_FLIP_SENSOR = false;

// ---- Límites y tiempos -------------------------------------------------------
constexpr float MAX_TRACK_SPEED = 0.40f;    // m/s (sin carga a 24 V ≈ 0.39-0.45: 775@6000rpm /51 /1.5)
constexpr float DEFAULT_MAX_ACCEL = 1.0f;   // m/s^2
constexpr uint32_t CMD_TIMEOUT_MS = 300;    // sin comandos -> frenar
constexpr uint16_t BATT_LOW_MV = 21600;     // 6S Li-ion: 3.6 V/celda
constexpr uint16_t BATT_CRIT_MV = 19800;    // 3.3 V/celda -> deshabilitar motores
constexpr float OVERCURRENT_A = 38.0f;      // fusible principal 40 A
constexpr uint32_t PWM_FREQ_HZ = 20000;     // inaudible, dentro del rango del MDD20A
constexpr int PWM_BITS = 10;

// ---- Tasas ------------------------------------------------------------------
constexpr uint32_t CONTROL_PERIOD_US = 5000;   // 200 Hz lazo de velocidad
constexpr uint32_t STATE_PERIOD_MS = 20;       // 50 Hz telemetría
constexpr uint32_t IMU_PERIOD_MS = 10;         // 100 Hz
constexpr uint32_t AUX_PERIOD_MS = 100;        // 10 Hz
