"""Ship input encoding, Shannyn's draft (docs/notes/ship_proposals.md §1, §3, §4): image motion from
the level's geometry, driving the T4/T5 motion detectors. **A draft until the ship design is logged
in docs/decisions.md**; the settings below are hers (agreed 2026-11-10), not tuned.

Every choice here is ours, not the fly's:
- **The eye** is at the ship's front face (x + 15), at its centre height, as for the cube (D41).
- **Viewing directions:** 37, every 5° of elevation from -90° (straight down) to +90° (straight
  up), both ends included (about the fly's interommatidial angle).
- **What each direction sees:** the nearest surface along its line of sight, among the visual cells
  (D41's 30 x 30 cells, clipped at the ground, D47) and the ship area's floor and ceiling. It counts
  if it is within 600 units ahead horizontally, so straight down and straight up always see the
  floor and ceiling. A cell the eye is inside is not seen (the eye can't see a surface it's in).
- **Image motion** of the point a direction sees, at height Δy above the eye and d ahead, with the
  ship moving at vx forward and vy up (game units per second):

      dφ/dt = (vx · Δy - vy · d) / (d² + Δy²)       (radians per second; positive = upward)

  The vy term is the ship's own climb or fall ("self-motion"); the vx term comes from flying
  forward ("flight"). `terms="self"` keeps the vy term only: Shannyn's control (§1d).
- **Pooling:** the plain mean over all 37 directions, in °/s. A direction that sees nothing within
  range counts as zero motion and stays in the mean.
- **Input:** downward pooled motion drives T4d + T5d, upward drives T4c + T5c, all neurons of each
  type on both eyes together, each at R_ship × f with f = min(1, |ω| / ω_full) (as R × f, D45).
  ω_full = 30°/s, the T4/T5 optimum (Maisak et al. 2013); the faster variant uses 90°/s. Only the
  group matching the sign is driven; the other gets 0 Hz. ω = 0 drives nothing.

Speeds: x moves X_PER_TICK per tick and y moves vy × TICK_DT_Y per tick, at 240 ticks per second.
"""

import bisect
import math
from dataclasses import dataclass

import numpy as np

from stereo_flyness.game.physics import TICK_DT_Y, TICKS_PER_SECOND, X_PER_TICK
from stereo_flyness.interface.encoding import EYE_AHEAD, obstacles

ELEVATIONS_DEG = np.arange(-90, 91, 5, dtype=float)  # 37 directions, -90 = straight down
VIEW_AHEAD = 600.0  # level units, horizontally
OMEGA_FULL_DEG = 30.0  # °/s: T4/T5's optimum (Maisak et al. 2013)
VX = X_PER_TICK * TICKS_PER_SECOND  # 311.58 units/s
VY_PER_UNIT = TICK_DT_Y * TICKS_PER_SECOND  # units/s per unit of the engine's vy (54)
TERMS = ("full", "self")
GROUPS = {"down": ("T4d", "T5d"), "up": ("T4c", "T5c")}
_EPS = 1e-9


@dataclass(frozen=True)
class Hit:
    """What one direction sees: the point's distance ahead (d) and height above the eye (dy)."""
    d: float
    dy: float
    what: str  # "cell", "floor" or "ceiling"


def look(eye_x: float, eye_y: float, floor: float, ceiling: float, cells, elevations_deg=ELEVATIONS_DEG,
         view_ahead: float = VIEW_AHEAD) -> list[Hit | None]:
    """The nearest surface along each direction, or None if nothing is within `view_ahead`.

    `cells` are `Obstacle`s (front x0, back x1, bottom, top), any order. Floor and ceiling are
    horizontal lines at their level y."""
    near = [c for c in cells if c.x1 > eye_x + _EPS and c.x0 < eye_x + view_ahead + _EPS
            and not (c.x0 < eye_x < c.x1 and c.bottom < eye_y < c.top)]
    out = []
    for phi in elevations_deg:
        best = None  # (horizontal distance, dy, what)
        if abs(phi) >= 90 - _EPS:  # straight up or down: x stays at the eye
            up = phi > 0
            best = (0.0, (ceiling if up else floor) - eye_y, "ceiling" if up else "floor")
            for c in near:
                if c.x0 <= eye_x <= c.x1:
                    face = c.bottom if up else c.top
                    if (face - eye_y > 0) == up and abs(face - eye_y) < abs(best[1]):
                        best = (0.0, face - eye_y, "cell")
        else:
            tan = math.tan(math.radians(phi))
            if tan > _EPS:
                h = (ceiling - eye_y) / tan
                best = (h, ceiling - eye_y, "ceiling")
            elif tan < -_EPS:
                h = (floor - eye_y) / tan
                best = (h, floor - eye_y, "floor")
            for c in near:
                lo, hi = c.x0 - eye_x, c.x1 - eye_x
                if abs(tan) <= _EPS:
                    if not (c.bottom <= eye_y <= c.top):
                        continue
                else:
                    a, b = (c.bottom - eye_y) / tan, (c.top - eye_y) / tan
                    lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
                lo = max(lo, 0.0)
                if lo <= hi + _EPS and (best is None or lo < best[0] - _EPS):
                    best = (lo, lo * tan, "cell")
        if best is not None and best[0] > view_ahead + _EPS:
            best = None
        out.append(None if best is None else Hit(best[0], best[1], best[2]))
    return out


