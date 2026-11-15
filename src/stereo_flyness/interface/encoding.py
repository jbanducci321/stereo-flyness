"""Cube input encoding (D41): how big the nearest obstacle looks, as a growing LC4/LPLC2 patch.

Every choice here is ours, not the fly's (PROJECT_BRIEF §2):
- **The eye** is at the cube's front face (x + 15), at the cube's centre height.
- **What it sees is visual cells**, not hitboxes: each object fills the 30 x 30 cell around its
  hitbox centre, so a spike looks 30 units tall. Cells in the same column that touch
  vertically are merged into one object (a two-block wall is one object, 60 units tall).
  Cells are clipped at the ground (y = 0): the eye can't see below the floor, so a spike sunk
  into a pit looks only as tall as the part above it (D41 amendment, 2026-11-01).
- **Which objects loom:** by default only those on a collision course, i.e. overlapping the
  cube's current vertical extent (`mode="collision"`). So ceilings don't loom, and obstacles
  below the cube stop looming mid-jump. `mode="all"` is D43's "every object looms" comparison.
- **Iteration 2, fix 1 (`path="no_press"`, off by default; docs/notes/fix1_design.md, agreed
  2026-11-15):** while the cube stands on something raised, an object is also on course if the cube's
  **no-press path** (where it would go if the fly never pressed again, in the game's own physics)
  runs into it. Such an object, on course only because of the fall, is shown in the
  **landing-level view**: θ from an eye at the object's base level (its bottom + 15), as a cube
  down at that level would see it, at the true horizontal distance. (The base level, not the first
  surface the path lands on: they differ only after a step down, where the path first lands on the
  lower step and then falls into pits at floor level; the pits are shown from the floor.) Objects already on course
  keep their usual θ. In the air and on the floor nothing changes, so landing stays invisible.
  `view="eye"` is option (i), reported alongside (Shannyn's condition): the same objects come on
  course, but θ is true optics from the current eye (a pit below a platform peaks at 7-14°).
  Frames where either is used are flagged (`Loom.predicted`) and labelled in replays with
  `PREDICTED_LABELS[view]`.
- **Angular size** of the nearest looming object, from its real top and bottom:
  θ = atan((top - eye) / d) - atan((bottom - eye) / d), with d the gap to its front face.
- **Patch:** on each side, a fraction f = min(1, θ / θ_full) of the LC4 neurons and the same
  fraction of the LPLC2 neurons are driven at rate R, in the fixed patch order of probe P5
  (`loom_patches`). Everything else gets 0 Hz. Both eyes are driven equally.
- **Rate scaling** (`rate_scaling=True`, proposed 2026-10-31, being dry-run before D41 changes):
  each driven neuron fires at R x f instead of R, so a small distant object drives few neurons
  weakly and the total input grows steeply as it nears. θ_full stays the only calibrated number.

Only cube mode is encoded; ship mode is a Step 5 decision, so in ship mode nothing looms.
"""

import bisect
import math
from dataclasses import dataclass, replace

import numpy as np

from stereo_flyness.game.engine import Game, Snapshot
from stereo_flyness.game.physics import HALF_PLAYER, PORTAL_WIDTH

CELL = 30.0  # a grid cell, in level units
HALF = CELL / 2
EYE_AHEAD = 15.0  # the cube's front face, from its centre
GROUND = 0.0  # level y of the floor; visual cells are clipped here
SIDES = ("right", "left")
TYPES = ("LC4", "LPLC2")
_EPS = 1e-6
PATHS = ("current", "no_press")
VIEWS = ("landing", "eye")  # fix 1's (ii) landing-level view and (i) true optics
PREDICTED_LABELS = {  # replay text for frames where Loom.predicted is set (hard rule 10)
    "landing": "θ shown from landing level, our construction",  # Shannyn's wording, 2026-11-15
    "eye": "on course via our predicted fall (our construction); θ from the eye (true optics)",  # Shannyn's
}
MAX_PATH_TICKS = 2400  # 10 s of prediction at most; paths normally end far sooner (floor, death)


@dataclass(frozen=True)
class Obstacle:
    """A merged stack of visual cells: front face x0, back face x1, bottom and top."""
    x0: float
    x1: float
    bottom: float
    top: float


def obstacles(boxes) -> list[Obstacle]:
    """Visual cells of a level's boxes, clipped at the ground (y = 0), with cells in the same
    column that touch vertically merged. Sorted by front face, then bottom."""
    columns = {}
    for b in boxes:
        cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
        if cy + HALF <= GROUND + _EPS:
            continue  # entirely below the floor: never seen
        columns.setdefault(round(cx - HALF, 6), []).append((max(cy - HALF, GROUND), cy + HALF))
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
    rate_hz: float  # each driven neuron's rate: R, or R x f with rate scaling
    predicted: bool = False  # fix 1: on course only via the no-press path, shown in the landing-level view


@dataclass(frozen=True)
class NoPressPath:
    """Where the cube goes if the fly never presses again, from a state on a raised surface.

    `states` are the predicted player states, tick by tick, up to where the path ends: on the
    floor (`floor_x`, after which the cube walks along y = 0 for good), at a death, at the level's
    end, or after MAX_PATH_TICKS.
    """
    states: tuple
    floor_x: float | None

    def hits(self, o: Obstacle) -> bool:
        """Does the predicted cube overlap the object's visual cell anywhere along the path?"""
        for p in self.states:
            if p.x + HALF_PLAYER <= o.x0 + _EPS:
                continue
            if p.x - HALF_PLAYER >= o.x1 - _EPS:
                continue
            if o.bottom < p.top - _EPS and o.top > p.bottom + _EPS:
                return True
        if self.floor_x is not None and o.x1 > self.floor_x - HALF_PLAYER + _EPS:
            return o.bottom < GROUND + 2 * HALF_PLAYER - _EPS  # the floor stretch: cube at 0-30
        return False


