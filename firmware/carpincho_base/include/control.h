// Controladores puros (sin Arduino) para poder probarlos en la PC.
#pragma once
#include <math.h>
#include <stdint.h>

namespace ctl {

inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

// Limitador de aceleración (rampa): mueve `cur` hacia `target` a lo sumo max_rate*dt.
inline float slew(float cur, float target, float max_rate, float dt) {
  float step = max_rate * dt;
  if (target > cur + step) return cur + step;
  if (target < cur - step) return cur - step;
  return target;
}

// PI de velocidad con feed-forward y anti-windup por saturación condicional.
// Salida en "duty" [-1, 1].
struct VelocityPI {
  float kp = 0.8f, ki = 4.0f, kff = 1.0f / 0.75f;  // kff = 1 / velocidad a duty 100% [m/s]
  float integ = 0.0f;

  float update(float setpoint, float measured, float dt) {
    float err = setpoint - measured;
    float ff = kff * setpoint;
    float out_unsat = ff + kp * err + integ;
    // solo integrar si no estamos saturados en la misma dirección del error
    bool sat_hi = out_unsat > 1.0f && err > 0;
    bool sat_lo = out_unsat < -1.0f && err < 0;
    if (!sat_hi && !sat_lo) integ = clampf(integ + ki * err * dt, -0.6f, 0.6f);
    if (fabsf(setpoint) < 1e-3f && fabsf(measured) < 0.02f) integ *= 0.9f;  // descarga en reposo
    return clampf(ff + kp * err + integ, -1.0f, 1.0f);
  }
  void reset() { integ = 0.0f; }
};

// Control de posición del flipper: P con velocidad máxima, banda muerta y detección de atasco.
struct FlipperCtl {
  float kp = 3.0f;           // [1/s]  -> velocidad pedida = kp * error
  float max_vel = 1.5f;      // rad/s
  float vel_to_duty = 0.55f; // duty por rad/s (feed-forward)
  float deadband = 0.02f;    // rad
  float min_angle = -1.745f, max_angle = 3.316f;   // -100° .. +190°
  float stall_time = 0.0f;
  bool stalled = false;

  // mode 1 = posición (value en rad), 2 = velocidad (value en rad/s). Devuelve duty.
  float update(uint8_t mode, float value, float angle, float vel, float dt) {
    if (stalled) return 0.0f;
    float v_cmd = 0.0f;
    if (mode == 1) {
      float target = clampf(value, min_angle, max_angle);
      float err = target - angle;
      if (fabsf(err) < deadband) return 0.0f;
      v_cmd = clampf(kp * err, -max_vel, max_vel);
    } else if (mode == 2) {
      v_cmd = clampf(value, -max_vel, max_vel);
      // límites blandos en modo velocidad
      if ((angle <= min_angle && v_cmd < 0) || (angle >= max_angle && v_cmd > 0)) v_cmd = 0.0f;
    } else {
      return 0.0f;
    }
    float duty = clampf(v_cmd * vel_to_duty, -1.0f, 1.0f);
    // atasco: pedimos mucho y no se mueve durante 1.5 s -> cortar (la correa patina antes de romper)
    if (fabsf(duty) > 0.5f && fabsf(vel) < 0.05f) {
      stall_time += dt;
      if (stall_time > 1.5f) stalled = true;
    } else {
      stall_time = 0.0f;
    }
    return stalled ? 0.0f : duty;
  }
  void clear_stall() { stalled = false; stall_time = 0.0f; }
};

// Convierte la lectura analógica del AS5600 (0..adc_max) a ángulo [-pi, pi) con offset de cero.
inline float as5600_angle(uint16_t raw, uint16_t adc_max, float zero_offset, bool invert) {
  float a = (float)raw / (float)adc_max * 2.0f * (float)M_PI;
  if (invert) a = -a;
  a -= zero_offset;
  while (a >= (float)M_PI) a -= 2.0f * (float)M_PI;
  while (a < -(float)M_PI) a += 2.0f * (float)M_PI;
  return a;
}

// "Desenrolla" un ángulo envuelto en [-pi, pi) para permitir rango > 360° útil (el flipper llega a 190°).
struct Unwrapper {
  bool init = false;
  float last = 0.0f, total = 0.0f;
  float update(float wrapped) {
    if (!init) { init = true; last = wrapped; total = wrapped; return total; }
    float d = wrapped - last;
    if (d > (float)M_PI) d -= 2.0f * (float)M_PI;
    if (d < -(float)M_PI) d += 2.0f * (float)M_PI;
    total += d;
    last = wrapped;
    return total;
  }
};

}  // namespace ctl
