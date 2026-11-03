"""Step 3: how the winning rate is picked from the grid (docs/notes/step3_proposal.md, with
Shannyn's answers of 2026-11-02).

Fixed before the runs:
- **Score:** mean progress over the training levels; the best wins.
- **Tie margin, measured:** max(1 point, the seed 0 vs seed 1 difference in mean progress at the
  default rate), so a difference one change of seed can make by itself is a tie.
- **Tie-break:** among tied rates, the one whose open-loop first Giant Fiber spike θ is closest to
  the fly's 39°. A rate where fewer than half the calibration trials fire ranks after every rate
  where at least half do; among those, more trials fired ranks higher. Anything still tied goes
  to the rate closest to the default on a log scale.
"""

import math
from dataclasses import dataclass

TARGET_DEG = 39.0


@dataclass(frozen=True)
class OpenLoop:
    """Where a rate makes the Giant Fiber first fire on the calibration loom."""
    mean_theta: float | None  # over the trials that fired
    fired: int
    trials: int


def tie_margin(seed0: float, seed1: float, floor: float = 0.01) -> float:
    """max(floor, |mean progress at seed 0 - at seed 1|), both at the default rate."""
    return max(floor, abs(seed0 - seed1))


def tie_rank(rate: float, open_loop: dict[float, OpenLoop], default: float) -> tuple:
    """Sort key among tied rates: lower is better."""
    o = open_loop[rate]
    log_distance = abs(math.log(rate / default))
    if 2 * o.fired >= o.trials and o.mean_theta is not None:
        return 0, abs(o.mean_theta - TARGET_DEG), log_distance, rate
    return 1, -o.fired, log_distance, rate


def pick_rate(scores: dict[float, float], open_loop: dict[float, OpenLoop], default: float,
              margin: float) -> tuple[float, list[float]]:
    """(winning rate, all tied rates in ascending order) from {rate: mean progress}."""
    if not scores:
        raise ValueError("no scores to pick from")
    best = max(scores.values())
    tied = sorted(r for r, s in scores.items() if s >= best - margin - 1e-12)
    if len(tied) > 1 and any(r not in open_loop for r in tied):
        raise ValueError("a tie needs the open-loop check at every tied rate")
    winner = tied[0] if len(tied) == 1 else min(tied, key=lambda r: tie_rank(r, open_loop, default))
    return winner, tied