class CubeEncoder:
    """Turns the game state into per-neuron Poisson rates for one "loom" input group (D41).

    `patches` is `loom_patches(...)`: per side, LC4 and LPLC2 IDs in patch order. `ids` is the
    input group's fixed neuron order (right LC4, right LPLC2, left LC4, left LPLC2, each in
    patch order); `rates(loom)` gives the matching rate vector.
    """

    def __init__(self, level, patches, theta_full_deg: float, rate_hz: float, mode: str = "collision",
                 rate_scaling: bool = False, path: str = "current", view: str = "landing"):
        if mode not in ("collision", "all"):
            raise ValueError(f"mode must be 'collision' or 'all', not {mode!r}")
        if path not in PATHS:
            raise ValueError(f"path must be one of {PATHS}, not {path!r}")
        if path == "no_press" and mode != "collision":
            raise ValueError("path='no_press' only applies to the collision-course mode")
        if view not in VIEWS:
            raise ValueError(f"view must be one of {VIEWS}, not {view!r}")
        self.path, self.view = path, view
        self._level, self._game, self._path_cache = level, None, None
        if theta_full_deg <= 0:
            raise ValueError("theta_full_deg must be positive")
        self.mode, self.theta_full_deg, self.rate_hz = mode, theta_full_deg, rate_hz
        self.rate_scaling = rate_scaling
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
        o, theta, _ = self._nearest(player)
        return o, theta

    def _nearest(self, player) -> tuple[Obstacle | None, float, bool]:
        """As `nearest`, plus whether the object is on course only via the no-press path."""
        if player.mode != "cube":
            return None, 0.0, False
        path = self.no_press_path(player) if self._raised(player) else None
        eye_x = player.x + EYE_AHEAD
        best, best_theta, best_gap, best_pred = None, 0.0, math.inf, False
        for o in self.obstacles[bisect.bisect_left(self._x0, eye_x - _EPS):]:
            gap = o.x0 - eye_x
            if gap > best_gap + _EPS:
                break  # everything further on is further away
            eye_y, predicted = player.y, False
            if self.mode == "collision" and not (o.bottom < player.top - _EPS and o.top > player.bottom + _EPS):
                if path is None or not path.hits(o):
                    continue
                eye_y = o.bottom + HALF if self.view == "landing" else player.y  # (ii) or (i)
                predicted = True
            theta = angular_size(gap, o.bottom, o.top, eye_y)
            if best is None or gap < best_gap - _EPS or theta > best_theta:
                best, best_theta, best_gap, best_pred = o, theta, gap, predicted
        return best, best_theta, best_pred

    def _raised(self, player) -> bool:
        """Fix 1 applies only while the cube stands on something above the floor."""
        return (self.path == "no_press" and player.mode == "cube" and player.on_ground
                and player.bottom > GROUND + _EPS)

    def no_press_path(self, player) -> NoPressPath:
        """The cube's path if the fly never presses again, simulated in the game's own engine.

        While the fly doesn't press, the cube follows the last prediction exactly, so it's reused
        from the matching state on. (The engine's stair-snap memory isn't carried over; it moves x
        by at most 1 unit at a landing, and only affects where the path lands on stair steps.)
        """
        cache = self._path_cache
        if cache is not None:
            for i, s in enumerate(cache.states[:2]):
                if (s.x, s.y, s.vy, s.on_ground, s.mode) == (player.x, player.y, player.vy, player.on_ground, player.mode):
                    path = NoPressPath(cache.states[i:], cache.floor_x)
                    self._path_cache = path
                    return path
        if self._game is None:
            self._game = Game(self._level)
        game, portals = self._game, self._level.portals
        next_portal = sum(1 for q in portals if q.x + PORTAL_WIDTH / 2 < player.x - HALF_PLAYER)
        game.restore(Snapshot(replace(player), 0, None, False, (), None, 0.0, next_portal, None))
        states, floor_x = [replace(player)], None
        while not game.over and len(states) < MAX_PATH_TICKS:
            game.tick(False)
            p = game.player
            if p.mode != "cube":
                break
            if p.on_ground and p.bottom <= GROUND + _EPS:
                floor_x = p.x
                break
            states.append(replace(p))
        path = NoPressPath(tuple(states), floor_x)
        self._path_cache = path
        return path

    def encode(self, player) -> Loom:
        o, theta, predicted = self._nearest(player)
        theta_deg = math.degrees(theta)
        f = min(1.0, theta_deg / self.theta_full_deg)
        driven = {key: int(round(f * len(self.patches[key]))) for key in self.order}
        rate = self.rate_hz * f if self.rate_scaling else self.rate_hz
        return Loom(theta_deg, None if o is None else o.x0 - (player.x + EYE_AHEAD), o, f, driven, rate, predicted)

    def rates(self, loom: Loom) -> np.ndarray:
        """Per-neuron rates (Hz) in `ids` order: the loom's rate for the first `driven` of each
        patch, else 0."""
        out = np.zeros(len(self.ids))
        for key, n in loom.driven.items():
            s = self._slices[key]
            out[s.start:s.start + n] = loom.rate_hz
        return out
