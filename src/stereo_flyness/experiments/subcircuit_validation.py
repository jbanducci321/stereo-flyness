"""How closely a subcircuit reproduces the whole brain in the pathway tests (J5).

Both networks run the same conditions with the same seeds, so trials can be compared one to one.
Three kinds of comparison:
- **key groups:** each watched group's mean rate (Giant Fibers, VS, DNp20/22, LPi09), per condition;
- **whole activity:** every neuron's mean rate (D34 record), for neurons in the subcircuit, as a
  correlation plus how many whole-brain-active neurons stay active, go silent, or were cut out;
- **verdicts:** whether the go/no-go rules (D29-D31) come out the same.

How close is close enough is a decision for S5/J5, not made here: this only measures.
"""

import math

import numpy as np
import pandas as pd


def neuron_rates(trials: list[dict]) -> pd.Series:
    """Mean rate (Hz) of every neuron that fired in any of `trials`, indexed by FlyWire ID."""
    if not trials:
        return pd.Series(dtype=float)
    secs = sum(t["meta"]["n_frames"] * t["meta"]["frame_ms"] / 1000 for t in trials)
    total = {}
    for t in trials:
        for i, n in zip(t["all_ids"], t["all_spikes"].sum(axis=0)):
            total[int(i)] = total.get(int(i), 0) + int(n)
    return pd.Series(total, dtype=float) / secs


def activity_fidelity(whole: pd.Series, sub: pd.Series, sub_ids, exclude=()) -> dict:
    """Compare per-neuron rates. `exclude` (e.g. stimulated neurons, our input) is left out.

    - r: Pearson correlation of rates over neurons in the subcircuit that fire in either network;
    - kept_active: share of whole-brain-active neurons inside the subcircuit that still fire;
    - cut_active: whole-brain-active neurons that aren't in the subcircuit at all;
    - new_active: neurons that fire in the subcircuit but not in the whole brain.
    """
    sub_ids, exclude = set(int(i) for i in sub_ids), set(int(i) for i in exclude)
    whole = whole[[i not in exclude for i in whole.index]]
    sub = sub[[i not in exclude for i in sub.index]]
    inside = [i for i in whole.index if i in sub_ids]
    both = sorted(set(inside) | set(sub.index))
    w = whole.reindex(both, fill_value=0.0)
    s = sub.reindex(both, fill_value=0.0)
    r = float(np.corrcoef(w, s)[0, 1]) if len(both) > 1 and w.std() > 0 and s.std() > 0 else math.nan
    return {
        "whole_active": len(whole), "inside": len(inside),
        "kept_active": float((sub.reindex(inside, fill_value=0) > 0).mean()) if inside else math.nan,
        "cut_active": len(whole) - len(inside),
        "new_active": int(sum(i not in whole.index for i in sub.index)),
        "r": r,
    }


def compare_groups(whole: pd.DataFrame, sub: pd.DataFrame, groups) -> pd.DataFrame:
    """Per condition and group: whole-brain mean, subcircuit mean, difference and relative error.

    Both tables are per-trial rows from `trial_row` with a `key` column.
    """
    rows = []
    for key in sorted(set(whole["key"]) & set(sub["key"])):
        w, s = whole[whole["key"] == key], sub[sub["key"] == key]
        for g in groups:
            col = f"rate:{g}"
            if col not in w or w[col].isna().all():
                continue
            wm, sm = w[col].mean(), s[col].mean()
            rows.append({"condition": key, "group": g, "whole": wm, "subcircuit": sm, "diff": sm - wm,
                         "rel_error": (sm - wm) / wm if wm else (0.0 if sm == 0 else math.inf)})
    return pd.DataFrame(rows)