def image_motion(hit: Hit, vy: float, vx: float = VX) -> tuple[float, float]:
    """(self-motion part, flight part) of the point's image motion, in °/s; positive is upward.
    `vy` in units per second."""
    r2 = hit.d ** 2 + hit.dy ** 2
    if r2 <= _EPS:
        return 0.0, 0.0
    return math.degrees(-vy * hit.d / r2), math.degrees(vx * hit.dy / r2)


@dataclass(frozen=True)
class Motion:
    """What the ship encoding saw and did on one tick (logged every tick, hard rule 10)."""
    omega_deg: float  # pooled image motion used for the input, °/s (positive = upward)
    omega_self_deg: float  # its self-motion part (pooled vy term)
    omega_flight_deg: float  # its forward-flight part (pooled vx term)
    seen: int  # directions that saw a surface within range
    f: float
    group: str | None  # "down", "up" or None
    rate_hz: float  # each driven neuron's rate, R_ship × f


class ShipEncoder:
    """Turns the ship's state into per-neuron rates for the "down" and "up" groups.

    `neurons` maps each type (T4c, T4d, T5c, T5d) and side to FlyWire IDs; `eyes` picks the sides
    (Shannyn: both, with the left–right asymmetry stated, docs/notes/ship_neuron_check.md).
    """

    def __init__(self, level, neurons: dict, rate_hz: float, omega_full_deg: float = OMEGA_FULL_DEG,
                 terms: str = "full", eyes=("right", "left")):
        if terms not in TERMS:
            raise ValueError(f"terms must be one of {TERMS}, not {terms!r}")
        if omega_full_deg <= 0:
            raise ValueError("omega_full_deg must be positive")
        self.rate_hz, self.omega_full_deg, self.terms, self.eyes = rate_hz, omega_full_deg, terms, tuple(eyes)
        self.cells = obstacles(level.boxes)
        self._x0 = [c.x0 for c in self.cells]
        self.ids = {g: [i for side in self.eyes for t in types for i in neurons[t][side]] for g, types in GROUPS.items()}

    def _near(self, eye_x: float):
        lo = bisect.bisect_left(self._x0, eye_x - 2 * EYE_AHEAD - _EPS)
        hi = bisect.bisect_right(self._x0, eye_x + VIEW_AHEAD + _EPS)
        return self.cells[lo:hi]

    def encode(self, player, bounds: tuple[float, float]) -> Motion:
        eye_x, eye_y = player.x + EYE_AHEAD, player.y
        hits = look(eye_x, eye_y, bounds[0], bounds[1], self._near(eye_x))
        vy = player.vy * VY_PER_UNIT
        parts = [image_motion(h, vy) for h in hits if h is not None]
        n = len(hits)
        s = sum(p[0] for p in parts) / n
        fl = sum(p[1] for p in parts) / n
        omega = s + fl if self.terms == "full" else s
        f = min(1.0, abs(omega) / self.omega_full_deg)
        group = None if omega == 0 else "down" if omega < 0 else "up"
        return Motion(omega, s, fl, len(parts), f, group, self.rate_hz * f if group else 0.0)

    def rates(self, m: Motion) -> dict[str, np.ndarray]:
        return {g: np.full(len(ids), m.rate_hz if g == m.group else 0.0) for g, ids in self.ids.items()}
