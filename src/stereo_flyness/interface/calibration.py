"""Calibrating θ_full to the fly's escape threshold (D43).

The target is the angular size at which a real fly's Giant Fiber-driven takeoff happens: θ ≈ 39°
(mean, s.d. ≈ 14°; von Reyn et al. 2014 Fig. 5b, short mode, r/v = 40 ms). The model is shown
a game-like loom, open loop: the cube runs at game speed straight at a single 30-unit object
and never jumps, so θ grows exactly as in the game (D41, r/v = 48 ms). For each θ_full we
record θ at the Giant Fiber's first spike. The calibrated θ_full is where the mean first-spike θ
crosses the target. Game performance plays no part.

One choice here is ours and not fixed by D43: how far away the object starts (`start_gap`).
The model integrates sustained input, so a longer approach can fire the Giant Fiber earlier.
"""

import math

import numpy as np

from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox
from stereo_flyness.game.physics import HALF_PLAYER

TARGET_DEG = 39.0
CELL = 30.0


def approach_level(start_gap: float = 600.0, after: float = 60.0) -> Level:
    """A flat level with one spike whose front face is `start_gap` units ahead of the eye at the
    start (the cube starts at x = 0, its eye at x = 15)."""
    x0 = HALF_PLAYER + start_gap
    return Level(f"approach_{start_gap:g}", "calibration (D43)", x0 + CELL + after,
                 [Box("spike", *hitbox("spike", x0 + CELL / 2, CELL / 2))])


def first_spike_theta(brain) -> float | None:
    """θ (degrees) the brain was seeing in the frame of its first Giant Fiber spike, or None."""
    gf = brain["spikes_GF_R"] + brain["spikes_GF_L"]
    hits = np.flatnonzero(gf.to_numpy() > 0)
    return float(brain["theta_deg"].iloc[hits[0]]) if len(hits) else None


def crossing(theta_full: list[float], mean_theta: list[float], target: float = TARGET_DEG) -> float | None:
    """The θ_full at which the mean first-spike θ crosses `target`, interpolated linearly in
    log θ_full between the two bracketing points. None if no pair brackets the target."""
    pts = sorted((t, m) for t, m in zip(theta_full, mean_theta) if m is not None and not math.isnan(m))
    for (t0, m0), (t1, m1) in zip(pts, pts[1:]):
        if (m0 - target) * (m1 - target) <= 0 and m0 != m1:
            w = (target - m0) / (m1 - m0)
            return math.exp(math.log(t0) + w * (math.log(t1) - math.log(t0)))
    return None
