import math

from carpincho_teleop.mapping import TeleopMapper

REST = [0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0]   # gatillos sueltos = +1


def axes(**kw):
    a = list(REST)
    idx = dict(lx=0, ly=1, lt=2, rx=3, ry=4, rt=5, dx=6, dy=7)
    for k, v in kw.items():
        a[idx[k]] = v
    return a


def buttons(*names):
    b = [0] * 11
    idx = dict(a=0, b=1, x=2, y=3, lb=4, rb=5, back=6, start=7, guide=8)
    for n in names:
        b[idx[n]] = 1
    return b


def test_deadman_required():
    m = TeleopMapper()
    assert m.update(axes(ly=1.0), buttons()).v == 0.0
    assert m.update(axes(ly=1.0), buttons("lb")).v > 0.3


def test_speed_levels_and_turn_sign():
    m = TeleopMapper()
    m.update(axes(dy=1.0), buttons())          # subir nivel
    o = m.update(axes(ly=1.0, rx=1.0), buttons("lb"))
    assert math.isclose(o.v, 0.70, rel_tol=1e-6)
    assert o.w < 0                             # stick a la derecha = girar a la derecha (w negativo)


def test_flipper_preset_edge_only():
    m = TeleopMapper()
    o1 = m.update(axes(), buttons("lb", "y"))
    o2 = m.update(axes(), buttons("lb", "y"))
    assert math.isclose(o1.flipper_pos, math.radians(60)) and o2.flipper_pos is None


def test_arm_mode_jog_and_poses():
    m = TeleopMapper()
    m.update(axes(), buttons("back"))
    assert m.mode == "arm"
    m.update(axes(), buttons())
    o = m.update(axes(ly=1.0, rt=-1.0), buttons("lb", "y"))
    assert o.arm_jog[0] > 0 and o.named_pose == "stow" and o.gripper > 0


def test_start_toggles_enable_once():
    m = TeleopMapper()
    assert m.update(axes(), buttons("start")).toggle_enable
    assert not m.update(axes(), buttons("start")).toggle_enable
