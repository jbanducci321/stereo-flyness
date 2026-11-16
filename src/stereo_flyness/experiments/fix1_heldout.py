"""Fix 1, step 4: the held-out opening's verdicts (docs/notes/fix1_heldout_plan.md).

Pure functions; `scripts/fix1_heldout_report.py` loads the runs, checks them and writes the report.
The test's per-level reading (the feature, getting past it) is step 3's (`fix1_step3.py`), unchanged.

- **The test (D55's bar), iteration-2 held-out levels:** fix 1 passes if the fixed fly is better on more
  levels than worse and the two-sided sign test over the levels that differ gives p < 0.05.
- **The no-harm check, iteration 1's held-out cube levels:** each level's score is the median, over its
  seeds, of the obstacle groups a run passes. Fix 1 passes if there's no significant drop (p < 0.05 with
  more levels worse than better) and it's worse on no more levels than better. The second condition
  implies the first; both are D55's wording, so both are reported.
"""

from statistics import median

import numpy as np

from stereo_flyness.experiments.fix1_step3 import sign_test


def groups_passed(outs: list[str]) -> int:
    """Obstacle groups a run got past (a completed run passes all of them)."""
    return sum(o == "cleared" for o in outs)


def level_score(passed: list[int]) -> float:
    """A level's no-harm score: the median run over its seeds."""
    return median(passed)


def compare(fixed: dict, unfixed: dict) -> tuple[int, int, int]:
    """Levels where the fixed score is higher (better), lower (worse), or equal (tied)."""
    better = sum(fixed[lv] > unfixed[lv] for lv in unfixed)
    worse = sum(fixed[lv] < unfixed[lv] for lv in unfixed)
    return better, worse, len(unfixed) - better - worse


def bar_verdict(better: int, worse: int) -> tuple[bool, float]:
    p = sign_test(better, worse)
    return better > worse and p < 0.05, p


def no_harm_verdict(better: int, worse: int) -> tuple[bool, bool, float]:
    """(no significant drop, worse on no more levels than better, p)."""
    p = sign_test(better, worse)
    return not (p < 0.05 and worse > better), worse <= better, p


def arms_diverge(unfixed: np.ndarray, fixed: np.ndarray, predicted: np.ndarray) -> str | None:
    """Same level and seed: why the arms' holds break the rule, or None. They must be equal up to the
    first frame fix 1 changed (`predicted`), and throughout if it changed none: identical input, same seed."""
    if len(predicted) != len(fixed):
        return "the brain log and the ticks differ in length"
    if not predicted.any():
        if len(unfixed) != len(fixed) or not (unfixed == fixed).all():
            return "fix 1 changed no frame, but the arms differ"
        return None
    n = min(int(predicted.argmax()), len(unfixed))
    return None if (unfixed[:n] == fixed[:n]).all() else "the arms differ before fix 1 changed a frame"
