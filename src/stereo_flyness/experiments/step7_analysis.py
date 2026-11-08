"""Step 7's comparisons (D52): the whole brain against the subcircuit, on fly-driven runs with the
same settings, level and Poisson seed. Used by scripts/step7_report.py.

- `state_split` (the bar): two games are identical if the cube's state (x, y, vy) is exactly the
  same after every tick and they last the same number of ticks. If not, the first tick where it
  differs. Judged on the game, not the press log: the Giant Fiber carries over and presses in
  mid-air, where a press does nothing, so an extra mid-air press isn't a split (Shannyn, D52).
- `first_split`: the first tick where the logged presses differ. Described only: a pair can
  differ in presses and still play the same game.
- `shared_approaches` (described only): rule 5 (D46) on fly-driven runs. Each approach's first
  press is compared, only while both networks saw exactly the same game, i.e. up to and including
  the split. After it the games are in different states, so approaches don't line up.
"""

import numpy as np
import pandas as pd

from stereo_flyness.experiments.subcircuit_validation import press_agreement

STATE = ("x", "y", "vy")


def first_split(held_a, held_b) -> int | None:
    """The first tick where two runs' presses differ, or None if the press logs are identical.

    A run that ends earlier than the other with no differing press before that splits where it ended."""
    a, b = np.asarray(held_a, bool), np.asarray(held_b, bool)
    n = min(len(a), len(b))
    diff = np.flatnonzero(a[:n] != b[:n])
    if len(diff):
        return int(diff[0])
    return None if len(a) == len(b) else n


def state_split(ticks_a: pd.DataFrame, ticks_b: pd.DataFrame) -> int | None:
    """The first row of ticks.parquet (the state after that tick) where the cube's x, y or vy
    differ, or None if the games are identical. Exact comparison: the game is deterministic.

    Row j is the state after the tick that applied brain row j's press (D40), so the brain rows
    that saw the same game are 0..j: the split row is also the last brain row both saw alike."""
    a, b = ticks_a.loc[:, STATE].to_numpy(float), ticks_b.loc[:, STATE].to_numpy(float)
    n = min(len(a), len(b))
    diff = np.flatnonzero((a[:n] != b[:n]).any(axis=1))
    if len(diff):
        return int(diff[0])
    return None if len(a) == len(b) else n


def shared_approaches(whole: pd.DataFrame, sub: pd.DataFrame, spans: list[tuple[int, int]],
                      split: int | None, max_frames: int = 1) -> dict:
    """Rule 5 on the part of two fly-driven runs where both saw the same game.

    Brain row k saw the game after k ticks and decided the press applied at row k, so the input is
    the same up to and including the split row; the presses there are compared. `spans` are the
    approaches from a replay (`approach_spans`)."""
    n = min(len(whole), len(sub)) if split is None else min(split + 1, len(whole), len(sub))
    clipped = [(a, min(b, n)) for a, b in spans if a < n]
    out = press_agreement(whole.iloc[:n].reset_index(drop=True), sub.iloc[:n].reset_index(drop=True),
                          max_frames=max_frames, spans=clipped)
    out["compared"] = out["approaches"] - out["neither"]
    return out
