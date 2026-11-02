"""Step 3: how the winning rate is picked from the grid (docs/notes/step3_proposal.md, section 4).

Fixed before the runs: the best mean progress wins; any rate within `margin` of the best counts as
tied, and among tied rates the one closest to the untuned default (on a log scale) wins, i.e. the
one that moves the fly least from its calibrated state.
"""

import math


def pick_rate(scores: dict[float, float], default: float, margin: float) -> tuple[float, list[float]]:
    """(winning rate, all tied rates in ascending order) from {rate: mean progress}."""
    if not scores:
        raise ValueError("no scores to pick from")
    best = max(scores.values())
    tied = sorted(r for r, s in scores.items() if s >= best - margin - 1e-12)
    winner = min(tied, key=lambda r: (abs(math.log(r / default)), r))
    return winner, tied
