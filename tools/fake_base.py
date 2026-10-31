#!/usr/bin/env python3
"""Simulador de la placa base ESP32 en un puerto serie virtual (pty). Sirve para probar todo el
software del Jetson SIN el robot: base_bridge, teleop, autonomía, RViz...

    python3 tools/fake_base.py                   # imprime el puerto, p. ej. /dev/pts/5
    ros2 run carpincho_base base_bridge --ros-args -p port:=/dev/pts/5 -p auto_enable:=true

Simula: orugas con rampa de aceleración, encoders, flipper con velocidad máx., IMU (yaw
integrado), batería que se descarga, watchdog de 300 ms y el E-stop (tecla 'e' + Enter).
"""

from __future__ import annotations

import math
import os
import pty
import select
import struct
import sys
import threading
import time
import tty
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ros2_ws/src/carpincho_base"))
from carpincho_base import protocol as P  # noqa: E402

COUNTS_PER_M = 7140.2
TRACK_SEP_EFF = 0.275 * 1.6


class FakeBase:
    def __init__(self) -> None:
        self.master, slave = pty.openpty()
        tty.setraw(self.master)
        self.port = os.ttyname(slave)
        self.rx = P.Receiver()
        self.seq = 0
        self.sp = [0.0, 0.0]
        self.v = [0.0, 0.0]
        self.enc = [0.0, 0.0]
        self.flip = 0.0
        self.flip_mode, self.flip_value = 0, 0.0
        self.enabled = False
        self.last_cmd = 0.0
        self.yaw = 0.0
        self.batt = 25.0
        self.estop = False
        self.zeroed = False

    def send(self, msg_id: int, payload: bytes) -> None:
        os.write(self.master, P.build_frame(msg_id, self.seq, payload))
        self.seq = (self.seq + 1) & 0xFF

    def handle(self, pkt: P.Packet) -> None:
        if pkt.msg_id == P.CMD_DRIVE:
            self.sp = list(struct.unpack(P.FMT_CMD_DRIVE, pkt.payload))
            self.last_cmd = time.monotonic()
        elif pkt.msg_id == P.CMD_FLIPPER:
            self.flip_mode, self.flip_value = struct.unpack(P.FMT_CMD_FLIPPER, pkt.payload)
            self.last_cmd = time.monotonic()
        elif pkt.msg_id == P.CMD_AUX:
            _, _, flags = struct.unpack(P.FMT_CMD_AUX, pkt.payload)
            self.enabled = bool(flags & 1)
        elif pkt.msg_id == P.CMD_HEARTBEAT:
            self.last_cmd = time.monotonic()
        elif pkt.msg_id == P.CMD_ZERO_FLIPPER:
            self.flip, self.zeroed = 0.0, True
            self.send(P.MSG_LOG, b"flipper: cero calibrado")
        elif pkt.msg_id == P.CMD_GET_INFO:
            self.send(P.MSG_INFO, bytes([P.VERSION]) + b"fake-base 0.1")

    def run(self) -> None:
        print(f"Placa base simulada en: {self.port}   (tecla e + Enter = E-stop)", flush=True)
        threading.Thread(target=self.keyboard, daemon=True).start()
        t_last_imu, t_prev = 0.0, time.monotonic()
        while True:
            r, _, _ = select.select([self.master], [], [], 0.005)
            if r:
                for pkt in self.rx.feed(os.read(self.master, 512)):
                    self.handle(pkt)
            now = time.monotonic()
            dt = now - t_prev
            if dt < 0.02:
                continue
            t_prev = now
            timeout = time.monotonic() - self.last_cmd > 0.3
            if self.estop:
                self.enabled = False      # igual que el firmware: el E-stop desarma
            can = self.enabled and not timeout and not self.estop
            for i in range(2):
                target = self.sp[i] if can else 0.0
                step = 1.0 * dt
                self.v[i] += max(-step, min(step, target - self.v[i]))
                self.enc[i] += self.v[i] * dt * COUNTS_PER_M * (1 if i == 0 else -1)
            self.yaw += (self.v[1] - self.v[0]) / TRACK_SEP_EFF * dt
            if can and self.flip_mode == 1:
                self.flip += max(-1.5 * dt, min(1.5 * dt, self.flip_value - self.flip))
            elif can and self.flip_mode == 2:
                self.flip += max(-1.5, min(1.5, self.flip_value)) * dt
            self.batt = max(19.0, self.batt - 1e-5 - 2e-5 * (abs(self.v[0]) + abs(self.v[1])))
            faults = (1 if timeout else 0) | (0x80 if self.estop else 0) | (0x02 if self.batt < 21.6 else 0)
            st = struct.pack(P.FMT_STATE, int(time.monotonic() * 1000) & 0xFFFFFFFF, int(self.enc[0]),
                             int(self.enc[1]), self.v[0], self.v[1], self.flip, 0.0, int(self.batt * 1000),
                             int(150 + 800 * (abs(self.v[0]) + abs(self.v[1]))), faults,
                             (1 if self.enabled else 0) | (2 if self.zeroed else 0))
            self.send(P.MSG_STATE, st)
            if now - t_last_imu > 0.01:
                t_last_imu = now
                q = (math.cos(self.yaw / 2), 0.0, 0.0, math.sin(self.yaw / 2))
                wz = (self.v[1] - self.v[0]) / TRACK_SEP_EFF
                self.send(P.MSG_IMU, struct.pack(P.FMT_IMU, *q, 0.0, 0.0, wz, 0.0, 0.0, 9.81, 0xFF))

    def keyboard(self) -> None:
        for line in sys.stdin:
            if line.strip().lower() == "e":
                self.estop = not self.estop
                print("E-STOP", "APRETADO" if self.estop else "liberado", flush=True)


if __name__ == "__main__":
    try:
        FakeBase().run()
    except KeyboardInterrupt:
        pass
