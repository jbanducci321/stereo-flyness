"""Judging the pathway tests by the rules agreed before round 1 (D29-D32 in docs/decisions.md).

Everything here works on per-trial summaries (`trial_row`), so each rule can be checked by hand
against the saved trials. Definitions used throughout:
- a group's rate is its mean firing rate per neuron over the trial (Hz);
- "fires" means at least one neuron in the group spikes during the trial;
- "reliably" means in at least 9 of 10 trials (D33), i.e. at least 90% of a condition's trials;
- latencies are measured to the *end* of the 4.2 ms frame holding the first spike, so they are
  upper bounds with one-frame resolution;
- pooled SD = sqrt((SD_a^2 + SD_b^2) / 2), the trial-to-trial SD of two equal-sized groups.
"""

import math

import numpy as np
import pandas as pd

RELIABLE = 0.9  # fraction of trials (D33: 9 of 10)
EARLY_MS = 100  # D32: E2's lower rate needs a Giant Fiber spike within the first 100 ms


def first_spike_ms(counts: np.ndarray, frame_ms: float) -> float:
    """End of the first frame with a spike (NaN if none)."""
    idx = np.flatnonzero(counts)
    return (idx[0] + 1) * frame_ms if len(idx) else math.nan


def trial_row(tr: dict) -> dict:
    """One saved trial (`load_trial`) reduced to rates, 'fires' flags and Giant Fiber latency."""
    m = tr["meta"]
    secs = m["n_frames"] * m["frame_ms"] / 1000
    row = {"key": m["key"], "trial": m["trial"]}
    for g, s in tr["spikes"].items():
        row[f"rate:{g}"] = float(s.sum(axis=0).mean() / secs)
        row[f"fires:{g}"] = bool(s.any())
    if "GF_R" in tr["spikes"]:
        row["gf_first_ms"] = first_spike_ms(tr["spikes"]["GF_R"][:, 0], m["frame_ms"])
    return row


def onoff_cycles(tr: dict, group: str = "GF_R") -> pd.DataFrame:
    """E2: per on/off cycle, onset latency, offset and spikes during 'on', for one neuron group.

    - onset: input on -> end of the first frame with a spike during 'on' (NaN if none);
    - offset: input off -> end of the last frame with a spike during 'off' (0 if it stops at once).
    """
    m = tr["meta"]
    fr = m["frame_ms"]
    counts = tr["spikes"][group].sum(axis=1)
    rows, start = [], 0
    schedule = m["condition"]["schedule"]
    for k in range(0, len(schedule), 2):
        n_on, n_off = schedule[k][0], schedule[k + 1][0]
        on, off = counts[start:start + n_on], counts[start + n_on:start + n_on + n_off]
        last = np.flatnonzero(off)
        rows.append({"cycle": k // 2, "onset_ms": first_spike_ms(on, fr),
                     "offset_ms": (last[-1] + 1) * fr if len(last) else 0.0,
                     "spikes_on": int(on.sum())})
        start += n_on + n_off
    return pd.DataFrame(rows)


def pooled_sd(a, b) -> float:
    return math.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2)


def reliable(flags) -> bool:
    flags = list(flags)
    return len(flags) > 0 and sum(flags) >= RELIABLE * len(flags)


