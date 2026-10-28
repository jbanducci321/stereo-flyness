"""Run the Step 0 pathway tests (J4; design in docs/pathway_tests.md, config in
configs/pathway_tests.toml) on the whole brain.

Each trial is saved as its own file in git-ignored results/pathway_tests/<sign>/<experiment>/,
so the run can be stopped and restarted: finished trials are skipped.

Usage:
    uv run python scripts/run_pathway_tests.py --dry-run                 # list conditions, estimate time
    uv run python scripts/run_pathway_tests.py --only E1,S1 --jobs 4
    uv run python scripts/run_pathway_tests.py --match 150Hz --trials 1  # quick pilot
    uv run python scripts/run_pathway_tests.py --summary                 # rates from saved trials

The corrected connectivity (steering only) comes from scripts/make_corrected_connectivity.py.
"""

import argparse
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from find_target_neurons import fetch_annotations
from reproduce_sugar import PATH_COMP, PATH_CON, SUGAR_GRNS_783
from stereo_flyness.brain.celltypes import CellTypes, top_partners
from stereo_flyness.brain.signs import CORRECTED_NAME
from stereo_flyness.experiments.pathway_tests import DT_MS, build_conditions, frame_steps, load_trial, run_trial

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "pathway_tests.toml"
OUT = ROOT / "results" / "pathway_tests"
CON_PATHS = {"original": PATH_CON, "corrected": ROOT / "data" / CORRECTED_NAME}

# Rough whole-brain cost for --dry-run: FEASIBILITY benchmarks (16-26x real time, one worker)
# plus building the network for every trial.
SLOWDOWN, BUILD_S = 20, 30
SUMMARY_GROUPS = ["GF_R", "GF_L", "VS_R", "VS_L", "DNp20_R", "DNp22_R", "LPi09_R"]


def git_commit() -> str:
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    commit = git("rev-parse", "HEAD") or "unknown"
    return commit + ("-dirty" if git("status", "--porcelain", "--untracked-files=no") else "")


def conditions(cfg):
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    con = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
    n = cfg["escape"]["gf_partners"]
    partners = {s[0].upper(): top_partners(con, cells.ids("DNp01", side=s)[0], n) for s in ("right", "left")}
    return build_conditions(cfg, cells, partners, SUGAR_GRNS_783)


def select(conds, only, match):
    if only:
        wanted = only.split(",")
        conds = [c for c in conds if any(c.experiment.startswith(w) for w in wanted)]
    if match:
        conds = [c for c in conds if match in c.key]
    return conds


def summary(conds):
    rows = []
    for c in conds:
        paths = [c.path(OUT, t) for t in range(c.trials) if c.path(OUT, t).exists()]
        if not paths:
            continue
        per_trial = {}
        for p in paths:
            tr = load_trial(p)
            secs = tr["meta"]["n_frames"] * tr["meta"]["frame_ms"] / 1000
            for g in SUMMARY_GROUPS:
                if g in tr["spikes"]:  # mean rate per neuron in the group
                    per_trial.setdefault(g, []).append(tr["spikes"][g].sum(axis=0).mean() / secs)
        row = {"condition": c.key, "trials": len(paths)}
        for g, v in per_trial.items():
            row[g] = f"{np.mean(v):.1f} +/- {np.std(v, ddof=1) if len(v) > 1 else 0:.1f}"
        rows.append(row)
    if rows:
        print(pd.DataFrame(rows).set_index("condition").fillna("").to_string())
        print("\nRates are Hz per neuron, mean +/- SD across trials.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="experiments to run, by prefix, e.g. E1,S1 or E5")
    parser.add_argument("--match", help="only conditions whose name contains this text")
    parser.add_argument("--trials", type=int, help="run at most this many trials per condition")
    parser.add_argument("--jobs", type=int, default=4, help="parallel workers (each holds the whole brain, ~2-3 GB)")
    parser.add_argument("--dry-run", action="store_true", help="list conditions and estimated time, run nothing")
    parser.add_argument("--summary", action="store_true", help="print rates from saved trials, run nothing")
    args = parser.parse_args()

    cfg = tomllib.loads(CONFIG.read_text())
    conds = select(conditions(cfg), args.only, args.match)
    if args.summary:
        summary(conds)
        return

    tasks = [(c, t) for c in conds for t in range(min(c.trials, args.trials or c.trials))
             if not c.path(OUT, t).exists()]
    sim_s = sum(c.n_frames for c, _ in tasks) * frame_steps(cfg["frame_ms"]) * DT_MS / 1000
    est_h = (sim_s * SLOWDOWN + len(tasks) * BUILD_S) / 3600
    print(f"{len(conds)} conditions; {len(tasks)} trials to run ({sim_s:.0f} s simulated), "
          f"roughly {est_h:.1f} h on one worker, less with --jobs")
    if args.dry_run:
        for exp, n in pd.Series([c.experiment for c, _ in tasks]).value_counts(sort=False).items():
            print(f"  {exp}: {n} trials")
        return
    if not tasks:
        return
    if any(c.sign == "corrected" for c, _ in tasks) and not CON_PATHS["corrected"].exists():
        sys.exit("Corrected connectivity missing. Run scripts/make_corrected_connectivity.py first.")

    meta = {"commit": git_commit(), "config": CONFIG.read_text()}
    t0 = time.perf_counter()
    Parallel(n_jobs=args.jobs, verbose=10)(
        delayed(run_trial)(c, t, OUT, PATH_COMP, CON_PATHS[c.sign], cfg["base_seed"], cfg["frame_ms"], meta)
        for c, t in tasks)
    print(f"Ran {len(tasks)} trials in {(time.perf_counter() - t0) / 60:.1f} min")
    summary(conds)


if __name__ == "__main__":
    main()
