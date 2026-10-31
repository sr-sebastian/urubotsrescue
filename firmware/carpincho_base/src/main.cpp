// Firmware de la placa base del Carpincho (ESP32-S3).
//
// Responsabilidades (todo lo que necesita tiempo real o hardware de bajo nivel):
//   - Lazo de velocidad de las orugas a 200 Hz (PI + feed-forward + rampa).
//   - Control de posición/velocidad del flipper con AS5600 y detección de atasco.
//   - IMU BNO055, monitor de batería INA226, sensor Hall de la punta del brazo.
//   - Watchdog de comandos: sin mensajes del Jetson por 300 ms -> frena todo.
//   - Lectura del estado del E-stop (bus de motores sin energía -> F_ESTOP).
//   - LEDs de estado, focos y buzzer.
// La lógica "inteligente" (odometría, TF, teleop, autonomía) vive en ROS 2, en el Jetson.
#include <Adafruit_BNO055.h>
#include <Adafruit_NeoPixel.h>
#include <Arduino.h>
#include <ESP32Encoder.h>
#include <INA226.h>
#include <Wire.h>

#include "config.h"
#include "control.h"
#include "protocol.h"

// ---------------------------------------------------------------- periféricos
static ESP32Encoder encL, encR;
static Adafruit_BNO055 bno(55, 0x28, &Wire);
static INA226 ina(0x40, &Wire);
static Adafruit_NeoPixel leds(8, PIN_LEDS, NEO_GRB + NEO_KHZ800);
static bool imu_ok = false, ina_ok = false;

// ---------------------------------------------------------------- estado
static proto::Receiver rx;
static uint8_t tx_seq = 0;
static uint32_t last_cmd_ms = 0;
static float sp_left = 0, sp_right = 0;          // setpoints pedidos [m/s]
static float ramp_left = 0, ramp_right = 0;      // setpoints con rampa
static float v_left = 0, v_right = 0;            // medidos (filtrados)
static int64_t last_cnt_l = 0, last_cnt_r = 0;
static ctl::VelocityPI pi_l, pi_r;
static ctl::FlipperCtl flip;
static ctl::Unwrapper flip_unwrap;
static uint8_t flip_mode = 0;
static float flip_value = 0;
static float flip_angle = 0, flip_vel = 0, flip_zero = 0;
static bool flip_calibrated = false;
static float max_accel = DEFAULT_MAX_ACCEL;
static bool motors_enabled = false;              // "armado" por software (CMD_AUX bit0)
static uint8_t faults = 0;
static uint16_t batt_mv = 0;
static float batt_a = 0;
static uint8_t led_mode = 0;
static uint32_t loop_us_max = 0;

// canales LEDC
enum { CH_L = 0, CH_R = 1, CH_FLIP = 2, CH_AUX2 = 3, CH_LIGHTS = 4 };

static void pwm_setup(int pin, int ch) {
  ledcSetup(ch, PWM_FREQ_HZ, PWM_BITS);
  ledcAttachPin(pin, ch);
  ledcWrite(ch, 0);
}

// duty en [-1, 1] -> PWM + DIR
static void motor_write(int ch, int dir_pin, float duty, bool invert) {
  duty = ctl::clampf(duty, -1.0f, 1.0f);
  if (invert) duty = -duty;
  digitalWrite(dir_pin, duty >= 0 ? HIGH : LOW);
  ledcWrite(ch, (uint32_t)(fabsf(duty) * ((1 << PWM_BITS) - 1)));
}

static void stop_all() {
  motor_write(CH_L, PIN_DRV_L_DIR, 0, false);
  motor_write(CH_R, PIN_DRV_R_DIR, 0, false);
  motor_write(CH_FLIP, PIN_FLIP_DIR, 0, false);
  pi_l.reset();
  pi_r.reset();
  ramp_left = ramp_right = 0;
}

// ---------------------------------------------------------------- envío
static void send(uint8_t id, const void* payload, size_t len) {
  uint8_t frame[proto::MAX_FRAME];
  size_t n = proto::build_frame(id, tx_seq++, payload, len, frame);
  if (n && Serial.availableForWrite() >= (int)n) Serial.write(frame, n);
}

static void send_log(const char* txt) { send(proto::MSG_LOG, txt, strnlen(txt, proto::MAX_PAYLOAD)); }

