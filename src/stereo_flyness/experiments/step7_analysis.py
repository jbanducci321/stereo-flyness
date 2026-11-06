"""Step 7's comparisons (docs/notes/step7_proposal.md): the whole brain against the subcircuit, on
fly-driven runs with the same settings, level and Poisson seed. Used by scripts/step7_report.py.

Both candidate bars are computed, so the script works whichever one D52 fixes:
- `first_split`: are two games identical tick for tick? If not, the first tick where the presses
  differ. Bar (a) in the proposal: identical in at least 57 of 60 pairs.
- `shared_approaches`: rule 5 (D46) on fly-driven runs. Each approach's first press is compared,
  but only while both networks saw exactly the same game, i.e. up to and including the split.
  After a split, the two games are different games and their approaches no longer line up, so they
  aren't compared at all (neither as matches nor as misses).
"""

import numpy as np
import pandas as pd

from stereo_flyness.experiments.subcircuit_validation import press_agreement


def first_split(held_a, held_b) -> int | None:
    """The first tick where two runs' presses differ, or None if the games are identical.

    A run that ends earlier than the other with no differing press before that splits where it
    ended (the games can't be identical if one is longer)."""
    a, b = np.asarray(held_a, bool), np.asarray(held_b, bool)
    n = min(len(a), len(b))
    diff = np.flatnonzero(a[:n] != b[:n])
    if len(diff):
        return int(diff[0])
    return None if len(a) == len(b) else n


def shared_approaches(whole: pd.DataFrame, sub: pd.DataFrame, spans: list[tuple[int, int]],
                      split: int | None, max_frames: int = 1) -> dict:
    """Rule 5 on the part of two fly-driven runs where both saw the same game.

    Brain row k saw the game after k ticks and decided the press applied at row k, so the input is
    the same up to and including the split row; the differing press there is compared. `spans` are
    the approaches from a replay (`approach_timing`'s `approach_spans`)."""
    n = min(len(whole), len(sub)) if split is None else split + 1
    clipped = [(a, min(b, n)) for a, b in spans if a < n]
    out = press_agreement(whole.iloc[:n].reset_index(drop=True), sub.iloc[:n].reset_index(drop=True),
                          max_frames=max_frames, spans=clipped)
    out["compared"] = out["approaches"] - out["neither"]
    return out
