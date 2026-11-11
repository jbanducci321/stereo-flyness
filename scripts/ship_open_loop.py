"""The ship's open-loop checks before the baseline (Step 5; docs/notes/ship_analysis_plan.md, D53).

Whole brain, original signs, both eyes unless stated, 10 trials of 1 s each, with D53's input: all
T4d + T5d ("down") or all T4c + T5c ("up") at R_ship × f, R_ship = 150 Hz. Recorded as the pathway
tests are (every neuron that fires, D34), and **described**, except check 1:
1. **Zero input gives zero (the gate):** no ship input -> 0 DNp22 spikes (as D30). If it fails,
   nothing runs. (`run_trial` also stops on any spike with no input.)
2. **Response to motion speed:** "down" alone and "up" alone at f = 0.25, 0.5 and 1 (7.5, 15 and
   30°/s at ω_full = 30°/s).
3. **Left eye only:** "down" at the same f on the left eye's T4d + T5d.
4. **Both together:** "down" and "up" at the same f.

Usage:
    uv run python scripts/ship_open_loop.py --jobs 4      # runs what's missing, then the summary
    uv run python scripts/ship_open_loop.py --summary     # summary only

Trials go to results/ship_open_loop/ (git-ignored); the summary to results/ship_open_loop/summary.md.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from analyse_pathway_tests import md_table
from find_target_neurons import fetch_annotations
from reproduce_sugar import PATH_COMP, PATH_CON
from run_pathway_tests import git_commit
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.experiments.pathway_tests import Condition, load_trial, n_frames, run_trial

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "ship_open_loop"
R_SHIP = 150.0
F_LEVELS = (0.25, 0.5, 1.0)
TRIALS = 10
FRAME_MS = 4.1667  # one game tick (D23, D40)
DURATION_MS = 1000
BASE_SEED = 53
VS = [f"VS{i}" for i in range(1, 9)] + ["VSm"]


def conditions(cells: CellTypes) -> list[Condition]:
    def ids(*types, side=None):
        return cells.ids(*types) if side is None else cells.ids(*types, side=side)

    down, up = ids("T4d", "T5d"), ids("T4c", "T5c")
    down_left = ids("T4d", "T5d", side="left")
    watch = {f"{c}_{s[0].upper()}": ids(c, side=s) for c in ("DNp22", "DNp20") for s in ("right", "left")}
    watch |= {f"VS_{s[0].upper()}": ids(*VS, side=s) for s in ("right", "left")}
    n = n_frames(DURATION_MS, FRAME_MS)

    def cond(check, name, inputs, rates):
        return Condition(check, name, "original", inputs, [(n, rates)], watch, trials=TRIALS, side="both")

    out = [cond("check1", "zero_input", {"down": down, "up": up}, {"down": 0.0, "up": 0.0})]
    for f in F_LEVELS:
        r = R_SHIP * f
        out.append(cond("check2", f"down_both/f{f:g}", {"down": down}, {"down": r}))
        out.append(cond("check2", f"up_both/f{f:g}", {"up": up}, {"up": r}))
        out.append(cond("check3", f"down_left/f{f:g}", {"down_left": down_left}, {"down_left": r}))
        out.append(cond("check4", f"down+up_both/f{f:g}", {"down": down, "up": up}, {"down": r, "up": r}))
    return out


def summary(conds) -> pd.DataFrame:
    rows = []
    for c in conds:
        for t in range(c.trials):
            p = c.path(OUT, t)
            if not p.exists():
                continue
            tr = load_trial(p)
            seconds = tr["rates"].shape[0] * tr["meta"]["frame_ms"] / 1000
            row = {"check": c.experiment, "condition": c.name, "trial": t}
            for g, sp in tr["spikes"].items():
                if g in c.watch:
                    row[f"{g} Hz"] = sp.sum() / sp.shape[1] / seconds
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    conds = conditions(cells)
    if not args.summary:
        meta = {"commit": git_commit(), "network": "whole_brain", "purpose": "ship open-loop checks (D53)"}
        jobs = [(c, t) for c in conds for t in range(c.trials) if not c.path(OUT, t).exists()]
        print(f"{len(jobs)} trials to run", flush=True)
        Parallel(n_jobs=args.jobs)(delayed(run_trial)(c, t, OUT, PATH_COMP, PATH_CON, BASE_SEED, FRAME_MS, meta)
                                   for c, t in jobs)
    df = summary(conds)
    if df.empty:
        sys.exit("No trials yet.")
    cols = [c for c in df.columns if c.endswith(" Hz")]
    g = df.groupby(["check", "condition"], sort=False)
    table = g[cols].mean().round(1).astype(str) + " ± " + g[cols].std().fillna(0).round(1).astype(str)
    table.insert(0, "n", g.size())
    zero = df[df["check"] == "check1"]
    gate = zero[[c for c in cols if c.startswith("DNp22")]].to_numpy().sum() == 0 and len(zero) == TRIALS
    lines = ["# Ship open-loop checks (D53), whole brain, original signs\n",
             f"R_ship = {R_SHIP:g} Hz × f; 1 s trials; rates per cell, mean ± s.d. across trials.\n",
             f"**Check 1 (the gate), zero input → 0 DNp22 spikes in {len(zero)} trials: {'PASS' if gate else 'FAIL'}.**\n",
             md_table(table.reset_index(), 1)]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
