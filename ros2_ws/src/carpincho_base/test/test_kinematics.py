import math

from carpincho_base.kinematics import (Odometry, TrackGeometry, pitch_from_quat, tracks_to_twist,
                                       twist_to_tracks, yaw_from_quat)

G = TrackGeometry(0.275, 1.6)


def test_roundtrip():
    vl, vr = twist_to_tracks(0.3, 0.5, G, 10.0)
    v, w = tracks_to_twist(vl, vr, G)
    assert math.isclose(v, 0.3) and math.isclose(w, 0.5)


def test_saturation_keeps_curvature():
    vl, vr = twist_to_tracks(1.0, 2.0, G, 0.7)
    assert max(abs(vl), abs(vr)) <= 0.7 + 1e-9
    v, w = tracks_to_twist(vl, vr, G)
    assert math.isclose(w / v, 2.0, rel_tol=1e-6)


def test_odometry_straight_and_turn():
    o = Odometry()
    for _ in range(100):
        o.update(0.01, 0.01, G)
    assert math.isclose(o.x, 1.0, abs_tol=1e-9) and abs(o.y) < 1e-9
    o2 = Odometry()
    arc = math.pi / 2 * G.effective_separation / 2
    for _ in range(100):
        o2.update(-arc / 100, arc / 100, G)
    assert math.isclose(o2.yaw, math.pi / 2, abs_tol=1e-6)


def test_quat_helpers():
    yaw = 0.7
    w, z = math.cos(yaw / 2), math.sin(yaw / 2)
    assert math.isclose(yaw_from_quat(w, 0, 0, z), yaw)
    pitch = 0.3
    assert math.isclose(pitch_from_quat(math.cos(pitch / 2), 0, math.sin(pitch / 2), 0), pitch)


def test_se3_relay_identity_at_start():
    from carpincho_base.se3 import compose, invert
    s = math.sqrt(0.5)
    T_bl = ((-0.17, 0.0, 0.43), (s, 0.0, 0.0, s))        # lidar montado girado 90°
    ident = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0))
    T = compose(compose(T_bl, ident), invert(T_bl))
    assert all(abs(v) < 1e-9 for v in T[0])
    assert abs(abs(T[1][0]) - 1.0) < 1e-9


def test_se3_relay_forward_motion():
    from carpincho_base.se3 import compose, invert
    T_bl = ((-0.17, 0.0, 0.43), (1.0, 0.0, 0.0, 0.0))
    moved = ((1.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0))      # el LiDAR avanzó 1 m
    (x, y, z), _ = compose(compose(T_bl, moved), invert(T_bl))
    assert abs(x - 1.0) < 1e-9 and abs(y) < 1e-9 and abs(z) < 1e-9
