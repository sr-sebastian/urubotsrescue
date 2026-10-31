"""Protocolo de bus serie Feetech STS/SMS (STS3215). Python puro, testeable sin hardware.

Paquete:  FF FF  ID  LEN  INSTR  PARAM...  CHK      LEN = nº params + 2
          CHK = ~(ID + LEN + INSTR + sum(PARAM)) & 0xFF
Respuesta: FF FF  ID  LEN  ERROR  PARAM...  CHK
Registros en little-endian (low byte primero). Posición 0..4095 = 0..360°.

Adaptador recomendado: Waveshare "Bus Servo Adapter (A)" o el de Feetech (FE-URT-1), a 1 Mbps.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

# instrucciones
PING = 0x01
READ = 0x02
WRITE = 0x03
REG_WRITE = 0x04
ACTION = 0x05
SYNC_READ = 0x82
SYNC_WRITE = 0x83
BROADCAST = 0xFE

# registros STS3215 (tabla de memoria SMS_STS)
REG_ID = 5
REG_BAUD = 6
REG_MIN_ANGLE = 9
REG_MAX_ANGLE = 11
REG_MODE = 33
REG_TORQUE_ENABLE = 40
REG_ACC = 41
REG_GOAL_POSITION = 42
REG_GOAL_TIME = 44
REG_GOAL_SPEED = 46
REG_LOCK = 55
REG_PRESENT_POSITION = 56
REG_PRESENT_SPEED = 58
REG_PRESENT_LOAD = 60
REG_PRESENT_VOLTAGE = 62
REG_PRESENT_TEMPERATURE = 63
REG_MOVING = 66
REG_PRESENT_CURRENT = 69

TICKS_PER_REV = 4096

ERROR_BITS = {
    0x01: "tensión",
    0x02: "sensor de ángulo",
    0x04: "temperatura",
    0x08: "corriente",
    0x20: "sobrecarga",
}


def checksum(body: bytes) -> int:
    return (~sum(body)) & 0xFF


def packet(servo_id: int, instr: int, params: bytes = b"") -> bytes:
    body = bytes([servo_id & 0xFF, len(params) + 2, instr]) + params
    return b"\xff\xff" + body + bytes([checksum(body)])


def u16(v: int) -> bytes:
    return bytes([v & 0xFF, (v >> 8) & 0xFF])


def signed15(v: int) -> int:
    """Formato de velocidad/posición del STS: bit 15 = signo."""
    return (-(v & 0x7FFF)) if v & 0x8000 else v


def write_packet(servo_id: int, addr: int, data: bytes) -> bytes:
    return packet(servo_id, WRITE, bytes([addr]) + data)


def read_packet(servo_id: int, addr: int, length: int) -> bytes:
    return packet(servo_id, READ, bytes([addr, length]))


def sync_write_packet(addr: int, items: dict[int, bytes]) -> bytes:
    """Escribe el mismo bloque de registros a varios servos en un solo paquete."""
    lens = {len(d) for d in items.values()}
    if len(lens) != 1:
        raise ValueError("todos los datos del sync write deben tener el mismo largo")
    n = lens.pop()
    params = bytes([addr, n])
    for sid, data in items.items():
        params += bytes([sid]) + data
    return packet(BROADCAST, SYNC_WRITE, params)


def goal_block(position: int, time_ms: int = 0, speed: int = 0) -> bytes:
    """Bloque de 6 bytes desde REG_GOAL_POSITION: posición, tiempo, velocidad."""
    position = max(0, min(TICKS_PER_REV - 1, int(round(position))))
    return u16(position) + u16(max(0, time_ms)) + u16(max(0, speed))


@dataclass
class Status:
    servo_id: int
    error: int
    params: bytes

    @property
    def error_names(self) -> list[str]:
        return [n for b, n in ERROR_BITS.items() if self.error & b]


def parse_status(buf: bytes) -> tuple[Status | None, bytes]:
    """Busca un paquete de estado completo al comienzo de `buf`.
    Devuelve (Status o None, resto del buffer)."""
    i = buf.find(b"\xff\xff")
    while i >= 0:
        if len(buf) < i + 4:
            return None, buf[i:]
        sid, ln = buf[i + 2], buf[i + 3]
        if ln < 2 or sid == 0xFF:
            i = buf.find(b"\xff\xff", i + 1)
            continue
        end = i + 4 + ln
        if len(buf) < end:
            return None, buf[i:]
        body = buf[i + 2:end - 1]
        if checksum(body) == buf[end - 1]:
            return Status(sid, buf[i + 4], bytes(buf[i + 5:end - 1])), buf[end:]
        i = buf.find(b"\xff\xff", i + 1)
    return None, b""


class Bus:
    """Acceso al bus con pyserial. Pensado para un solo hilo (el del nodo)."""

    def __init__(self, port: str, baud: int = 1_000_000, timeout: float = 0.02):
        import serial  # import tardío: los tests no lo necesitan

        self.ser = serial.Serial(port, baud, timeout=timeout)
        self.timeout = timeout

    def close(self) -> None:
        self.ser.close()

    def _xfer(self, pkt: bytes, expect_reply: bool = True) -> Status | None:
        self.ser.reset_input_buffer()
        self.ser.write(pkt)
        if not expect_reply:
            return None
        buf = b""
        t0 = time.monotonic()
        while time.monotonic() - t0 < self.timeout * 3:
            buf += self.ser.read(64)
            st, buf = parse_status(buf)
            if st is not None:
                return st
        return None

    def ping(self, sid: int) -> bool:
        return self._xfer(packet(sid, PING)) is not None

    def read(self, sid: int, addr: int, length: int) -> bytes | None:
        st = self._xfer(read_packet(sid, addr, length))
        return st.params if st and len(st.params) == length else None

    def write(self, sid: int, addr: int, data: bytes) -> bool:
        return self._xfer(write_packet(sid, addr, data)) is not None

    def torque(self, sid: int, on: bool) -> bool:
        return self.write(sid, REG_TORQUE_ENABLE, bytes([1 if on else 0]))

    def read_position(self, sid: int) -> int | None:
        d = self.read(sid, REG_PRESENT_POSITION, 2)
        return None if d is None else d[0] | (d[1] << 8)

    def read_feedback(self, sid: int) -> dict | None:
        """Posición, velocidad, carga, tensión y temperatura en una sola lectura (8 bytes)."""
        d = self.read(sid, REG_PRESENT_POSITION, 8)
        if d is None:
            return None
        return dict(position=d[0] | (d[1] << 8), speed=signed15(d[2] | (d[3] << 8)),
                    load=signed15(d[4] | (d[5] << 8)), voltage=d[6] / 10.0, temperature=d[7])

    def sync_goal(self, goals: dict[int, int], time_ms: int = 0, speed: int = 0) -> None:
        items = {sid: goal_block(pos, time_ms, speed) for sid, pos in goals.items()}
        self._xfer(sync_write_packet(REG_GOAL_POSITION, items), expect_reply=False)

    def set_id(self, old: int, new: int) -> bool:
        """Cambia el ID (EEPROM). Conectar UN solo servo al bus para hacer esto."""
        ok = self.write(old, REG_LOCK, b"\x00")
        ok = ok and self.write(old, REG_ID, bytes([new]))
        ok = ok and self.write(new, REG_LOCK, b"\x01")
        return ok
