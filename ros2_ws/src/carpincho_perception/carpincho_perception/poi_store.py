"""Confirmación y deduplicación de puntos de interés (Python puro).

Una detección se confirma cuando se vio `min_hits` veces dentro de `radius` metros (filtra falsos
positivos de un solo cuadro). Luego se fija la posición como el promedio de esas observaciones.
Un mismo (tipo, nombre) solo se reporta una vez: el reglamento descarta repetidos y penaliza
detecciones con error grande.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Candidate:
    type: str
    name: str
    xs: list = field(default_factory=list)
    ys: list = field(default_factory=list)
    zs: list = field(default_factory=list)
    confs: list = field(default_factory=list)
    first_t: float = 0.0
    mode: str = "T"

    def mean(self):
        n = len(self.xs)
        return sum(self.xs) / n, sum(self.ys) / n, sum(self.zs) / n


@dataclass
class Confirmed:
    id: int
    type: str
    name: str
    x: float
    y: float
    z: float
    confidence: float
    t: float
    mode: str


class PoiStore:
    def __init__(self, min_hits: int = 3, radius: float = 0.5, max_candidates: int = 200):
        self.min_hits = min_hits
        self.radius = radius
        self.max_candidates = max_candidates
        self.candidates: list[Candidate] = []
        self.confirmed: list[Confirmed] = []
        self._next_id = 1

    def add(self, type_: str, name: str, x: float, y: float, z: float, conf: float, t: float,
            mode: str = "T") -> Confirmed | None:
        """Agrega una observación. Devuelve el POI si en esta llamada quedó confirmado."""
        if any(c.type == type_ and c.name == name for c in self.confirmed):
            return None
        for c in self.candidates:
            if c.type == type_ and c.name == name:
                mx, my, mz = c.mean()
                if math.dist((mx, my, mz), (x, y, z)) <= self.radius:
                    c.xs.append(x)
                    c.ys.append(y)
                    c.zs.append(z)
                    c.confs.append(conf)
                    if mode == "T":
                        c.mode = "T"      # si alguna observación fue teleoperada, se reporta T
                    if len(c.xs) >= self.min_hits:
                        return self._confirm(c)
                    return None
        c = Candidate(type_, name, [x], [y], [z], [conf], t, mode)
        self.candidates.append(c)
        if len(self.candidates) > self.max_candidates:
            self.candidates.pop(0)
        if self.min_hits <= 1:
            return self._confirm(c)
        return None

    def _confirm(self, c: Candidate) -> Confirmed:
        x, y, z = c.mean()
        p = Confirmed(self._next_id, c.type, c.name, x, y, z, max(c.confs), c.first_t, c.mode)
        self._next_id += 1
        self.confirmed.append(p)
        self.candidates = [k for k in self.candidates if not (k.type == c.type and k.name == c.name)]
        return p

    def clear(self) -> None:
        self.candidates.clear()
        self.confirmed.clear()
        self._next_id = 1
