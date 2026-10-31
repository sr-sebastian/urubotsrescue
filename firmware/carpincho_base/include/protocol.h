// Protocolo serie Jetson <-> ESP32 (placa base del Carpincho).
//
// Trama en el cable:  COBS( id | seq | payload... | crc16_lo | crc16_hi ) 0x00
//   - COBS: elimina los 0x00 del paquete, el 0x00 marca el fin de trama (resincroniza solo).
//   - CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) sobre id+seq+payload.
//   - Todos los números en little-endian. float = IEEE-754 32 bits.
//
// Este archivo es C++ portable (sin Arduino) para poder probarlo en la PC:
//   g++ -std=c++17 -I include test_host/test_protocol.cpp -o /tmp/t && /tmp/t
// La implementación espejo en Python está en
//   ros2_ws/src/carpincho_base/carpincho_base/protocol.py  (¡mantener sincronizadas!)
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace proto {

constexpr uint8_t VERSION = 1;
constexpr size_t MAX_PAYLOAD = 64;
constexpr size_t MAX_PACKET = MAX_PAYLOAD + 4;               // id + seq + payload + crc
constexpr size_t MAX_FRAME = MAX_PACKET + MAX_PACKET / 254 + 2;  // COBS + 0x00

// ---- IDs de mensajes -------------------------------------------------------
enum MsgId : uint8_t {
  // host -> MCU
  CMD_DRIVE = 0x01,        // float v_left, float v_right   [m/s en la superficie de la oruga]
  CMD_FLIPPER = 0x02,      // u8 mode (0 libre/freno, 1 posición, 2 velocidad), float valor [rad | rad/s]
  CMD_AUX = 0x03,          // u8 luces (0-255), u8 modo_led, u8 flags (bit0 habilitar motores, bit1 buzzer)
  CMD_CONFIG = 0x04,       // float kp, ki, kff, max_accel, flip_kp, flip_max_vel
  CMD_HEARTBEAT = 0x05,    // u32 host_ms
  CMD_ZERO_FLIPPER = 0x06, // sin payload: el ángulo actual pasa a ser 0 (flipper horizontal adelante)
  CMD_GET_INFO = 0x07,     // sin payload: pide MSG_INFO
  // MCU -> host
  MSG_STATE = 0x81,        // ver StateMsg (50 Hz)
  MSG_IMU = 0x82,          // ver ImuMsg (100 Hz)
  MSG_AUX = 0x83,          // ver AuxMsg (10 Hz)
  MSG_LOG = 0x84,          // texto ASCII (sin terminador)
  MSG_INFO = 0x85,         // u8 version protocolo + texto versión firmware
};

enum Fault : uint8_t {
  F_CMD_TIMEOUT = 1 << 0,
  F_BATT_LOW = 1 << 1,
  F_BATT_CRIT = 1 << 2,
  F_FLIP_SENSOR = 1 << 3,
  F_FLIP_STALL = 1 << 4,
  F_IMU = 1 << 5,
  F_OVERCURRENT = 1 << 6,
  F_ESTOP = 1 << 7,
};

#pragma pack(push, 1)
struct CmdDrive { float v_left; float v_right; };
struct CmdFlipper { uint8_t mode; float value; };
struct CmdAux { uint8_t lights; uint8_t led_mode; uint8_t flags; };
struct CmdConfig { float kp, ki, kff, max_accel, flip_kp, flip_max_vel; };
struct CmdHeartbeat { uint32_t host_ms; };
struct StateMsg {
  uint32_t t_ms;
  int32_t enc_left, enc_right;      // cuentas acumuladas (x4)
  float v_left, v_right;            // m/s medidas
  float flip_angle, flip_vel;       // rad, rad/s
  uint16_t batt_mv;
  int16_t batt_ca;                  // corriente en centiamperes (0.01 A)
  uint8_t faults;                   // Fault
  uint8_t flags;                    // bit0 motores habilitados, bit1 flipper calibrado
};
struct ImuMsg {
  float qw, qx, qy, qz;
  float gx, gy, gz;                 // rad/s
  float ax, ay, az;                 // m/s^2
  uint8_t calib;                    // sys<<6 | gyr<<4 | acc<<2 | mag
};
struct AuxMsg {
  float hall_mT;                    // campo del sensor Hall de la punta del brazo
  uint16_t hall_raw;
  int16_t board_temp_c10;           // 0.1 °C
  uint16_t loop_us_max;             // peor tiempo de lazo (diagnóstico)
};
#pragma pack(pop)

static_assert(sizeof(StateMsg) == 34, "StateMsg cambió de tamaño: actualizar protocol.py");
static_assert(sizeof(ImuMsg) == 41, "ImuMsg cambió de tamaño: actualizar protocol.py");
static_assert(sizeof(AuxMsg) == 10, "AuxMsg cambió de tamaño: actualizar protocol.py");

// ---- CRC-16/CCITT-FALSE ----------------------------------------------------
inline uint16_t crc16(const uint8_t* d, size_t n, uint16_t crc = 0xFFFF) {
  for (size_t i = 0; i < n; i++) {
    crc ^= (uint16_t)d[i] << 8;
    for (int b = 0; b < 8; b++) crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
  }
  return crc;
}

// ---- COBS ------------------------------------------------------------------
// Codifica `n` bytes en `out` (sin el 0x00 final). Devuelve el largo escrito.
inline size_t cobs_encode(const uint8_t* in, size_t n, uint8_t* out) {
  size_t read = 0, write = 1, code_idx = 0;
  uint8_t code = 1;
  while (read < n) {
    if (in[read] == 0) {
      out[code_idx] = code;
      code = 1;
      code_idx = write++;
      read++;
    } else {
      out[write++] = in[read++];
      code++;
      if (code == 0xFF) {
        out[code_idx] = code;
        code = 1;
        code_idx = write++;
      }
    }
  }
  out[code_idx] = code;
  return write;
}

// Decodifica `n` bytes (sin el 0x00 final). Devuelve el largo o 0 si es inválido.
inline size_t cobs_decode(const uint8_t* in, size_t n, uint8_t* out) {
  size_t read = 0, write = 0;
  while (read < n) {
    uint8_t code = in[read++];
    if (code == 0) return 0;
    for (uint8_t i = 1; i < code; i++) {
      if (read >= n) return 0;
      uint8_t b = in[read++];
      if (b == 0) return 0;
      out[write++] = b;
    }
    if (code != 0xFF && read < n) out[write++] = 0;
  }
  return write;
}

// Arma una trama completa (COBS + 0x00). Devuelve el largo total.
inline size_t build_frame(uint8_t id, uint8_t seq, const void* payload, size_t len, uint8_t* frame) {
  uint8_t pkt[MAX_PACKET];
  if (len > MAX_PAYLOAD) return 0;
  pkt[0] = id;
  pkt[1] = seq;
  if (len) memcpy(pkt + 2, payload, len);
  uint16_t c = crc16(pkt, len + 2);
  pkt[len + 2] = (uint8_t)(c & 0xFF);
  pkt[len + 3] = (uint8_t)(c >> 8);
  size_t m = cobs_encode(pkt, len + 4, frame);
  frame[m] = 0x00;
  return m + 1;
}

// Receptor incremental: alimentar byte a byte con push(); cuando devuelve true hay
// un paquete válido en id/seq/payload/len.
class Receiver {
 public:
  uint8_t id = 0, seq = 0, len = 0;
  uint8_t payload[MAX_PAYLOAD];
  uint32_t crc_errors = 0, framing_errors = 0;

  bool push(uint8_t b) {
    if (b != 0) {
      if (n_ < sizeof(buf_)) buf_[n_++] = b;
      else overflow_ = true;
      return false;
    }
    // fin de trama
    bool ok = false;
    if (n_ > 0 && !overflow_) {
      uint8_t pkt[MAX_FRAME];
      size_t m = cobs_decode(buf_, n_, pkt);
      if (m >= 4 && m - 4 <= MAX_PAYLOAD) {
        uint16_t c = (uint16_t)pkt[m - 2] | ((uint16_t)pkt[m - 1] << 8);
        if (crc16(pkt, m - 2) == c) {
          id = pkt[0];
          seq = pkt[1];
          len = (uint8_t)(m - 4);
          memcpy(payload, pkt + 2, len);
          ok = true;
        } else {
          crc_errors++;
        }
      } else {
        framing_errors++;
      }
    } else if (overflow_) {
      framing_errors++;
    }
    n_ = 0;
    overflow_ = false;
    return ok;
  }

 private:
  uint8_t buf_[MAX_FRAME];
  size_t n_ = 0;
  bool overflow_ = false;
};

}  // namespace proto
