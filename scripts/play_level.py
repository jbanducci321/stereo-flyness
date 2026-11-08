"""The fly plays any level in closed loop, switching controllers at portals (Steps 5-6).

`play_cube.py` stays the runner of record for cube levels (Steps 2-4). This one plays cube, ship
and mixed levels, and Stereo Madness, through `interface/modes.py`: one controller per mode, each
with its own input encoding and output rule. The cube's is D41-D47's, unchanged. The ship's is
Shannyn's design (Step 5); until it's logged in `SHIP_CONTROLLERS`, a level with any ship section
is refused **before** the brain is built, so no part of a ship or mixed level, and no part of
Stereo Madness, is ever played without it.

Stereo Madness is the held-out final test (D7, hard rule 5):
- it only runs with `--stereo-madness-final`, after its N, seeds and settings are fixed (Step 6);
- it's always blind (D33): only progress and stuck flags are printed, never an outcome;
- it writes to its own folder, results/stereo_madness/.

Every frame is logged for the replay viewer, with the mode the fly was shown (hard rule 10).

Usage:
    uv run python scripts/play_level.py cube-easy-4 --network final          # any training level
    uv run python scripts/play_level.py mixed-easy-0 ship-easy-0 --network final --ship <design>
    uv run python scripts/play_level.py mixed-easy-1000000 --suite held_out --quiet --ship <design>
    uv run python scripts/play_level.py stereo_madness --stereo-madness-final --ship <design> --seed 0

Writes results/closed_loop/<network>/[<suite>/]<settings>/<driver>/<level>/ (as play_cube.py), or
results/stereo_madness/<network>/<settings>/<driver>/stereo_madness/. Settings: θ_full, encoding
mode and R as play_cube.py, then `_ship-<design>`, then `_seed<n>`, then any `--tag`.
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
from stereo_flyness.brain.controls import file_sha256
from stereo_flyness.experiments.cascades import load_stuck_state
from stereo_flyness.experiments.pathway_tests import loom_patches
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level
from stereo_flyness.game.suites import load_level
from stereo_flyness.interface.encoding import CubeEncoder
from stereo_flyness.interface.modes import CubeController, ShipNotDesigned, play_modes

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "closed_loop"
SM_OUT = ROOT / "results" / "stereo_madness"
SM_NAME = "stereo_madness"
SM_LEVEL = ROOT / "data" / "gd" / "stereo_madness.json"

# The ship's encoding and output rule, by design name (Step 5). Each entry builds a Controller from
# (level, cells, args). Only designs logged in docs/decisions.md go here.
SHIP_CONTROLLERS: dict = {}


def modes_of(level: Level) -> set[str]:
    return {mode for mode, *_ in level.sections()}


def get_level(name, suite) -> Level:
    return Level.load(SM_LEVEL) if name == SM_NAME else load_level(LEVELS, job(name, suite))[0]


def refuse(args, levels: dict[str, Level]) -> str | None:
    """Why these runs can't start, or None. Checked before any brain is built."""
    if SM_NAME in levels:
        if not args.stereo_madness_final:
            return ("Stereo Madness is the held-out final test (D7, hard rule 5). It only runs with "
                    "--stereo-madness-final, once Step 6 has fixed its N, seeds and settings.")
        if len(levels) > 1:
            return "Run Stereo Madness on its own, not alongside other levels."
        if args.bot:
            return "Stereo Madness here is the fly's test; the bot's run is scripts/bot_stereo_madness.py."
    ship = [n for n, lv in levels.items() if "ship" in modes_of(lv)]
    if ship and args.ship is None:
        return (f"{', '.join(ship)} {'has' if len(ship) == 1 else 'have'} ship sections, and the ship's encoding "
                f"and output rule aren't designed yet (Step 5, docs/notes/ship_brief.md). Pass --ship <design> "
                f"once it's logged{'; known designs: ' + ', '.join(SHIP_CONTROLLERS) if SHIP_CONTROLLERS else ''}.")
    if args.ship is not None and args.ship not in SHIP_CONTROLLERS:
        return f"Unknown ship design {args.ship!r}. Known: {', '.join(SHIP_CONTROLLERS) or 'none yet'}."
    return None


def controllers_for(level, cells, patches, gf, args) -> dict:
    out = {}
    if "cube" in modes_of(level):
        enc = CubeEncoder(level, patches, args.theta_full, args.rate, args.mode, args.rate_scaling)
        out["cube"] = CubeController(enc, gf)
    if "ship" in modes_of(level):
        out["ship"] = ShipNotDesigned() if args.ship is None else SHIP_CONTROLLERS[args.ship](level, cells, args)
    return out


