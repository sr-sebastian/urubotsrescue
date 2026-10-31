import math

from carpincho_autonomy.lane_logic import AutoFlipper, LaneParams, LaneTraverse, sector_distance, wrap


def sim(lt, steps=4000, dt=0.05, y0=0.15, yaw0=0.1, width=1.2):
    """Robot unicycle en un pasillo recto de `width` m (paredes en y = ±width/2)."""
    x, y, yaw, dist, t = 0.0, y0, yaw0, 0.0, 0.0
    lt.start(0.0, 0.0, 0.0)
    for _ in range(steps):
        left = width / 2 - y
        right = width / 2 + y
        # en el sentido de vuelta las paredes se intercambian
        if abs(wrap(yaw - math.pi)) < math.pi / 2:
            left, right = right, left
        v, w = lt.step(t, yaw, dist, 0.0, left, right, None)
        x += v * math.cos(yaw) * dt
        y += v * math.sin(yaw) * dt
        yaw = wrap(yaw + w * dt)
        dist += abs(v) * dt
        t += dt
        if lt.s.state in ("DONE", "ABORT"):
            break
    return x, y, yaw


def test_centers_and_completes_round_trip():
    lt = LaneTraverse(LaneParams(lane_length=3.0, traverses=2))
    x, y, _ = sim(lt)
    assert lt.s.state == "DONE" and lt.s.traverses_done == 2
    assert abs(x) < 0.4 and abs(y) < 0.1          # volvió cerca del inicio y centrado


def test_stuck_triggers_recovery_then_abort():
    lt = LaneTraverse(LaneParams(stuck_time=1.0, max_recoveries=1))
    lt.start(0.0, 0.0, 0.0)
    t = 0.0
    for _ in range(400):
        lt.step(t, 0.0, 0.0, 0.0, 0.6, 0.6, None)   # dist nunca aumenta
        t += 0.05
    assert lt.s.state == "ABORT"


def test_sector_distance():
    n = 360
    ranges = [2.0] * n
    for i in range(80, 100):
        ranges[i] = 0.5      # obstáculo a ~90° (izquierda)
    d = sector_distance(ranges, -math.pi, 2 * math.pi / n, math.radians(-100), math.radians(-80))
    assert d == 0.5 or d == 2.0
    d = sector_distance(ranges, 0.0, 2 * math.pi / n, math.radians(80), math.radians(100))
    assert d == 0.5


def test_auto_flipper_sequence():
    af = AutoFlipper()
    assert af.update(0.0, 0.0) == af.flat
    assert af.update(math.radians(15), 0.0) == af.climb
    assert af.update(math.radians(10), -math.radians(30)) == af.crest
    assert af.update(math.radians(-12), 0.0) == af.descend
    assert af.update(0.0, 0.0) == af.flat
