"""Run the Step 0 pathway tests (J4; design in docs/pathway_tests.md, config in
configs/pathway_tests.toml) on the whole brain or a subcircuit.

Each trial is saved as its own file in git-ignored results/pathway_tests/<sign>/<experiment>/,
so the run can be stopped and restarted: finished trials are skipped.

Usage:
    uv run python scripts/run_pathway_tests.py --dry-run                 # list conditions, estimate time
    uv run python scripts/run_pathway_tests.py --only E1,S1 --jobs 4
    uv run python scripts/run_pathway_tests.py --match 150Hz --trials 1  # quick pilot
    uv run python scripts/run_pathway_tests.py --summary                 # rates from saved trials
    uv run python scripts/run_pathway_tests.py --subcircuit example      # same tests on a subcircuit (J5)

The corrected connectivity (steering only) comes from scripts/make_corrected_connectivity.py.
With --subcircuit NAME, the tests run on data/subcircuits/NAME/ (scripts/extract_subcircuit.py)
and are saved to results/subcircuits/NAME/pathway_tests/. Conditions whose neurons aren't all in
the subcircuit are skipped and listed. Seeds are the same as the whole brain's, so the two can be
compared trial by trial.
"""

import argparse
import dataclasses
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
from stereo_flyness.experiments.pathway_tests import (
    DT_MS, build_conditions, frame_steps, load_trial, loom_patches, run_trial,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "pathway_tests.toml"
OUT = ROOT / "results" / "pathway_tests"
CON_PATHS = {"original": PATH_CON, "corrected": ROOT / "data" / CORRECTED_NAME}

# Rough whole-brain cost for --dry-run: FEASIBILITY benchmarks (16-26x real time, one worker)
# plus building the network for every trial.
SLOWDOWN, BUILD_S = 20, 30
SUMMARY_GROUPS = ["GF_R", "GF_L", "VS_R", "VS_L", "DNp20_R", "DNp22_R", "LPi09_R"]
SUBCIRCUITS = ROOT / "data" / "subcircuits"


def network(subcircuit=None):
    """(comp path, {sign: connectivity path}, results folder) for the whole brain or a subcircuit."""
    if subcircuit is None:
        return PATH_COMP, CON_PATHS, OUT
    d = SUBCIRCUITS / subcircuit
    if not (d / "comp.csv").exists():
        sys.exit(f"No subcircuit at {d}. Run scripts/extract_subcircuit.py first.")
    cons = {"original": d / "con.parquet"}
    if (d / "con_corrected.parquet").exists():
        cons["corrected"] = d / "con_corrected.parquet"
    return d / "comp.csv", cons, ROOT / "results" / "subcircuits" / subcircuit / "pathway_tests"


def runnable(conds, path_comp, con_paths):
    """Conditions whose sign version exists and whose input and watched neurons are all in the
    network, and the rest. A silenced neuron that isn't in the network is already gone, which is
    the same as silencing it (no outgoing synapses), so it's dropped from the silence list."""
    ids = set(pd.read_csv(path_comp, index_col=0).index)
    ok, skipped = [], []
    for c in conds:
        needed = {i for g in (c.inputs, c.watch) for v in g.values() for i in v}
        if c.sign in con_paths and needed <= ids:
            ok.append(dataclasses.replace(c, silence=[i for i in c.silence if i in ids]))
        else:
            skipped.append(c)
    return ok, skipped


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
    p5 = cfg.get("probes", {}).get("p5")
    patches = loom_patches(con, cells, p5["seed"]) if p5 else None
    return build_conditions(cfg, cells, partners, SUGAR_GRNS_783, patches)


def select(conds, only, match):
    if only:
        wanted = only.split(",")
        conds = [c for c in conds if any(c.experiment.startswith(w) for w in wanted)]
    if match:
        conds = [c for c in conds if match in c.key]
    return conds


def summary(conds, out=OUT):
    rows = []
    for c in conds:
        paths = [c.path(out, t) for t in range(c.trials) if c.path(out, t).exists()]
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
    parser.add_argument("--subcircuit", help="run on data/subcircuits/NAME instead of the whole brain")
    args = parser.parse_args()

    cfg = tomllib.loads(CONFIG.read_text())
    path_comp, con_paths, out = network(args.subcircuit)
    conds, skipped = runnable(select(conditions(cfg), args.only, args.match), path_comp, con_paths)
    if skipped:
        print(f"Skipping {len(skipped)} conditions (sign version or neurons not in this network): "
              f"{', '.join(c.key for c in skipped[:5])}{' ...' if len(skipped) > 5 else ''}")
    if args.summary:
        summary(conds, out)
        return

    tasks = [(c, t) for c in conds for t in range(min(c.trials, args.trials or c.trials))
             if not c.path(out, t).exists()]
    # Zero-input baselines first, so the automatic check (D30) stops a broken round early
    tasks.sort(key=lambda task: task[0].rates().any())
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
    if any(not con_paths[c.sign].exists() for c, _ in tasks):
        sys.exit("Corrected connectivity missing. Run scripts/make_corrected_connectivity.py first.")

    meta = {"commit": git_commit(), "config": CONFIG.read_text(), "network": args.subcircuit or "whole_brain"}
    t0 = time.perf_counter()
    Parallel(n_jobs=args.jobs, verbose=10)(
        delayed(run_trial)(c, t, out, path_comp, con_paths[c.sign], cfg["base_seed"], cfg["frame_ms"], meta)
        for c, t in tasks)
    print(f"Ran {len(tasks)} trials in {(time.perf_counter() - t0) / 60:.1f} min")
    summary(conds, out)


if __name__ == "__main__":
    main()
