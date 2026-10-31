"""The fly plays cube levels in closed loop (Step 2, D40-D42).

The fly's brain controls the cube: no bot, no tuning. Every tick is logged with what the brain
saw (our encoding) kept apart from what it did (its spikes), and the run is labelled
"driver: fly" (hard rule 10). The Step 2 baseline of record needs the calibrated θ_full and the
final subcircuit (D43); until then, runs here are smoke tests and say so.

Usage:
    uv run python scripts/play_cube.py cube-easy-0 --network interim --theta-full 180
    uv run python scripts/play_cube.py cube-easy-0 cube-easy-1 --suite training --jobs 2

Writes results/closed_loop/<network>/<settings>/<level>/ticks.csv and summary.json (git-ignored).
"""

import argparse
import json
import sys
import tomllib
from pathlib import Path

import pandas as pd
from joblib import Parallel, delayed

from find_target_neurons import fetch_annotations
from inspect_encoding import LEVELS, job
from reproduce_sugar import PATH_COMP, PATH_CON
from run_pathway_tests import CONFIG, git_commit, network
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.experiments.pathway_tests import loom_patches
from stereo_flyness.game.engine import Game
from stereo_flyness.game.suites import load_level
from stereo_flyness.interface.closed_loop import play
from stereo_flyness.interface.encoding import CubeEncoder

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "closed_loop"


def one(name, suite, path_comp, path_con, patches, gf, args, out, seed):
    from stereo_flyness.brain.stepper import BrainStepper

    level, _ = load_level(LEVELS, job(name, suite))
    enc = CubeEncoder(level, patches, args.theta_full, args.rate, args.mode)
    st = BrainStepper(path_comp, path_con, inputs={"loom": enc.ids}, watch=gf, seed=seed)
    result = play(Game(level), st, enc)
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(result.ticks).to_csv(d / "ticks.csv", index=False)
    summary = {**result.summary, "suite": suite, "network": args.network, "seed": seed, "commit": git_commit(),
               "status": "smoke test: uncalibrated settings, interim network (not the D43 baseline)"
               if args.network != "final" else "D43 run"}
    (d / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("levels", nargs="+")
    parser.add_argument("--suite", default="training")
    parser.add_argument("--network", default="interim", help="subcircuit name, or whole_brain")
    parser.add_argument("--theta-full", type=float, default=180.0)
    parser.add_argument("--rate", type=float, default=150.0)
    parser.add_argument("--mode", default="collision", choices=["collision", "all"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = tomllib.loads(CONFIG.read_text())
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    con = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
    patches = loom_patches(con, cells, cfg["probes"]["p5"]["seed"])  # P5's patch order (D41)
    gf = {"GF_R": cells.ids("DNp01", side="right"), "GF_L": cells.ids("DNp01", side="left")}
    path_comp, con_paths, _ = network(None if args.network == "whole_brain" else args.network)
    out = OUT / args.network / f"{args.theta_full:g}deg_{args.mode}_R{args.rate:g}"
    summaries = Parallel(n_jobs=args.jobs)(
        delayed(one)(n, args.suite, path_comp, con_paths["original"], patches, gf, args, out, args.seed)
        for n in args.levels)
    for s in summaries:
        death = "completed" if s["completed"] else f"died at {100 * s['progress']:.0f}% ({s['death']['kind']} at x {s['death']['x']:.0f})"
        print(f"{s['level']}: {death}; {s['jumps']} jumps, {s['presses']} presses in {s['seconds']:.1f} s [{s['status']}]")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
