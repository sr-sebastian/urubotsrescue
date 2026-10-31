import math

import pytest

from carpincho_arm import feetech as ft
from carpincho_arm.kinematics import ArmGeometry, Unreachable, fk, ik, interpolate, static_torques

G = ArmGeometry()


def test_packet_checksum_known():
    # PING al ID 1: FF FF 01 02 01 FB  (ejemplo del manual Feetech/Dynamixel 1.0)
    assert ft.packet(1, ft.PING) == bytes.fromhex("ffff010201fb")


def test_parse_status_with_noise():
    reply = ft.packet(3, 0x00, bytes([0x10, 0x08]))   # misma estructura que un estado
    st, rest = ft.parse_status(b"\x00\x13" + reply + b"\xff")
    assert st is not None and st.servo_id == 3 and st.error == 0 and st.params == bytes([0x10, 0x08])
    assert rest == b"\xff"


def test_sync_write_layout():
    pkt = ft.sync_write_packet(ft.REG_GOAL_POSITION, {1: ft.goal_block(2048), 2: ft.goal_block(100)})
    assert pkt[:2] == b"\xff\xff" and pkt[2] == ft.BROADCAST and pkt[4] == ft.SYNC_WRITE
    assert pkt[5] == ft.REG_GOAL_POSITION and pkt[6] == 6
    assert pkt[7] == 1 and pkt[8:10] == bytes([0x00, 0x08])


@pytest.mark.parametrize("target", [(0.45, 0.0, 0.40, math.pi / 2), (0.30, 0.15, 0.10, 2.4),
                                    (0.20, -0.20, 0.55, 1.2), (0.50, 0.05, 0.30, math.pi / 2)])
def test_ik_fk_roundtrip(target):
    q = ik(*target, G)
    x, y, z, p = fk(q, G)
    assert math.isclose(x, target[0], abs_tol=1e-6)
    assert math.isclose(y, target[1], abs_tol=1e-6)
    assert math.isclose(z, target[2], abs_tol=1e-6)
    assert math.isclose(p, target[3], abs_tol=1e-6)


def test_unreachable():
    with pytest.raises(Unreachable):
        ik(2.0, 0.0, 0.3, math.pi / 2, G)


def test_reach_linear_rail_60cm():
    """El reglamento pone los carriles lineales a 60 cm del piso. El deck está a 0.194 m:
    la punta tiene que llegar a z = 0.60 - 0.194 = 0.406 m del arm_base_link, a 0.35 m adelante."""
    q = ik(0.35, 0.0, 0.406, math.pi / 2, G)
    assert q is not None


def test_interpolate_endpoints():
    tr = interpolate([0, 0, 0, 0, 0], [1, 2, 3, 4, 5], 10)
    assert tr[-1] == [1, 2, 3, 4, 5] and len(tr) == 10


def test_static_torque_budget():
    """Brazo horizontal extendido con 200 g: el hombro (2 servos x 2.9 N·m x 2:1) debe tener margen."""
    q = [0, math.pi / 2, 0, 0, 0]
    t2, t3 = static_torques(q, G)
    assert t2 < 2 * 2.9 * 2.0 * 0.75, f"hombro {t2:.2f} N·m"
    assert t3 < 2.9 * 2.0 * 0.75, f"codo {t3:.2f} N·m"
