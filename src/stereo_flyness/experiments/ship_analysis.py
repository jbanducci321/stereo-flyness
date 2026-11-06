"""The ship baseline's design-independent measures (Step 5). Used by scripts/ship_report.py.

Everything here reads only the game log (ticks.parquet, run.json), so it works for any ship design.
What depends on the design (death classes like D48's, timing against the fly's own readout) waits
for it. The bars these feed are **proposals** until Step 5's decision fixes them with Shannyn.

- `replay_run`: rebuild a run from its logged holds and check it matches the record.
- `compare_runs`: D48's "equal", in game terms: both completed, or both died on the same object
  (`death_source_id`); otherwise the one that got further is better.
- `hold_stats`: how the fly held in ship mode: share of ship ticks held, the length of each hold
  and each release (the ship needs sustained holds, docs/notes/ship_brief.md §1), switches per second.
- `sections_reached`: for mixed levels, which ship sections the player reached and got through.
"""

import numpy as np
import pandas as pd

from stereo_flyness.game.engine import Game
from stereo_flyness.game.physics import TICKS_PER_SECOND


def replay_run(level, held, run: dict) -> Game:
    """Replay the logged holds; stop if the game doesn't end exactly as recorded."""
    game = Game(level)
    for h in held:
        if game.over:
            raise ValueError(f"{run.get('level')}: the logged holds go on after the game ended")
        game.tick(bool(h))
    got = {"completed": game.finished, "ticks": game.ticks, "progress": game.progress}
    for k, v in got.items():
        if (abs(v - run[k]) > 1e-9) if isinstance(v, float) else v != run[k]:
            raise ValueError(f"{run.get('level')}: replay gives {k} = {v}, the record says {run[k]}")
    return game


def compare_runs(a: dict, b: dict) -> int:
    """+1 if run `a` did better than `b`, -1 if worse, 0 if equal. Dicts with completed, progress
    and death_source_id (None for a death on no object, e.g. a level with none)."""
    if a["completed"] and b["completed"]:
        return 0
    if a["completed"] != b["completed"]:
        return 1 if a["completed"] else -1
    src_a, src_b = a.get("death_source_id"), b.get("death_source_id")
    if src_a is not None and not pd.isna(src_a) and src_a == src_b:
        return 0
    return int(np.sign(a["progress"] - b["progress"]))


def _runs(mask: np.ndarray) -> list[int]:
    """Lengths of the runs of True in `mask`."""
    if not mask.any():
        return []
    padded = np.concatenate([[False], mask, [False]]).astype(int)
    d = np.diff(padded)
    return list(np.flatnonzero(d == -1) - np.flatnonzero(d == 1))


def hold_stats(ticks: pd.DataFrame, mode: str = "ship") -> dict:
    """Holding in `mode` only (ticks.parquet: `mode` and `held` per tick).

    Holds and releases are counted within each stretch in that mode, so a hold doesn't run on
    across a cube section."""
    in_mode = ticks["mode"].to_numpy() == mode
    held = ticks["held"].to_numpy(bool)
    holds, releases, switches = [], [], 0
    for a, n in zip(*_starts_and_lengths(in_mode)):
        h = held[a:a + n]
        holds += _runs(h)
        releases += _runs(~h)
        switches += int(np.count_nonzero(h[1:] != h[:-1]))
    n_ticks = int(in_mode.sum())
    return {"ticks": n_ticks, "held_share": float(held[in_mode].mean()) if n_ticks else None,
            "holds": len(holds), "median_hold_ticks": float(np.median(holds)) if holds else None,
            "median_release_ticks": float(np.median(releases)) if releases else None,
            "switches_per_s": switches / (n_ticks / TICKS_PER_SECOND) if n_ticks else None}


def _starts_and_lengths(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    padded = np.concatenate([[False], mask, [False]]).astype(int)
    d = np.diff(padded)
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return starts, ends - starts


def sections_reached(level, final_x: float, completed: bool) -> list[dict]:
    """Each ship section of the level: reached (the player got to its start) and passed (got past its end)."""
    out = []
    for mode, x0, x1, _ in level.sections():
        if mode == "ship":
            out.append({"x0": x0, "x1": x1, "reached": completed or final_x >= x0,
                        "passed": completed or final_x >= x1})
    return out


def death_mode(ticks: pd.DataFrame, completed: bool) -> str | None:
    """The mode the player died in (None if it completed)."""
    return None if completed or ticks.empty else str(ticks["mode"].iloc[-1])
