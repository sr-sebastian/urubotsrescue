"""Transformaciones rígidas mínimas: T = ((x, y, z), (w, x, y, z)). Python puro."""

from __future__ import annotations

import math


def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw)


def qconj(q):
    return (q[0], -q[1], -q[2], -q[3])


def qnorm(q):
    n = math.sqrt(sum(v * v for v in q)) or 1.0
    return tuple(v / n for v in q)


def rotate(q, v):
    w = qmul(qmul(q, (0.0, *v)), qconj(q))
    return w[1], w[2], w[3]


def from_msg(t, q):
    return (tuple(t), qnorm(tuple(q)))


def compose(a, b):
    """a ∘ b: primero b, después a (T_ac = T_ab · T_bc)."""
    ta, qa = a
    tb, qb = b
    r = rotate(qa, tb)
    return ((ta[0] + r[0], ta[1] + r[1], ta[2] + r[2]), qnorm(qmul(qa, qb)))


def invert(a):
    t, q = a
    qi = qconj(q)
    r = rotate(qi, t)
    return ((-r[0], -r[1], -r[2]), qi)
