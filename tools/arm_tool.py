#!/usr/bin/env python3
"""Herramienta de banco para los servos Feetech STS3215 del brazo (sin ROS).

    python3 tools/arm_tool.py scan                    # lista los IDs que responden (1..20)
    python3 tools/arm_tool.py setid 1 4               # cambia el ID 1 -> 4 (¡un solo servo en el bus!)
    python3 tools/arm_tool.py read                    # lee posición/tensión/temperatura de todos
    python3 tools/arm_tool.py zeros                   # torque OFF, mover el brazo a la pose cero
                                                      # (eslabones verticales) y Enter: imprime los
                                                      # "zeros" listos para pegar en arm.yaml
Opciones: --port /dev/carpincho_arm --baud 1000000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ros2_ws/src/carpincho_arm"))
from carpincho_arm import feetech as ft  # noqa: E402

JOINT_IDS = {"arm_j1": [1], "arm_j2": [2, 3], "arm_j3": [4], "arm_j4": [5], "arm_j5": [6], "gripper": [7]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "setid", "read", "zeros"])
    ap.add_argument("args", nargs="*", type=int)
    ap.add_argument("--port", default="/dev/carpincho_arm")
    ap.add_argument("--baud", type=int, default=1_000_000)
    a = ap.parse_args()
    bus = ft.Bus(a.port, a.baud)
    if a.cmd == "scan":
        found = [i for i in range(1, 21) if bus.ping(i)]
        print("IDs encontrados:", found or "ninguno (¿12 V conectados? ¿baudrate?)")
    elif a.cmd == "setid":
        old, new = a.args
        print("OK" if bus.set_id(old, new) else "FALLÓ")
    elif a.cmd == "read":
        for name, ids in JOINT_IDS.items():
            for sid in ids:
                fb = bus.read_feedback(sid)
                print(f"{name:8s} id={sid}: {fb if fb else 'sin respuesta'}")
    elif a.cmd == "zeros":
        for ids in JOINT_IDS.values():
            for sid in ids:
                bus.torque(sid, False)
        input("Torque OFF. Poné el brazo en pose cero (todo vertical, pinza cerrada) y apretá Enter... ")
        for name, ids in JOINT_IDS.items():
            vals = [bus.read_position(sid) for sid in ids]
            print(f"    {name}: zeros: {vals}")
    bus.close()


if __name__ == "__main__":
    main()
