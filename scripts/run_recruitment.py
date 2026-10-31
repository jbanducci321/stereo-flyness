"""Whole-brain recruitment runs for the final subcircuit (Step 2.6, D43).

10 training cube levels x 7 encoding settings (configs/recruitment.toml), bot-driven: the cube
follows the bot's winning path while the brain watches, so every part of each level is seen.
Each run is recorded (`fly_log`) and labelled "bot". Finished runs are skipped, so an
interrupted batch resumes where it stopped.

Both calibrated θ_full values (R x f and the flat-rate comparison; D43, D45) must be logged in
the config or passed with --theta-full and --flat-theta-full.

Usage:
    uv run python scripts/run_recruitment.py --dry-run --theta-full 204 --flat-theta-full 1165  # list runs, estimate time
    uv run python scripts/run_recruitment.py --jobs 4                         # the overnight batch
    uv run python scripts/run_recruitment.py --network interim --theta-full 204 --flat-theta-full 1165 \\
        --levels cube-easy-0 --max-seconds 3                                  # quick smoke test

Writes results/recruitment/<network>/theta<θ_full>_flat<θ_full>/<setting>/<level>/ and manifest.csv.
"""

import argparse
import sys
import time
import tomllib
from pathlib import Path

import pandas as pd
from joblib import Parallel, delayed

from find_target_neurons import fetch_annotations
from inspect_encoding import LEVELS, job
from reproduce_sugar import PATH_COMP, PATH_CON
from run_pathway_tests import CONFIG as PATHWAY_CONFIG, git_commit, network
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.experiments.cascades import load_stuck_state
from stereo_flyness.experiments.pathway_tests import loom_patches
from stereo_flyness.experiments.recruitment import is_done, run_dir, run_seed, settings
from stereo_flyness.game.engine import Game
from stereo_flyness.game.physics import TICKS_PER_SECOND
from stereo_flyness.game.suites import load_level
from stereo_flyness.interface.closed_loop import play
from stereo_flyness.interface.encoding import CubeEncoder

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "recruitment.toml"
OUT = ROOT / "results" / "recruitment"
# Rough cost: whole brain ~24x slower than real time alone, about twice that with 4 at once
X_REAL_TIME = {"whole_brain": 24.0}


def one(level_name, setting, cfg, path_comp, path_con, patches, gf, stuck_ids, out, max_ticks, net_name):
    from stereo_flyness.brain.stepper import BrainStepper

    folder = run_dir(out, level_name, setting)
    if is_done(folder):
        return {"level": level_name, "setting": setting.name, "skipped": True}
    level, bot = load_level(LEVELS, job(level_name, cfg["suite"]))
    enc = CubeEncoder(level, patches, setting.theta_full_deg, setting.rate_hz, setting.mode, setting.rate_scaling)
    seed = run_seed(cfg["base_seed"], level_name, setting)
    st = BrainStepper(path_comp, path_con, inputs={"loom": enc.ids}, watch=gf, seed=seed)
    inputs = bot.tick_inputs
    policy = lambda g: inputs[g.ticks] if g.ticks < len(inputs) else False  # noqa: E731
    meta = {"purpose": "recruitment (D43)", "network": net_name, "setting": setting.name, "seed": seed,
            "commit": git_commit(), "suite": cfg["suite"]}
    t0 = time.perf_counter()
    rec = play(Game(level), st, enc, policy=policy, stuck_ids=stuck_ids, meta=meta, max_ticks=max_ticks)
    rec.summary["wall_s"] = round(time.perf_counter() - t0, 1)
    rec.save(folder)
    return {"level": level_name, "setting": setting.name, "skipped": False, "completed": rec.summary["completed"],
            "seconds": rec.summary["seconds"], "stuck_from_frame": rec.stuck_from,
            "backup_from_frame": rec.summary["backup_from_frame"], "wall_s": rec.summary["wall_s"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--theta-full", type=float, help="calibrated θ_full, R x f (overrides the config)")
    parser.add_argument("--flat-theta-full", type=float, help="calibrated θ_full, flat R (overrides the config)")
    parser.add_argument("--network", help="override the config's network (e.g. interim for a smoke test)")
    parser.add_argument("--levels", nargs="+", help="only these levels")
    parser.add_argument("--settings", nargs="+", help="only these settings, by name")
    parser.add_argument("--max-seconds", type=float, help="stop each run early (smoke tests only)")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = tomllib.loads(CONFIG.read_text())
    theta = args.theta_full or cfg["theta_full_deg"]
    flat = args.flat_theta_full or cfg["flat_theta_full_deg"]
    sets = settings(cfg, theta, flat)
    if args.settings:
        sets = [s for s in sets if s.name in args.settings]
    levels = args.levels or cfg["levels"]
    net_name = args.network or cfg["network"]
    smoke = args.max_seconds is not None or net_name != cfg["network"]
    out = OUT / (net_name + ("_smoke" if smoke else "")) / f"theta{theta:g}_flat{flat:g}"
    todo = [(lv, s) for s in sets for lv in levels if not is_done(run_dir(out, lv, s))]

    x = X_REAL_TIME.get(net_name, 9.0) * (2 if args.jobs > 1 else 1)
    secs = args.max_seconds or 30.0
    est_h = len(todo) * secs * x / max(1, args.jobs) / 3600
    print(f"{len(sets)} settings x {len(levels)} levels; {len(todo)} runs to do on {net_name} "
          f"(θ_full = {theta:g}° R x f, {flat:g}° flat), roughly {est_h:.1f} h with {args.jobs} at once.")
    for s in sets:
        print(f"  {s.name}: θ_full {s.theta_full_deg:g}°, R {s.rate_hz:g} Hz, {s.mode}, "
              f"{'R x f' if s.rate_scaling else 'flat R'}")
    if args.dry_run or not todo:
        return

    pcfg = tomllib.loads(PATHWAY_CONFIG.read_text())
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    con = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
    patches = loom_patches(con, cells, pcfg["probes"]["p5"]["seed"])
    gf = {"GF_R": cells.ids("DNp01", side="right"), "GF_L": cells.ids("DNp01", side="left")}
    stuck_ids = load_stuck_state(ROOT / pcfg["cascade"]["stuck_state"])
    path_comp, con_paths, _ = network(None if net_name == "whole_brain" else net_name)
    max_ticks = None if args.max_seconds is None else int(args.max_seconds * TICKS_PER_SECOND)

    rows = Parallel(n_jobs=args.jobs, verbose=5)(
        delayed(one)(lv, s, cfg, path_comp, con_paths["original"], patches, gf, stuck_ids, out, max_ticks, net_name)
        for lv, s in todo)
    manifest = out / "manifest.csv"
    old = pd.read_csv(manifest) if manifest.exists() else pd.DataFrame()
    new = pd.DataFrame([r for r in rows if not r["skipped"]])
    pd.concat([old, new], ignore_index=True).to_csv(manifest, index=False)
    stuck = new[new["stuck_from_frame"].notna()] if len(new) else new
    print(f"Done: {len(new)} runs; {len(stuck)} entered the stuck state (frames from the flag on are dropped "
          f"from recruitment). Wrote {manifest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
