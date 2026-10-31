"""Cube input encoding (D41): how big the nearest obstacle looks, as a growing LC4/LPLC2 patch.

Every choice here is ours, not the fly's (PROJECT_BRIEF §2):
- **The eye** is at the cube's front face (x + 15), at the cube's centre height.
- **What it sees is visual cells**, not hitboxes: each object fills the 30 x 30 cell around its
  hitbox centre, so a spike looks 30 units tall. Cells in the same column that touch
  vertically are merged into one object (a two-block wall is one object, 60 units tall).
- **Which objects loom:** by default only those on a collision course, i.e. overlapping the
  cube's current vertical extent (`mode="collision"`). So ceilings don't loom, and obstacles
  below the cube stop looming mid-jump. `mode="all"` is D43's "every object looms" comparison.
- **Angular size** of the nearest looming object, from its real top and bottom:
  θ = atan((top - eye) / d) - atan((bottom - eye) / d), with d the gap to its front face.
- **Patch:** on each side, a fraction f = min(1, θ / θ_full) of the LC4 neurons and the same
  fraction of the LPLC2 neurons are driven at rate R, in the fixed patch order of probe P5
  (`loom_patches`). Everything else gets 0 Hz. Both eyes are driven equally.

Only cube mode is encoded; ship mode is a Step 5 decision, so in ship mode nothing looms.
"""

import bisect
import math
from dataclasses import dataclass

import numpy as np

CELL = 30.0  # a grid cell, in level units
HALF = CELL / 2
EYE_AHEAD = 15.0  # the cube's front face, from its centre
SIDES = ("right", "left")
TYPES = ("LC4", "LPLC2")
_EPS = 1e-6


@dataclass(frozen=True)
class Obstacle:
    """A merged stack of visual cells: front face x0, back face x1, bottom and top."""
    x0: float
    x1: float
    bottom: float
    top: float


def obstacles(boxes) -> list[Obstacle]:
    """Visual cells of a level's boxes, with cells in the same column that touch vertically
    merged. Sorted by front face, then bottom."""
    columns = {}
    for b in boxes:
        cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
        columns.setdefault(round(cx - HALF, 6), []).append((cy - HALF, cy + HALF))
    out = []
    for x0, cells in columns.items():
        cells.sort()
        lo, hi = cells[0]
        for b, t in cells[1:]:
            if b <= hi + _EPS:  # touching or overlapping: same object
                hi = max(hi, t)
            else:
                out.append(Obstacle(x0, x0 + CELL, lo, hi))
                lo, hi = b, t
        out.append(Obstacle(x0, x0 + CELL, lo, hi))
    return sorted(out, key=lambda o: (o.x0, o.bottom))


def angular_size(gap: float, bottom: float, top: float, eye_y: float) -> float:
    """Angle (radians) an object's front face subtends at the eye, from its top and bottom."""
    d = max(gap, _EPS)
    return math.atan((top - eye_y) / d) - math.atan((bottom - eye_y) / d)


@dataclass(frozen=True)
class Loom:
    """What the encoding saw and did on one tick (logged every tick, hard rule 10)."""
    theta_deg: float  # angular size of the nearest looming object (0 if none)
    gap: float | None  # distance from the eye to its front face
    obstacle: Obstacle | None
    f: float  # fraction of each population driven
    driven: dict  # {(side, type): number of neurons driven, from the start of the patch order}
    rate_hz: float


class CubeEncoder:
    """Turns the game state into per-neuron Poisson rates for one "loom" input group (D41).

    `patches` is `loom_patches(...)`: per side, LC4 and LPLC2 IDs in patch order. `ids` is the
    input group's fixed neuron order (right LC4, right LPLC2, left LC4, left LPLC2, each in
    patch order); `rates(loom)` gives the matching rate vector.
    """

    def __init__(self, level, patches, theta_full_deg: float, rate_hz: float, mode: str = "collision"):
        if mode not in ("collision", "all"):
            raise ValueError(f"mode must be 'collision' or 'all', not {mode!r}")
        if theta_full_deg <= 0:
            raise ValueError("theta_full_deg must be positive")
        self.mode, self.theta_full_deg, self.rate_hz = mode, theta_full_deg, rate_hz
        self.obstacles = obstacles(level.boxes)
        self._x0 = [o.x0 for o in self.obstacles]
        self.order = [(s, t) for s in SIDES for t in TYPES]
        self.patches = {(s, t): list(patches[s][t]) for s, t in self.order}
        self.ids = [i for key in self.order for i in self.patches[key]]
        self._slices, start = {}, 0
        for key in self.order:
            self._slices[key] = slice(start, start + len(self.patches[key]))
            start += len(self.patches[key])

    def nearest(self, player) -> tuple[Obstacle | None, float]:
        """The nearest looming obstacle ahead of the eye and its angular size (radians)."""
        if player.mode != "cube":
            return None, 0.0
        eye_x = player.x + EYE_AHEAD
        best, best_theta, best_gap = None, 0.0, math.inf
        for o in self.obstacles[bisect.bisect_left(self._x0, eye_x - _EPS):]:
            gap = o.x0 - eye_x
            if gap > best_gap + _EPS:
                break  # everything further on is further away
            if self.mode == "collision" and not (o.bottom < player.top - _EPS and o.top > player.bottom + _EPS):
                continue
            theta = angular_size(gap, o.bottom, o.top, player.y)
            if best is None or gap < best_gap - _EPS or theta > best_theta:
                best, best_theta, best_gap = o, theta, gap
        return best, best_theta

    def encode(self, player) -> Loom:
        o, theta = self.nearest(player)
        theta_deg = math.degrees(theta)
        f = min(1.0, theta_deg / self.theta_full_deg)
        driven = {key: int(round(f * len(self.patches[key]))) for key in self.order}
        return Loom(theta_deg, None if o is None else o.x0 - (player.x + EYE_AHEAD), o, f, driven, self.rate_hz)

    def rates(self, loom: Loom) -> np.ndarray:
        """Per-neuron rates (Hz) in `ids` order: R for the first `driven` of each patch, else 0."""
        out = np.zeros(len(self.ids))
        for key, n in loom.driven.items():
            s = self._slices[key]
            out[s.start:s.start + n] = loom.rate_hz
        return out
