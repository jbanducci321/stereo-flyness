"""Stereo Madness on new seeds (D60; docs/notes/sm_newseeds_plan.md): the report's measures.

Pure functions; `scripts/sm_newseeds_report.py` loads and checks the runs. Like
`experiments/stereo_madness.py`, nothing here reads Stereo Madness itself: the tests use generated levels.

- `strip_at` / `strip_end`: the hazard strip (pits or spikes, a cell or less apart) at a given x, and its far edge.
- `got_past`: whether a run is alive with its whole body past an edge (or completed the level).
- `milestones`: how many runs reach each of P8's milestones.
- `prediction8`: the measures for Shannyn's fix 1 prediction 8, by D60's rule.
"""

from stereo_flyness.game.physics import HALF_PLAYER

HAZARDS = ("pit", "spike")


def strip_at(level, x: float, gap: float = 30.0) -> tuple[float, float] | None:
    """The (x0, x1) of the strip of hazards that contains x, hazards chained while the next one starts
    at most `gap` after the last ends. None if no hazard is within a cube's half-width of x."""
    boxes = sorted((b for b in level.boxes if b.kind in HAZARDS), key=lambda b: b.x0)
    strips, cur = [], []
    for b in boxes:
        if cur and b.x0 - max(c.x1 for c in cur) > gap:
            strips.append(cur)
            cur = []
        cur.append(b)
    if cur:
        strips.append(cur)
    for s in strips:
        x0, x1 = min(b.x0 for b in s), max(b.x1 for b in s)
        if x0 - HALF_PLAYER <= x <= x1 + HALF_PLAYER:
            return x0, x1
    return None


def strip_end(level, x: float, gap: float = 30.0) -> float | None:
    """The far edge of the hazard strip at x (`strip_at`), or None."""
    s = strip_at(level, x, gap)
    return None if s is None else s[1]


def got_past(reached_x: float, completed: bool, edge: float) -> bool:
    """Alive with the whole cube past `edge`: completed, or died further on than edge + half a cube."""
    return completed or reached_x > edge + HALF_PLAYER


def milestones(runs: list[dict], edge: float) -> dict:
    """P8's milestones, as run counts. Each run: completed, x (death x, or the level length),
    ship_reached and ship_passed (from `stereo_madness.where`)."""
    return {"past Part 1's furthest point": sum(got_past(r["x"], r["completed"], edge) for r in runs),
            "reached the first ship portal": sum(r["ship_reached"] >= 1 for r in runs),
            "cleared the first ship section": sum(r["ship_passed"] >= 1 for r in runs),
            "completed the level": sum(bool(r["completed"]) for r in runs)}


def prediction8(median: float, any_past: bool, centre: float = 0.092, band: float = 0.01) -> dict:
    """D60's rule: the median is "unchanged" within ±1 percentage point of 9.2% (inclusive); the
    prediction is a hit only if it is, and some run gets past Part 1's furthest point."""
    unchanged = centre - band - 1e-12 <= median <= centre + band + 1e-12
    return {"median unchanged": unchanged, "a run past Part 1's furthest point": any_past,
            "hit": unchanged and any_past}