def one(name, level, path_comp, path_con, cells, patches, gf, stuck_ids, args, out, extra):
    from stereo_flyness.brain.stepper import BrainStepper

    ctrl = controllers_for(level, cells, patches, gf, args)
    inputs = {g: ids for c in ctrl.values() for g, ids in c.groups.items()}
    watch = {g: ids for c in ctrl.values() for g, ids in c.watch.items()}
    st = BrainStepper(path_comp, path_con, inputs=inputs, watch=watch, seed=args.seed)
    policy = None
    if args.bot:
        frames = load_level(LEVELS, job(name, args.suite))[1].tick_inputs
        policy = lambda game: frames[game.ticks] if game.ticks < len(frames) else False  # noqa: E731
    meta = {"suite": "stereo_madness" if name == SM_NAME else args.suite, "network": args.network, "seed": args.seed,
            "commit": git_commit(), "ship_design": args.ship, **extra}
    rec = play_modes(Game(level), st, ctrl, policy=policy, stuck_ids=stuck_ids, meta=meta)
    rec.save(out / rec.driver / name)
    return rec.summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("levels", nargs="+", help=f"level names in --suite, or {SM_NAME}")
    parser.add_argument("--suite", default="training")
    parser.add_argument("--network", default="final", help="subcircuit name, or whole_brain")
    parser.add_argument("--theta-full", type=float, default=None, help="default: configs/recruitment.toml (D43)")
    parser.add_argument("--rate", type=float, default=150.0, help="R, Hz (D50: 150 is the fly of record)")
    parser.add_argument("--mode", default="collision", choices=["collision", "all"])
    parser.add_argument("--flat", dest="rate_scaling", action="store_false", help="flat R instead of R x f (D45)")
    parser.add_argument("--ship", default=None, help="the ship design (Step 5), as named in SHIP_CONTROLLERS")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--bot", action="store_true", help="the bot drives; the brain only watches")
    parser.add_argument("--tag", default="")
    parser.add_argument("--quiet", action="store_true", help="blind (D33): progress and stuck flags only")
    parser.add_argument("--stereo-madness-final", action="store_true",
                        help="allow Stereo Madness (Step 6 only, once its runs are fixed)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = tomllib.loads(CONFIG.read_text())
    if args.theta_full is None:
        args.theta_full = tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())["theta_full_deg"]

    levels = {n: get_level(n, args.suite) for n in args.levels}
    why = refuse(args, levels)
    if why:
        sys.exit(f"Refused, nothing run: {why}")
    sm = SM_NAME in levels
    quiet = args.quiet or sm or args.suite == "held_out" and not args.bot

    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    con = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
    patches = loom_patches(con, cells, cfg["probes"]["p5"]["seed"])  # P5's patch order (D41)
    gf = {"GF_R": cells.ids("DNp01", side="right"), "GF_L": cells.ids("DNp01", side="left")}
    path_comp, con_paths, _ = network(None if args.network == "whole_brain" else args.network)
    stuck_ids = load_stuck_state(ROOT / cfg["cascade"]["stuck_state"])  # restricted to the network (D38)
    status = {"final": "subcircuit (D46)", "whole_brain": "whole brain"}.get(args.network, f"{args.network} network")
    base = (SM_OUT / args.network if sm else OUT / args.network if args.suite == "training"
            else OUT / args.network / args.suite)
    out = base / (f"{args.theta_full:g}deg_{args.mode}_R{args.rate:g}{'' if args.rate_scaling else '_flat'}"
                  f"{'' if args.ship is None else f'_ship-{args.ship}'}"
                  f"{'' if args.seed == 0 else f'_seed{args.seed}'}{args.tag}")
    path_con = con_paths["original"]
    extra = {"status": status + (", Stereo Madness final test" if sm else ""),
             "connectome": {"file": path_con.name, "sha256": file_sha256(path_con)}}
    runs = Parallel(n_jobs=args.jobs, return_as="generator_unordered")(
        delayed(one)(n, lv, path_comp, path_con, cells, patches, gf, stuck_ids, args, out, extra)
        for n, lv in levels.items())
    summaries = []
    for i, s in enumerate(runs, 1):
        summaries.append(s)
        if quiet:  # the stuck flag is the one live check allowed (D48)
            flag = "" if s["stuck_from_frame"] is None else f"; STUCK from frame {s['stuck_from_frame']}"
            print(f"run {i}/{len(levels)} done{flag}", flush=True)
    if quiet:
        print(f"Wrote {out.relative_to(ROOT)} (outcomes not shown: blind)")
        return
    for s in sorted(summaries, key=lambda s: args.levels.index(s["level"])):
        end = "completed" if s["completed"] else f"died at {100 * s['progress']:.0f}% ({s['death_kind']} at x {s['death_x']:.0f})"
        print(f"{s['level']} [{s['driver']}-driven, modes {', '.join(s['modes'])}]: {end}; {s['presses']} presses in "
              f"{s['seconds']:.1f} s")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