// ---------------------------------------------------------------- recepción
static void handle_packet() {
  using namespace proto;
  switch (rx.id) {
    case CMD_DRIVE:
      if (rx.len == sizeof(CmdDrive)) {
        CmdDrive c;
        memcpy(&c, rx.payload, sizeof c);
        sp_left = ctl::clampf(c.v_left, -MAX_TRACK_SPEED, MAX_TRACK_SPEED);
        sp_right = ctl::clampf(c.v_right, -MAX_TRACK_SPEED, MAX_TRACK_SPEED);
        last_cmd_ms = millis();
      }
      break;
    case CMD_FLIPPER:
      if (rx.len == sizeof(CmdFlipper)) {
        CmdFlipper c;
        memcpy(&c, rx.payload, sizeof c);
        if (c.mode != flip_mode) flip.clear_stall();
        flip_mode = c.mode;
        flip_value = c.value;
        last_cmd_ms = millis();
      }
      break;
    case CMD_AUX:
      if (rx.len == sizeof(CmdAux)) {
        CmdAux c;
        memcpy(&c, rx.payload, sizeof c);
        ledcWrite(CH_LIGHTS, (uint32_t)c.lights * ((1 << PWM_BITS) - 1) / 255);
        led_mode = c.led_mode;
        bool en = c.flags & 0x01;
        if (en && !motors_enabled) {
          pi_l.reset();
          pi_r.reset();
          flip.clear_stall();
        }
        motors_enabled = en;
        digitalWrite(PIN_BUZZER, (c.flags & 0x02) ? HIGH : LOW);
      }
      break;
    case CMD_CONFIG:
      if (rx.len == sizeof(CmdConfig)) {
        CmdConfig c;
        memcpy(&c, rx.payload, sizeof c);
        pi_l.kp = pi_r.kp = c.kp;
        pi_l.ki = pi_r.ki = c.ki;
        pi_l.kff = pi_r.kff = c.kff;
        max_accel = c.max_accel;
        flip.kp = c.flip_kp;
        flip.max_vel = c.flip_max_vel;
        send_log("config aplicada");
      }
      break;
    case CMD_HEARTBEAT:
      last_cmd_ms = millis();
      break;
    case CMD_ZERO_FLIPPER:
      flip_zero += flip_angle;
      flip_unwrap = ctl::Unwrapper();
      flip_calibrated = true;
      send_log("flipper: cero calibrado");
      break;
    case CMD_GET_INFO: {
      uint8_t buf[40];
      buf[0] = proto::VERSION;
      size_t n = strlen(FW_VERSION);
      memcpy(buf + 1, FW_VERSION, n);
      send(MSG_INFO, buf, n + 1);
      break;
    }
    default:
      break;
  }
}

// ---------------------------------------------------------------- sensores
static void read_flipper(float dt) {
  uint16_t raw = analogRead(PIN_FLIP_ANGLE);
  // AS5600 desconectado/sin imán suele dar 0 o 4095 fijo: lo marcamos como error
  static uint16_t same = 0, last_raw = 0;
  same = (raw == last_raw && (raw < 5 || raw > 4090)) ? same + 1 : 0;
  last_raw = raw;
  if (same > 200) faults |= proto::F_FLIP_SENSOR; else faults &= ~proto::F_FLIP_SENSOR;
  float a = ctl::as5600_angle(raw, 4095, flip_zero, INVERT_FLIP_SENSOR);
  float unwrapped = flip_unwrap.update(a);
  float vel = (unwrapped - flip_angle) / dt;
  flip_vel = 0.8f * flip_vel + 0.2f * vel;
  flip_angle = unwrapped;
}

static void read_power() {
  if (ina_ok) {
    batt_mv = (uint16_t)(ina.getBusVoltage() * 1000.0f);
    batt_a = ina.getCurrent();
  }
  if (batt_mv > 5000 && batt_mv < BATT_LOW_MV) faults |= proto::F_BATT_LOW; else faults &= ~proto::F_BATT_LOW;
  if (batt_mv > 5000 && batt_mv < BATT_CRIT_MV) faults |= proto::F_BATT_CRIT;  // queda latcheado
  if (fabsf(batt_a) > OVERCURRENT_A) faults |= proto::F_OVERCURRENT; else faults &= ~proto::F_OVERCURRENT;
  if (digitalRead(PIN_ESTOP_SENSE) == LOW) faults |= proto::F_ESTOP; else faults &= ~proto::F_ESTOP;
}

