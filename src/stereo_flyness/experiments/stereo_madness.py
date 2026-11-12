"""Stereo Madness's report measures (Step 6; docs/notes/step6_proposal.md §4 and §6). Used by
scripts/stereo_madness_report.py. Nothing here reads Stereo Madness itself: the functions take any
level, and the tests use generated ones (hard rule 5).

- `where`: the section a run ended in (its mode and number), and the ship sections it reached and
  passed.
- `showcase`: the replay shown, picked by rule before the runs (§4): the run whose progress is
  closest to the median of its variant's runs, ties to the lowest seed.
- `spread`: completed count and progress median, quartiles and range ("k of 10, median X%").
"""

import numpy as np


def where(level, x: float, completed: bool) -> dict:
    """For a run that reached `x` (its death x, or the end): the section it ended in and the ship
    sections it reached (started) and passed (got past the end of)."""
    sections = level.sections()
    ship = [(i, s) for i, s in enumerate(sections) if s[0] == "ship"]
    ended = None
    if not completed:
        ended = next((i for i, s in enumerate(sections) if s[1] <= x < s[2]), len(sections) - 1)
    return {"ended_in": None if ended is None else f"{sections[ended][0]} section {ended + 1} of {len(sections)}",
            "ended_mode": None if ended is None else sections[ended][0],
            "ship_sections": len(ship),
            "ship_reached": sum(1 for _, s in ship if completed or x >= s[1]),
            "ship_passed": sum(1 for _, s in ship if completed or x >= s[2])}


def showcase(runs: list[dict]) -> dict:
    """The run with progress closest to the median progress of `runs`, ties to the lowest seed."""
    if not runs:
        raise ValueError("no runs")
    med = float(np.median([r["progress"] for r in runs]))
    return min(runs, key=lambda r: (abs(r["progress"] - med), r["seed"]))


def spread(runs: list[dict]) -> dict:
    p = np.array([r["progress"] for r in runs], float)
    q1, med, q3 = np.percentile(p, [25, 50, 75])
    return {"completed": int(sum(bool(r["completed"]) for r in runs)), "runs": len(runs), "median": float(med),
            "q1": float(q1), "q3": float(q3), "min": float(p.min()), "max": float(p.max())}
