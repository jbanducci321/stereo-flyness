"""The ship's pathway from the logged steering tests (Step 5): each eye, and VSm (no new runs).

Reads the saved S1 and S2 trials (whole brain, original signs; results/pathway_tests/original/), which
drove T4d + T5d ("down") or T4c + T5c ("up") on the right eye, the left eye or both, and recorded
every neuron that fired (D34). Reports, per condition, the mean firing rate (Hz, ± s.d. across trials)
of the ship's readout DNp22 on each side, of DNp20, and of the VS cells that feed DNp22 (VS2, VS3,
VSm), on each side.

Answers two questions from Shannyn's draft (docs/notes/ship_proposals.md, ship_reading.md):
1. Does the left eye's "down" input reach DNp22 (the pathway tests' judged runs drove the right eye)?
2. How did VSm respond to "down" drive (it wasn't a watched group)?

These conditions were the recruitment runs (J5): logged, never judged by D29-D31. Descriptive only.

Usage:
    uv run python scripts/ship_pathway_check.py

Writes results/pathway_tests/analysis/ship_pathway.csv (git-ignored) and prints the tables.
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from stereo_flyness.experiments.pathway_tests import load_trial

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "results" / "pathway_tests" / "original"
ANN = ROOT / "data" / "flywire_annotations_v3.1.0_neurons.tsv"
OUT = ROOT / "results" / "pathway_tests" / "analysis" / "ship_pathway.csv"
CELLS = ["DNp22", "DNp20", "VS2", "VS3", "VSm"]
SIDES = {"R": "right", "L": "left"}
EYES = {"R": "right eye", "L": "left eye", "B": "both eyes"}


def cell_ids() -> dict[str, list[int]]:
    ann = pd.read_csv(ANN, sep="\t", low_memory=False, usecols=["root_id", "cell_type", "side"])
    return {f"{c}_{s}": ann.loc[(ann.cell_type == c) & (ann.side == side), "root_id"].astype("int64").tolist()
            for c in CELLS for s, side in SIDES.items()}


def rates(trial, ids: dict[str, list[int]]) -> dict[str, float]:
    """Mean firing rate per cell of each group (Hz) over the trial."""
    seconds = trial["rates"].shape[0] * float(trial["meta"]["frame_ms"]) / 1000
    col = {int(i): k for k, i in enumerate(trial["all_ids"])}
    total = trial["all_spikes"].sum(axis=0)
    return {g: sum(int(total[col[i]]) if i in col else 0 for i in members) / len(members) / seconds
            for g, members in ids.items()}


def collect(ids) -> pd.DataFrame:
    rows = []
    for exp in ("S1", "S2"):
        for cond in sorted((TRIALS / exp).iterdir()):
            m = (re.fullmatch(r"S1__(down|up)_([RLB])__(\d+)Hz", cond.name)
                 or re.fullmatch(r"S2__down_([RLB])_(\d+)Hz\+up_\1__(\d+)Hz", cond.name))
            if not m:
                continue
            if exp == "S1":
                key = {"test": "S1", "drive": m[1], "eye": m[2], "rate_hz": int(m[3]), "up_hz": None}
            else:
                key = {"test": "S2", "drive": "down", "eye": m[1], "rate_hz": int(m[2]), "up_hz": int(m[3])}
            for f in sorted(cond.glob("trial_*.npz")):
                rows.append({**key, "trial": f.stem, **rates(load_trial(f), ids)})
    return pd.DataFrame(rows)


def summary(df: pd.DataFrame, by: list[str], cols: list[str]) -> pd.DataFrame:
    g = df.groupby(by, dropna=False)
    out = g.size().rename("n").to_frame()
    for c in cols:
        out[c] = [f"{m:.1f} ± {s:.1f}" for m, s in zip(g[c].mean(), g[c].std().fillna(0))]
    return out.reset_index()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    df = collect(cell_ids())
    if df.empty:
        sys.exit(f"No S1/S2 trials found in {TRIALS}.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    df["eye"] = df["eye"].map(EYES)
    cols = [f"{c}_{s}" for c in CELLS for s in SIDES]
    print("S1: one motion group alone, by eye and rate (Hz per cell, mean ± s.d. across trials)\n")
    print(summary(df[df["test"] == "S1"], ["drive", "eye", "rate_hz"], cols).to_string(index=False))
    print("\nS2: 'down' at a fixed rate plus an 'up' sweep, by eye\n")
    print(summary(df[df["test"] == "S2"], ["eye", "rate_hz", "up_hz"], cols).to_string(index=False))
    print(f"\nWrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
