"""Protocolo serie Jetson <-> ESP32. Espejo exacto de firmware/carpincho_base/include/protocol.h.

Trama: COBS(id | seq | payload | crc16 LE) + 0x00.  CRC-16/CCITT-FALSE sobre id+seq+payload.
Este módulo es Python puro (sin ROS) para poder testearlo y usarlo desde tools/base_monitor.py.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

VERSION = 1
MAX_PAYLOAD = 64

# ---- IDs -----------------------------------------------------------------------
CMD_DRIVE = 0x01
CMD_FLIPPER = 0x02
CMD_AUX = 0x03
CMD_CONFIG = 0x04
CMD_HEARTBEAT = 0x05
CMD_ZERO_FLIPPER = 0x06
CMD_GET_INFO = 0x07
MSG_STATE = 0x81
MSG_IMU = 0x82
MSG_AUX = 0x83
MSG_LOG = 0x84
MSG_INFO = 0x85

FLIP_MODE_OFF = 0
FLIP_MODE_POSITION = 1
FLIP_MODE_VELOCITY = 2

FAULTS = {
    0x01: "CMD_TIMEOUT",
    0x02: "BATT_LOW",
    0x04: "BATT_CRIT",
    0x08: "FLIP_SENSOR",
    0x10: "FLIP_STALL",
    0x20: "IMU",
    0x40: "OVERCURRENT",
    0x80: "ESTOP",
}

# ---- formatos (deben coincidir con los struct packed del firmware) --------------
FMT_CMD_DRIVE = "<ff"
FMT_CMD_FLIPPER = "<Bf"
FMT_CMD_AUX = "<BBB"
FMT_CMD_CONFIG = "<ffffff"
FMT_CMD_HEARTBEAT = "<I"
FMT_STATE = "<IiiffffHhBB"      # 34 bytes
FMT_IMU = "<ffffffffffB"        # 41 bytes
FMT_AUX = "<fHhH"               # 10 bytes

assert struct.calcsize(FMT_STATE) == 34
assert struct.calcsize(FMT_IMU) == 41
assert struct.calcsize(FMT_AUX) == 10


def fault_names(mask: int) -> list[str]:
    return [name for bit, name in FAULTS.items() if mask & bit]


# ---- CRC / COBS -----------------------------------------------------------------
def crc16(data: bytes, crc: int = 0xFFFF) -> int:
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def cobs_encode(data: bytes) -> bytes:
    out = bytearray([0])
    code_idx, code = 0, 1
    for b in data:
        if b == 0:
            out[code_idx] = code
            code_idx = len(out)
            out.append(0)
            code = 1
        else:
            out.append(b)
            code += 1
            if code == 0xFF:
                out[code_idx] = code
                code_idx = len(out)
                out.append(0)
                code = 1
    out[code_idx] = code
    return bytes(out)


def cobs_decode(data: bytes) -> bytes | None:
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        code = data[i]
        i += 1
        if code == 0:
            return None
        for _ in range(code - 1):
            if i >= n or data[i] == 0:
                return None
            out.append(data[i])
            i += 1
        if code != 0xFF and i < n:
            out.append(0)
    return bytes(out)


def build_frame(msg_id: int, seq: int, payload: bytes = b"") -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload demasiado grande")
    pkt = bytes([msg_id & 0xFF, seq & 0xFF]) + payload
    c = crc16(pkt)
    return cobs_encode(pkt + struct.pack("<H", c)) + b"\x00"


@dataclass
class Packet:
    msg_id: int
    seq: int
    payload: bytes


class Receiver:
    """Receptor incremental: feed(bytes) devuelve la lista de paquetes válidos completos."""

    MAX_FRAME = MAX_PAYLOAD + 4 + 4

    def __init__(self) -> None:
        self._buf = bytearray()
        self.crc_errors = 0
        self.framing_errors = 0

    def feed(self, data: bytes) -> list[Packet]:
        out = []
        for b in data:
            if b != 0:
                self._buf.append(b)
                if len(self._buf) > self.MAX_FRAME * 2:   # basura larga sin 0x00
                    self._buf.clear()
                    self.framing_errors += 1
                continue
            if not self._buf:
                continue
            raw = cobs_decode(bytes(self._buf))
            self._buf.clear()
            if raw is None or len(raw) < 4:
                self.framing_errors += 1
                continue
            (c,) = struct.unpack("<H", raw[-2:])
            if crc16(raw[:-2]) != c:
                self.crc_errors += 1
                continue
            out.append(Packet(raw[0], raw[1], raw[2:-2]))
        return out


# ---- (de)serialización de alto nivel -------------------------------------------
@dataclass
class State:
    t_ms: int
    enc_left: int
    enc_right: int
    v_left: float
    v_right: float
    flip_angle: float
    flip_vel: float
    batt_mv: int
    batt_ca: int
    faults: int
    flags: int

    @property
    def motors_enabled(self) -> bool:
        return bool(self.flags & 1)

    @property
    def flipper_calibrated(self) -> bool:
        return bool(self.flags & 2)


@dataclass
class Imu:
    qw: float
    qx: float
    qy: float
    qz: float
    gx: float
    gy: float
    gz: float
    ax: float
    ay: float
    az: float
    calib: int


@dataclass
class Aux:
    hall_mT: float
    hall_raw: int
    board_temp_c10: int
    loop_us_max: int


def parse(pkt: Packet):
    """Convierte un Packet en State / Imu / Aux / str (log/info) o None si no se reconoce."""
    try:
        if pkt.msg_id == MSG_STATE:
            return State(*struct.unpack(FMT_STATE, pkt.payload))
        if pkt.msg_id == MSG_IMU:
            return Imu(*struct.unpack(FMT_IMU, pkt.payload))
        if pkt.msg_id == MSG_AUX:
            return Aux(*struct.unpack(FMT_AUX, pkt.payload))
        if pkt.msg_id == MSG_LOG:
            return pkt.payload.decode("ascii", "replace")
        if pkt.msg_id == MSG_INFO:
            return f"protocolo v{pkt.payload[0]}: " + pkt.payload[1:].decode("ascii", "replace")
    except struct.error:
        return None
    return None


def drive(v_left: float, v_right: float) -> bytes:
    return struct.pack(FMT_CMD_DRIVE, v_left, v_right)


def flipper(mode: int, value: float) -> bytes:
    return struct.pack(FMT_CMD_FLIPPER, mode, value)


def aux(lights: int, led_mode: int, enable_motors: bool, buzzer: bool = False) -> bytes:
    flags = (1 if enable_motors else 0) | (2 if buzzer else 0)
    return struct.pack(FMT_CMD_AUX, max(0, min(255, int(lights))), led_mode & 0xFF, flags)


def config(kp: float, ki: float, kff: float, max_accel: float, flip_kp: float, flip_max_vel: float) -> bytes:
    return struct.pack(FMT_CMD_CONFIG, kp, ki, kff, max_accel, flip_kp, flip_max_vel)


def heartbeat(host_ms: int) -> bytes:
    return struct.pack(FMT_CMD_HEARTBEAT, host_ms & 0xFFFFFFFF)


def battery_percent_6s(volts: float) -> float:
    """Estimación grosera del % de una batería 6S Li-ion (21700) en reposo/carga liviana."""
    table = [(19.8, 0), (20.4, 5), (21.0, 10), (21.6, 25), (22.2, 45), (22.8, 60), (23.4, 75),
             (24.0, 88), (24.6, 96), (25.2, 100)]
    if volts <= table[0][0]:
        return 0.0
    for (v0, p0), (v1, p1) in zip(table, table[1:]):
        if volts <= v1:
            return p0 + (p1 - p0) * (volts - v0) / (v1 - v0)
    return 100.0
