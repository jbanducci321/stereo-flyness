"""The fly plays cube levels in closed loop (Step 2, D40-D42).

The fly's brain controls the cube: no bot, no tuning. Every tick is logged with what the brain
saw (our encoding) kept apart from what it did (its spikes), and the run is labelled
"driver: fly" (hard rule 10). The Step 2 baseline of record needs the calibrated θ_full and the
final subcircuit (D43); until then, runs here are smoke tests and say so.

Usage:
    uv run python scripts/play_cube.py cube-easy-0 --network interim --theta-full 180
    uv run python scripts/play_cube.py cube-easy-0 cube-easy-1 --suite training --jobs 2
    uv run python scripts/play_cube.py cube-easy-0 --bot      # bot drives, brain watches (D43)

Writes results/closed_loop/<network>/[<suite>/]<settings>/<driver>/<level>/ (the suite folder only
for held_out; settings end in `_flat` without `--rate-scaling`), a recorded run (`fly_log`):
the game's run log (replayable), brain.parquet, spikes.npz and run.json (git-ignored).
"""

import argparse
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
from stereo_flyness.experiments.cascades import load_stuck_state
from stereo_flyness.interface.closed_loop import play
from stereo_flyness.interface.encoding import CubeEncoder

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "closed_loop"


def one(name, suite, path_comp, path_con, patches, gf, stuck_ids, args, out, seed):
    from stereo_flyness.brain.stepper import BrainStepper

    level, bot = load_level(LEVELS, job(name, suite))
    enc = CubeEncoder(level, patches, args.theta_full, args.rate, args.mode, args.rate_scaling)
    st = BrainStepper(path_comp, path_con, inputs={"loom": enc.ids}, watch=gf, seed=seed)
    policy = None
    if args.bot:
        inputs = bot.tick_inputs
        policy = lambda game: inputs[game.ticks] if game.ticks < len(inputs) else False  # noqa: E731
    meta = {"suite": suite, "network": args.network, "seed": seed, "commit": git_commit(),
            "status": {"final": "D43 run", "whole_brain": "D43 run (whole brain, the reference network)"}.get(
                args.network, f"smoke test: {args.network} network (not the D43 baseline)")}
    rec = play(Game(level), st, enc, policy=policy, stuck_ids=stuck_ids, meta=meta)
    rec.save(out / rec.driver / name)
    return rec.summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("levels", nargs="+")
    parser.add_argument("--suite", default="training")
    parser.add_argument("--network", default="interim", help="subcircuit name, or whole_brain")
    parser.add_argument("--theta-full", type=float, default=180.0)
    parser.add_argument("--rate", type=float, default=150.0)
    parser.add_argument("--mode", default="collision", choices=["collision", "all"])
    parser.add_argument("--rate-scaling", action="store_true", help="driven neurons fire at R x f (D45)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--bot", action="store_true", help="the bot drives; the brain only watches (D43)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = tomllib.loads(CONFIG.read_text())
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    con = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
    patches = loom_patches(con, cells, cfg["probes"]["p5"]["seed"])  # P5's patch order (D41)
    gf = {"GF_R": cells.ids("DNp01", side="right"), "GF_L": cells.ids("DNp01", side="left")}
    path_comp, con_paths, _ = network(None if args.network == "whole_brain" else args.network)
    stuck_ids = load_stuck_state(ROOT / cfg["cascade"]["stuck_state"])  # restricted to the network (D38)
    # Held-out levels reuse training names (cube-easy-0, ...), so they get their own folder.
    base = OUT / args.network if args.suite == "training" else OUT / args.network / args.suite
    out = base / f"{args.theta_full:g}deg_{args.mode}_R{args.rate:g}{'' if args.rate_scaling else '_flat'}"
    summaries = Parallel(n_jobs=args.jobs)(
        delayed(one)(n, args.suite, path_comp, con_paths["original"], patches, gf, stuck_ids, args, out, args.seed)
        for n in args.levels)
    for s in summaries:
        end = "completed" if s["completed"] else f"died at {100 * s['progress']:.0f}% ({s['death_kind']} at x {s['death_x']:.0f})"
        stuck = "" if s["stuck_from_frame"] is None else f"; STUCK from frame {s['stuck_from_frame']}"
        print(f"{s['level']} [{s['driver']}-driven]: {end}; {s['jumps']} jumps, {s['presses']} presses in "
              f"{s['seconds']:.1f} s{stuck} [{s['status']}]")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