// ---------------------------------------------------------------- LEDs
static void update_leds(uint32_t now) {
  uint32_t c;
  bool blink = (now / 250) % 2;
  if (faults & proto::F_ESTOP) c = blink ? leds.Color(255, 0, 0) : 0;
  else if (faults & (proto::F_BATT_CRIT | proto::F_OVERCURRENT | proto::F_FLIP_STALL)) c = leds.Color(255, 0, 0);
  else if (faults & proto::F_CMD_TIMEOUT) c = blink ? leds.Color(255, 120, 0) : 0;
  else if (faults & proto::F_BATT_LOW) c = leds.Color(255, 120, 0);
  else if (led_mode == 1) c = leds.Color(0, 80, 255);     // autónomo (azul, reglamento: visible)
  else if (motors_enabled) c = leds.Color(0, 255, 0);
  else c = leds.Color(0, 60, 0);
  for (int i = 0; i < 8; i++) leds.setPixelColor(i, c);
  leds.show();
}

// ---------------------------------------------------------------- setup / loop
void setup() {
  Serial.setRxBufferSize(1024);
  Serial.begin(921600);   // USB CDC nativo: la velocidad es simbólica
  pinMode(PIN_DRV_L_DIR, OUTPUT);
  pinMode(PIN_DRV_R_DIR, OUTPUT);
  pinMode(PIN_FLIP_DIR, OUTPUT);
  pinMode(PIN_AUX2_DIR, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_ESTOP_SENSE, INPUT);
  pwm_setup(PIN_DRV_L_PWM, CH_L);
  pwm_setup(PIN_DRV_R_PWM, CH_R);
  pwm_setup(PIN_FLIP_PWM, CH_FLIP);
  pwm_setup(PIN_AUX2_PWM, CH_AUX2);
  pwm_setup(PIN_LIGHTS, CH_LIGHTS);
  stop_all();

  analogReadResolution(12);
  analogSetPinAttenuation(PIN_FLIP_ANGLE, ADC_11db);
  analogSetPinAttenuation(PIN_HALL, ADC_11db);

  ESP32Encoder::useInternalWeakPullResistors = puType::up;
  encL.attachFullQuad(PIN_ENC_L_A, PIN_ENC_L_B);
  encR.attachFullQuad(PIN_ENC_R_A, PIN_ENC_R_B);
  encL.setFilter(250);
  encR.setFilter(250);

  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  // IMUPLUS = acelerómetro + giróscopo (sin magnetómetro: los motores lo enloquecen)
  imu_ok = bno.begin(OPERATION_MODE_IMUPLUS);
  if (imu_ok) bno.setExtCrystalUse(true);
  ina_ok = ina.begin();
  if (ina_ok) ina.setMaxCurrentShunt(40.0f, 0.002f);   // shunt externo 2 mΩ / 40 A

  leds.begin();
  leds.setBrightness(60);
  last_cmd_ms = millis();
  send_log(FW_VERSION " iniciado");
}

