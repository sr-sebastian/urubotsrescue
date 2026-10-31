// Tests de PC para protocol.h y control.h (no necesitan la placa).
//   g++ -std=c++17 -Wall -Wextra -I include test_host/test_protocol.cpp -o /tmp/tp && /tmp/tp
#include <cassert>
#include <cmath>
#include <cstdio>
#include <vector>

#include "control.h"
#include "protocol.h"

static int fails = 0;
#define CHECK(c)                                                   \
  do {                                                             \
    if (!(c)) { std::printf("FALLA %s:%d  %s\n", __FILE__, __LINE__, #c); fails++; } \
  } while (0)

static void test_crc() {
  const char* s = "123456789";
  CHECK(proto::crc16((const uint8_t*)s, 9) == 0x29B1);   // vector estándar CCITT-FALSE
}

static void test_cobs_roundtrip() {
  for (size_t n = 0; n < 300; n += 7) {
    std::vector<uint8_t> in(n), enc(n + n / 254 + 2), dec(n + 2);
    for (size_t i = 0; i < n; i++) in[i] = (uint8_t)((i * 37) % 5 == 0 ? 0 : i * 13);
    size_t m = proto::cobs_encode(in.data(), n, enc.data());
    for (size_t i = 0; i < m; i++) CHECK(enc[i] != 0);
    size_t k = proto::cobs_decode(enc.data(), m, dec.data());
    CHECK(k == n);
    for (size_t i = 0; i < n; i++) CHECK(dec[i] == in[i]);
  }
}

static void test_frame_and_receiver() {
  proto::CmdDrive c{0.5f, -0.25f};
  uint8_t frame[proto::MAX_FRAME];
  size_t n = proto::build_frame(proto::CMD_DRIVE, 7, &c, sizeof c, frame);
  CHECK(frame[n - 1] == 0);
  // vector de referencia compartido con el test de Python (test_protocol.py)
  const uint8_t expected[] = {0x03, 0x01, 0x07, 0x01, 0x01, 0x02, 0x3f, 0x01,
                              0x05, 0x80, 0xbe, 0x4d, 0x0b, 0x00};
  CHECK(n == sizeof expected);
  for (size_t i = 0; i < n && i < sizeof expected; i++) CHECK(frame[i] == expected[i]);
  std::printf("trama CMD_DRIVE(0.5,-0.25) seq=7: ");
  for (size_t i = 0; i < n; i++) std::printf("%02x", frame[i]);
  std::printf("\n");

  proto::Receiver rx;
  // basura antes, para probar la resincronización
  const uint8_t junk[] = {0x11, 0x22, 0x00, 0x05, 0x00};
  for (uint8_t b : junk) rx.push(b);
  bool got = false;
  for (size_t i = 0; i < n; i++) got = rx.push(frame[i]);
  CHECK(got);
  CHECK(rx.id == proto::CMD_DRIVE && rx.seq == 7 && rx.len == sizeof c);
  proto::CmdDrive d;
  memcpy(&d, rx.payload, sizeof d);
  CHECK(d.v_left == 0.5f && d.v_right == -0.25f);
  // trama corrupta -> error de CRC
  frame[3] ^= 0x40;
  got = false;
  for (size_t i = 0; i < n; i++) got = rx.push(frame[i]);
  CHECK(!got);
  CHECK(rx.crc_errors + rx.framing_errors >= 1);
}

static void test_pi() {
  ctl::VelocityPI pi;
  float v = 0;
  // planta de primer orden: v' = (0.75*duty - v)/0.1
  for (int i = 0; i < 400; i++) {
    float u = pi.update(0.4f, v, 0.005f);
    v += (0.75f * u - v) / 0.1f * 0.005f;
  }
  CHECK(std::fabs(v - 0.4f) < 0.01f);
  // saturación: setpoint inalcanzable no debe acumular integral infinita
  for (int i = 0; i < 2000; i++) pi.update(5.0f, 0.75f, 0.005f);
  CHECK(pi.integ <= 0.6f + 1e-6f);
}

static void test_flipper() {
  ctl::FlipperCtl f;
  float ang = 0, vel = 0;
  for (int i = 0; i < 2000; i++) {
    float duty = f.update(1, 1.0f, ang, vel, 0.005f);
    vel = duty / f.vel_to_duty;   // planta ideal
    ang += vel * 0.005f;
  }
  CHECK(std::fabs(ang - 1.0f) < 0.03f);
  // atasco: el flipper no se mueve aunque pidamos mucho
  ctl::FlipperCtl g;
  for (int i = 0; i < 400; i++) g.update(1, 2.0f, 0.0f, 0.0f, 0.005f);
  CHECK(g.stalled);
  // límite: no supera max_angle
  ctl::FlipperCtl h;
  CHECK(h.update(2, 1.0f, h.max_angle + 0.01f, 0, 0.005f) == 0.0f);
}

static void test_unwrap() {
  ctl::Unwrapper u;
  float a = 0;
  for (int i = 0; i <= 400; i++) {
    float t = i * 0.01f;   // 0 .. 4 rad
    float w = std::atan2(std::sin(t), std::cos(t));
    a = u.update(w);
  }
  CHECK(std::fabs(a - 4.0f) < 1e-3f);
  CHECK(std::fabs(ctl::as5600_angle(2048, 4095, 0, false) - (float)M_PI) < 0.01f ||
        std::fabs(ctl::as5600_angle(2048, 4095, 0, false) + (float)M_PI) < 0.01f);
}

int main() {
  test_crc();
  test_cobs_roundtrip();
  test_frame_and_receiver();
  test_pi();
  test_flipper();
  test_unwrap();
  if (fails) { std::printf("%d fallas\n", fails); return 1; }
  std::printf("OK: todos los tests de firmware pasaron\n");
  return 0;
}
