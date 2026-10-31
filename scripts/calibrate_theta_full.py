"""Calibrate θ_full to the fly's 39° escape threshold (D43), open loop.

For each θ_full, the cube runs at game speed straight at one spike and never jumps (the brain
only watches: runs are labelled bot-driven). θ at the Giant Fiber's first spike is recorded per
trial. The calibrated θ_full is where the mean crosses 39°.

D43's official calibration runs on the whole brain at R = 150 Hz. Runs on a subcircuit are dry
runs and are labelled as such.

Usage:
    uv run python scripts/calibrate_theta_full.py --network interim --trials 5          # dry run
    uv run python scripts/calibrate_theta_full.py --network whole_brain --trials 10     # official

Writes results/calibration/<network>/ (git-ignored): one recorded run per θ_full x trial,
results.csv and report.md.
"""

import argparse
import math
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from find_target_neurons import fetch_annotations
from reproduce_sugar import PATH_COMP, PATH_CON
from run_pathway_tests import CONFIG, git_commit, network
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.experiments.cascades import load_stuck_state
from stereo_flyness.experiments.pathway_tests import loom_patches
from stereo_flyness.game.engine import Game
from stereo_flyness.interface.calibration import TARGET_DEG, approach_level, crossing, first_spike_theta
from stereo_flyness.interface.closed_loop import play
from stereo_flyness.interface.encoding import CubeEncoder

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "calibration"
GRID = [180, 360, 720, 1440, 2880, 5760, 11520]


def trial(theta_full, t, path_comp, path_con, patches, gf, stuck_ids, args, out):
    from stereo_flyness.brain.stepper import BrainStepper

    level = approach_level(args.start_gap)
    enc = CubeEncoder(level, patches, theta_full, args.rate)
    seed = 1000 * t + int(theta_full)  # fixed per (θ_full, trial)
    st = BrainStepper(path_comp, path_con, inputs={"loom": enc.ids}, watch=gf, seed=seed)
    meta = {"network": args.network, "seed": seed, "commit": git_commit(), "purpose": "theta_full calibration (D43)",
            "status": "official" if args.network == "whole_brain" else "dry run (subcircuit)"}
    rec = play(Game(level), st, enc, policy=lambda g: False, stuck_ids=stuck_ids, meta=meta)
    rec.save(out / f"{theta_full:g}deg" / f"trial_{t:02d}")
    theta = first_spike_theta(rec.brain)
    hit = None if theta is None else rec.brain.loc[(rec.brain["spikes_GF_R"] + rec.brain["spikes_GF_L"]) > 0].iloc[0]
    return {"theta_full": theta_full, "trial": t, "first_spike_theta": theta,
            "gap_at_spike": None if hit is None else hit["gap"],
            "driven_at_spike": None if hit is None else int(sum(hit[c] for c in rec.brain.columns if c.startswith("driven_"))),
            "stuck": rec.stuck_from is not None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--network", default="interim", help="subcircuit name, or whole_brain")
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--rate", type=float, default=150.0)
    parser.add_argument("--start-gap", type=float, default=600.0, help="units from the eye to the spike at the start")
    parser.add_argument("--grid", type=float, nargs="+", default=GRID, help="θ_full values, degrees")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = tomllib.loads(CONFIG.read_text())
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    con = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
    patches = loom_patches(con, cells, cfg["probes"]["p5"]["seed"])
    gf = {"GF_R": cells.ids("DNp01", side="right"), "GF_L": cells.ids("DNp01", side="left")}
    stuck_ids = load_stuck_state(ROOT / cfg["cascade"]["stuck_state"])
    path_comp, con_paths, _ = network(None if args.network == "whole_brain" else args.network)
    out = OUT / args.network / f"gap{args.start_gap:g}_R{args.rate:g}"

    rows = Parallel(n_jobs=args.jobs)(
        delayed(trial)(tf, t, path_comp, con_paths["original"], patches, gf, stuck_ids, args, out)
        for tf in args.grid for t in range(args.trials))
    df = pd.DataFrame(rows)
    df.to_csv(out / "results.csv", index=False)

    per = df.groupby("theta_full").agg(
        mean=("first_spike_theta", "mean"), sd=("first_spike_theta", "std"),
        fired=("first_spike_theta", lambda s: int(s.notna().sum())), trials=("trial", "size"),
        mean_gap=("gap_at_spike", "mean"), driven=("driven_at_spike", "median"), stuck=("stuck", "sum")).reset_index()
    cal = crossing(list(per["theta_full"]), list(per["mean"]))
    total = sum(len(patches[s][t]) for s in patches for t in patches[s])
    status = "OFFICIAL (whole brain)" if args.network == "whole_brain" else "DRY RUN (subcircuit; not the D43 calibration)"
    lines = [f"# θ_full calibration: {status}\n",
             f"Network `{args.network}`, R = {args.rate:g} Hz, the spike starts {args.start_gap:g} units ahead of the eye, "
             f"{args.trials} trials per θ_full. Target: first Giant Fiber spike at θ = {TARGET_DEG:g}°. "
             f"Open loop: the cube never jumps (runs labelled bot-driven).\n",
             "| θ_full (°) | first-spike θ, mean ± s.d. (°) | trials that fired | gap at spike (units) | neurons driven at spike (of "
             f"{total}) | stuck |", "|---|---|---|---|---|---|"]
    for r in per.itertuples():
        m = "none" if math.isnan(r.mean) else f"{r.mean:.1f} ± {0 if math.isnan(r.sd) else r.sd:.1f}"
        lines.append(f"| {r.theta_full:g} | {m} | {r.fired}/{r.trials} | "
                     f"{'–' if math.isnan(r.mean_gap) else f'{r.mean_gap:.0f}'} | "
                     f"{'–' if math.isnan(r.driven) else f'{r.driven:.0f}'} | {r.stuck} |")
    if cal is None:
        lines.append(f"\n**No crossing of {TARGET_DEG:g}° in this grid.** Extend `--grid`.")
    else:
        f = TARGET_DEG / cal
        at = {f"{s} {t}": int(round(f * len(patches[s][t]))) for s in patches for t in patches[s]}
        lines += [f"\n**Calibrated θ_full ≈ {cal:,.0f}°** (log-interpolated). At θ = {TARGET_DEG:g}° that drives "
                  f"f = {f:.4f} of each population: " + ", ".join(f"{k} {v}" for k, v in at.items())
                  + f" ({sum(at.values())} of {total} neurons)."]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
