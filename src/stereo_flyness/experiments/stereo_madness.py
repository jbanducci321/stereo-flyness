"""Stereo Madness's report measures (Step 6; docs/notes/step6_proposal.md §4 and §6). Used by
scripts/stereo_madness_report.py. Nothing here reads Stereo Madness itself: the functions take any
level, and the tests use generated ones (hard rule 5).

- `where`: the section a run ended in (its mode and number), and the ship sections it reached and
  passed.
- `showcase`: the replay shown, picked by rule before the runs (§4): the run whose progress is
  closest to the median of its variant's runs, ties to the lowest seed.
- `spread`: completed count and progress median, quartiles and range ("k of 10, median X%").
- `killing_box` and `death_side`: the box that killed a run, and whether it was above or below the
  player at death (Shannyn's prediction 5, docs/notes/step6_predictions.md).
- `cube_match`: whether two runs' game states (x, y, vy) are identical on every tick before the
  first ship tick (her prediction 3: corrected signs play exactly like the record in cube sections).
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


def killing_box(level, death):
    """The box that killed the player: the nearest box of the death's kind that the player's
    30 x 30 hitbox overlaps at the death point. None if there's no death or no match."""
    if death is None:
        return None
    hits = [b for b in level.boxes if b.kind == death.kind and not (
        death.x + 15 < b.x0 or b.x1 < death.x - 15 or death.y + 15 < b.y0 or b.y1 < death.y - 15)]
    if not hits:
        return None
    return min(hits, key=lambda b: abs((b.x0 + b.x1) / 2 - death.x) + abs((b.y0 + b.y1) / 2 - death.y))


def death_side(level, death) -> str | None:
    """"above" if the killing box's centre is above the player's centre at death, else "below"."""
    b = killing_box(level, death)
    if b is None:
        return None
    return "above" if (b.y0 + b.y1) / 2 > death.y else "below"


STATE = ("x", "y", "vy")


def cube_match(a, b) -> dict:
    """Compare two runs' tick logs (DataFrames with mode, x, y, vy) on every tick before each run's
    first ship tick (or to its end, if it never reaches one). Identical means: the same number of
    such ticks, and exactly equal x, y and vy on each. `first_diff` is the first tick index where
    they differ (None if identical); `ticks` is how many ticks were compared."""
    def cut(t):
        ship = (t["mode"] == "ship").to_numpy()
        return int(ship.argmax()) if ship.any() else len(t)

    na, nb = cut(a), cut(b)
    n = min(na, nb)
    same = np.all([a[c].to_numpy()[:n] == b[c].to_numpy()[:n] for c in STATE], axis=0)
    if not same.all():
        return {"identical": False, "ticks": n, "first_diff": int((~same).argmax())}
    if na != nb:
        return {"identical": False, "ticks": n, "first_diff": n}
    return {"identical": True, "ticks": n, "first_diff": None}