def by_rate(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Mean, SD and trial count per input rate for the given columns."""
    return df.groupby("rate")[list(cols)].agg(["mean", "std", "count"])


def escape_rules(e1: pd.DataFrame) -> dict:
    """D29 rules 0-2 on E1 with LC4 + LPLC2. `e1` has one row per trial with a `rate` column.

    Rule 3 (onset latency) needs E2 at both rates and is judged separately (`latency_rule`).
    """
    rates = sorted(e1["rate"].unique())
    per_rate = {r: e1[e1["rate"] == r] for r in rates}
    rel = [r for r in rates if reliable(per_rate[r]["fires:GF_R"])]

    lo, hi = per_rate[min(rates)]["rate:GF_R"], per_rate[max(rates)]["rate:GF_R"]
    rise, rise_bar = hi.mean() - lo.mean(), 2 * pooled_sd(lo, hi)

    side = []
    for r in rel:
        right, left = per_rate[r]["rate:GF_R"], per_rate[r]["rate:GF_L"]
        diff, bar = right.mean() - left.mean(), 2 * pooled_sd(right, left)
        side.append({"rate": r, "right": right.mean(), "left": left.mean(), "diff": diff, "bar": bar,
                     "ratio": right.mean() / left.mean() if left.mean() else math.inf, "pass": diff > bar})
    side = pd.DataFrame(side)
    return {
        "reliable_rates": rel,
        "rule0": bool(rel),
        "rise": rise, "rise_bar": rise_bar, "rule1": bool(rise > rise_bar),
        "side": side, "rule2": bool(rel) and bool(side["pass"].all()),
    }


def pick_e2_rate(e1: pd.DataFrame) -> tuple[int, bool]:
    """D32: lowest rate where the right Giant Fiber spikes within 100 ms in >= 9/10 trials.
    Returns (rate, qualified); if none qualifies, (highest rate, False)."""
    for r in sorted(e1["rate"].unique()):
        early = e1.loc[e1["rate"] == r, "gf_first_ms"] <= EARLY_MS  # NaN (no spike) counts as False
        if reliable(early):
            return int(r), True
    return int(e1["rate"].max()), False


def latency_rule(cycles: pd.DataFrame, window_ms: float = 238) -> dict:
    """D29 rule 3 on E2 cycles (one row per trial x cycle): mean onset < 100 ms and
    4 x SD(onset) < the ~238 ms window. Cycles without a spike count as failures."""
    onset = cycles["onset_ms"]
    missed = int(onset.isna().sum())
    mean, sd = onset.mean(), onset.std(ddof=1)
    return {"mean_ms": mean, "sd_ms": sd, "missed_cycles": missed, "cycles": len(onset),
            "pass": missed == 0 and mean < 100 and 4 * sd < window_ms}


def steering_rules(s1: pd.DataFrame, down: str, up: str) -> dict:
    """D31 rules 1-2 for one sign version. `s1` has one row per trial with `group` and `rate`.

    Rule 3 (horizontal vs down at the half-of-maximum rate) needs round 2 (`horizontal_rule`).
    """
    rows = []
    for r in sorted(s1["rate"].unique()):
        d = s1[(s1["group"] == down) & (s1["rate"] == r)]
        u = s1[(s1["group"] == up) & (s1["rate"] == r)]
        rule1 = reliable(d["fires:VS_R"]) and reliable(d["fires:DNp20_R"])
        vs_frac = u["rate:VS_R"].mean() / d["rate:VS_R"].mean() if d["rate:VS_R"].mean() else math.inf
        dn_frac = u["rate:DNp20_R"].mean() / d["rate:DNp20_R"].mean() if d["rate:DNp20_R"].mean() else math.inf
        rows.append({"rate": r, "down_VS_R": d["rate:VS_R"].mean(), "down_DNp20_R": d["rate:DNp20_R"].mean(),
                     "up_VS_R": u["rate:VS_R"].mean(), "up_DNp20_R": u["rate:DNp20_R"].mean(),
                     "rule1": rule1, "up/down VS": vs_frac, "up/down DNp20": dn_frac,
                     "rule2": rule1 and vs_frac < 0.1 and dn_frac < 0.1})
    table = pd.DataFrame(rows)
    return {"table": table, "rule1": bool(table["rule1"].any()), "rule2": bool(table["rule2"].any())}


def pick_half_max(s1_down: pd.DataFrame) -> tuple[int, float]:
    """D32: lowest sweep rate whose mean right-VS rate is at least half the sweep's highest mean.
    Returns (rate, that rate's fraction of the maximum)."""
    means = s1_down.groupby("rate")["rate:VS_R"].mean().sort_index()
    top = means.max()
    for r, v in means.items():
        if v >= 0.5 * top:
            return int(r), float(v / top)
    raise ValueError("no rates")


def horizontal_rule(down: pd.DataFrame, horiz: pd.DataFrame) -> dict:
    """D31 rule 3: horizontal input's right-VS rate is below 'down' by more than 2 pooled SDs."""
    d, h = down["rate:VS_R"], horiz["rate:VS_R"]
    diff, bar = d.mean() - h.mean(), 2 * pooled_sd(d, h)
    return {"down": d.mean(), "horizontal": h.mean(), "diff": diff, "bar": bar, "pass": bool(diff > bar)}
