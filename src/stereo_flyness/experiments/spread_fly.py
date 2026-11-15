"""The spread-aware ideal fly (iteration 2, fix 2's check; docs/notes/fix2_design.md).

Like the ideal fly (`scripts/ideal_fly.py`), it has no brain and presses on every tick after one
where the nearest looming object's θ has reached its threshold (one tick late, as D40/D42). But
instead of one fixed threshold, **each approach draws its own**, from the model fly's first-spike
distribution (normal, mean 37.1°, s.d. 7.3°: R2, closed loop). So it says how often a fly with this
spread clears each obstacle, which a fixed threshold can't.

**A new approach** starts whenever a different object becomes the nearest looming one (D45's
rule): the next column of the same object (touching it, with the same bottom and top) continues
the approach, and an object that stops looming for a while (e.g. mid-jump) and comes back keeps
its draw. Draws below `MIN_THRESHOLD` are raised to it.

A check of the encoding and the fly's spread, never a model result.
"""

import random
from dataclasses import dataclass

from stereo_flyness.game.engine import Game

FLY_MEAN_DEG, FLY_SD_DEG = 37.1, 7.3  # R2: closed-loop first Giant Fiber spike, without carry-over
MIN_THRESHOLD = 1.0
_EPS = 1e-6


@dataclass
class SpreadRun:
    completed: bool
    progress: float
    death: str | None
    death_x: float | None
    thresholds: list[tuple[float, float]]  # (front face x of the approach's object, its drawn threshold)


def _continues(new, old) -> bool:
    """D45: the next column of the same object (touching, same bottom and top) isn't a new approach."""
    return (old is not None and abs(new.x0 - old.x1) < _EPS
            and abs(new.bottom - old.bottom) < _EPS and abs(new.top - old.top) < _EPS)


def spread_fly(enc, level, seed: int, mean: float = FLY_MEAN_DEG, sd: float = FLY_SD_DEG) -> SpreadRun:
    """One run of the spread-aware ideal fly on `level`, its draws seeded by `seed`."""
    rng = random.Random(f"spread:{level.name}:{mean}:{sd}:{seed}")
    game, held = Game(level), False
    current, threshold, drawn, seen = None, None, [], {}
    while not game.over:
        game.tick(held)
        p = game.player
        loom = enc.encode(p)
        o = loom.obstacle
        if o is not None and o != current:
            if o in seen:  # the same object looming again: same approach, same draw
                threshold = seen[o]
            elif not _continues(o, current):
                threshold = max(MIN_THRESHOLD, rng.gauss(mean, sd))
                drawn.append((o.x0, threshold))
            seen[o] = threshold
            current = o
        held = p.mode == "cube" and o is not None and loom.theta_deg >= threshold
    d = game.death
    return SpreadRun(game.finished, game.progress, None if d is None else f"{d.kind} at x {d.x:.0f}",
                     None if d is None else d.x, drawn)