void loop() {
  static uint32_t t_ctrl = micros(), t_state = 0, t_imu = 0, t_aux = 0;
  uint32_t t_start = micros();

  // 1) recepción no bloqueante
  while (Serial.available()) {
    if (rx.push((uint8_t)Serial.read())) handle_packet();
  }

  uint32_t now_us = micros();
  uint32_t now = millis();

  // 2) lazo de control a 200 Hz
  if (now_us - t_ctrl >= CONTROL_PERIOD_US) {
    float dt = (now_us - t_ctrl) * 1e-6f;
    t_ctrl = now_us;

    int64_t cl = encL.getCount(), cr = encR.getCount();
    float vl = (cl - last_cnt_l) / COUNTS_PER_M / dt * (INVERT_LEFT ? -1 : 1);
    float vr = (cr - last_cnt_r) / COUNTS_PER_M / dt * (INVERT_RIGHT ? -1 : 1);
    last_cnt_l = cl;
    last_cnt_r = cr;
    v_left = 0.7f * v_left + 0.3f * vl;
    v_right = 0.7f * v_right + 0.3f * vr;

    read_flipper(dt);
    if (flip.stalled) faults |= proto::F_FLIP_STALL; else faults &= ~proto::F_FLIP_STALL;

    bool timeout = (now - last_cmd_ms) > CMD_TIMEOUT_MS;
    if (timeout) faults |= proto::F_CMD_TIMEOUT; else faults &= ~proto::F_CMD_TIMEOUT;

    bool can_move = motors_enabled && !timeout &&
                    !(faults & (proto::F_ESTOP | proto::F_BATT_CRIT | proto::F_OVERCURRENT));
    if (!can_move) {
      stop_all();
      sp_left = sp_right = 0;
    } else {
      ramp_left = ctl::slew(ramp_left, sp_left, max_accel, dt);
      ramp_right = ctl::slew(ramp_right, sp_right, max_accel, dt);
      motor_write(CH_L, PIN_DRV_L_DIR, pi_l.update(ramp_left, v_left, dt), INVERT_LEFT);
      motor_write(CH_R, PIN_DRV_R_DIR, pi_r.update(ramp_right, v_right, dt), INVERT_RIGHT);
      bool flip_ok = !(faults & proto::F_FLIP_SENSOR) && (flip_calibrated || flip_mode == 2);
      float fd = flip_ok ? flip.update(flip_mode, flip_value, flip_angle, flip_vel, dt) : 0.0f;
      motor_write(CH_FLIP, PIN_FLIP_DIR, fd, INVERT_FLIP_MOTOR);
    }
  }

  // 3) telemetría
  if (now - t_state >= STATE_PERIOD_MS) {
    t_state = now;
    read_power();
    proto::StateMsg s{};
    s.t_ms = now;
    s.enc_left = (int32_t)encL.getCount();
    s.enc_right = (int32_t)encR.getCount();
    s.v_left = v_left;
    s.v_right = v_right;
    s.flip_angle = flip_angle;
    s.flip_vel = flip_vel;
    s.batt_mv = batt_mv;
    s.batt_ca = (int16_t)ctl::clampf(batt_a * 100.0f, -32000, 32000);
    s.faults = faults;
    s.flags = (motors_enabled ? 1 : 0) | (flip_calibrated ? 2 : 0);
    send(proto::MSG_STATE, &s, sizeof s);
  }
  if (imu_ok && now - t_imu >= IMU_PERIOD_MS) {
    t_imu = now;
    proto::ImuMsg m{};
    imu::Quaternion q = bno.getQuat();
    imu::Vector<3> g = bno.getVector(Adafruit_BNO055::VECTOR_GYROSCOPE);
    imu::Vector<3> a = bno.getVector(Adafruit_BNO055::VECTOR_ACCELEROMETER);
    m.qw = q.w(); m.qx = q.x(); m.qy = q.y(); m.qz = q.z();
    m.gx = g.x() * DEG_TO_RAD; m.gy = g.y() * DEG_TO_RAD; m.gz = g.z() * DEG_TO_RAD;
    m.ax = a.x(); m.ay = a.y(); m.az = a.z();
    uint8_t sys, gyr, acc, mag;
    bno.getCalibration(&sys, &gyr, &acc, &mag);
    m.calib = (sys << 6) | (gyr << 4) | (acc << 2) | mag;
    send(proto::MSG_IMU, &m, sizeof m);
  } else if (!imu_ok) {
    faults |= proto::F_IMU;
  }
  if (now - t_aux >= AUX_PERIOD_MS) {
    t_aux = now;
    proto::AuxMsg m{};
    m.hall_raw = analogRead(PIN_HALL);
    // SS49E: 1.8 mV/G alrededor de VCC/2 (alimentado a 3.3 V) -> mT
    float mv = m.hall_raw * 3300.0f / 4095.0f;
    m.hall_mT = (mv - 1650.0f) / 18.0f;
    m.board_temp_c10 = (int16_t)(temperatureRead() * 10.0f);
    m.loop_us_max = (uint16_t)min<uint32_t>(loop_us_max, 65535);
    loop_us_max = 0;
    send(proto::MSG_AUX, &m, sizeof m);
    update_leds(now);
  }

  uint32_t dur = micros() - t_start;
  if (dur > loop_us_max) loop_us_max = dur;
}
