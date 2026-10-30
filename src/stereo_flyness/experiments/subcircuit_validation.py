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
    - kept_active: share of **all** whole-brain-active neurons that still fire in the subcircuit
      (D36 rule 4). Neurons the build cut out count as lost: they are what held-out tests catch;
    - kept_inside: the same share among only the whole-brain-active neurons inside the subcircuit;
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
    still = int((sub.reindex(inside, fill_value=0) > 0).sum())
    return {
        "whole_active": len(whole), "inside": len(inside),
        "kept_active": still / len(whole) if len(whole) else math.nan,
        "kept_inside": still / len(inside) if inside else math.nan,
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


def kept_by_type(fid: pd.DataFrame, experiment_of: dict, threshold: float = 0.90) -> dict:
    """D36 rule 4 per probe type: {experiment: (median kept_active, lowest, passes)}. Each type
    passes if its median share of whole-brain-active neurons kept is >= `threshold`."""
    fa = fid[fid["whole_active"] > 0]
    out = {}
    for exp, rows in fa.groupby(fa["condition"].map(experiment_of)):
        med = float(rows["kept_active"].median())
        out[exp] = (med, float(rows["kept_active"].min()), med >= threshold)
    return out


def paired_cascades(whole_counts: dict, sub_counts: dict, ratio: float, min_extra: float) -> set:
    """Trials of one condition left out of rules 2-4 (D37): those where the whole brain's or the
    subcircuit's trial is a cascade (each judged against its own network's other trials)."""
    from stereo_flyness.experiments.cascades import cascade_flags

    flagged = set()
    for counts in (whole_counts, sub_counts):
        flagged |= {t for t, f in cascade_flags(counts, ratio, min_extra).items() if f}
    return flagged


def within_tolerance(whole: float, sub: float, rel: float = 0.10, floor_hz: float = 1.0,
                     small_hz: float = 10.0) -> bool:
    """D36 rule 2: within 10% of the whole brain's rate, or within 1 Hz for groups under 10 Hz."""
    if whole < small_hz:
        return abs(sub - whole) <= floor_hz
    return abs(sub - whole) <= rel * whole


def onsets(rates: np.ndarray) -> list[int]:
    """Frames where input switches on: no input group active in the previous frame, some now."""
    on = rates.any(axis=1)
    return [i for i in range(len(on)) if on[i] and (i == 0 or not on[i - 1])]


def first_spikes(trial: dict, group: str) -> list[int | None]:
    """For each input onset in a trial, frames from onset to the group's first spike before the
    next onset (None if it doesn't spike)."""
    starts = onsets(trial["rates"])
    counts = trial["spikes"][group].sum(axis=1)
    out = []
    for k, s in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(counts)
        hit = np.flatnonzero(counts[s:end])
        out.append(int(hit[0]) if len(hit) else None)
    return out


def first_spike_agreement(whole_trials: list[dict], sub_trials: list[dict], group: str,
                          max_frames: int = 1) -> tuple[int, int]:
    """D36 rule 3, paired trial by trial (same seeds): (events matching, events). An event
    matches if both networks spike within `max_frames` of each other; onsets where neither
    network spikes aren't events."""
    match = total = 0
    for w, s in zip(whole_trials, sub_trials):
        for a, b in zip(first_spikes(w, group), first_spikes(s, group)):
            if a is None and b is None:
                continue
            total += 1
            match += a is not None and b is not None and abs(a - b) <= max_frames
    return match, total
