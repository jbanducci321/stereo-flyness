"""The two no-brain references for Step 2 (D48): never press (the floor), and random presses (chance).

- **Never press:** the cube runs each level without ever jumping. How far it gets is the floor.
- **Random presses:** each tick is a press with probability p, where p is the baseline's presses
  per tick on that level, its seeds pooled (D48). 10 draws per level, with fixed seeds. If the fly
  doesn't beat this, its timing isn't doing anything.

Both are deterministic and need no brain. The random references read only the baseline's press
counts (ticks.parquet), so the baseline runs must be finished first. Nothing is printed but the
file written: the Step 2 report shows the results (D33).

Usage (Step 2, after the baseline's held-out runs):
    uv run python scripts/reference_flies.py
    uv run python scripts/reference_flies.py --suite training --seeds 0 --levels cube-easy-4 cube-easy-5   # a check

Writes results/references/<network>_<suite>.csv (git-ignored).
"""

import argparse
import sys
import tomllib
import zlib

import numpy as np
import pandas as pd

from inspect_encoding import LEVELS, job
from run_pathway_tests import ROOT
from stereo_flyness.game.engine import Game
from stereo_flyness.game.suites import load_level

RUNS = ROOT / "results" / "closed_loop"
OUT = ROOT / "results" / "references"
DRAWS = 10  # D48


def baseline_folder(network, suite, seed):
    """play_cube.py's folder for the Step 2 baseline of record at one seed."""
    tf = tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())["theta_full_deg"]
    base = RUNS / network if suite == "training" else RUNS / network / suite
    return base / f"{tf:g}deg_collision_R150{'' if seed == 0 else f'_seed{seed}'}" / "fly"


def press_rate(network, suite, seeds, name) -> float:
    """The baseline's presses per tick on one level, its seeds pooled."""
    held = ticks = 0
    for seed in seeds:
        f = baseline_folder(network, suite, seed) / name / "ticks.parquet"
        if not f.exists():
            sys.exit(f"Missing baseline run {f.parent}. Run the Step 2 baseline first (D48).")
        t = pd.read_parquet(f, columns=["held"])
        held, ticks = held + int(t["held"].sum()), ticks + len(t)
    return held / ticks


def play(level, press) -> dict:
    """One game where `press(game)` decides, after each tick, whether the next tick is held."""
    game, held = Game(level), False
    while not game.over:
        game.tick(held)
        held = game.player.mode == "cube" and press(game)
    d = game.death
    return {"completed": game.finished, "progress": game.progress, "ticks": game.ticks,
            "death": None if d is None else f"{d.kind} at x {d.x:.0f}"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--network", default="final")
    parser.add_argument("--suite", default="held_out", choices=["held_out", "training"])
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2], help="the baseline seeds to pool (D48)")
    parser.add_argument("--levels", nargs="+", help="default: every cube level of the suite")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    names = args.levels or sorted(p.stem for p in (LEVELS / args.suite).glob("cube-*.json")
                                  if not p.stem.endswith(".meta"))
    rows = []
    for name in names:
        level, _ = load_level(LEVELS, job(name, args.suite))
        rows.append({"level": name, "reference": "never press", "draw": None, "p": 0.0,
                     **play(level, lambda game: False)})
        p = press_rate(args.network, args.suite, args.seeds, name)
        for draw in range(DRAWS):
            rng = np.random.default_rng([draw, zlib.crc32(name.encode())])  # fixed per level and draw
            rows.append({"level": name, "reference": "random presses", "draw": draw, "p": p,
                         **play(level, lambda game: rng.random() < p)})
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{args.network}_{args.suite}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Wrote {out.relative_to(ROOT)} ({len(rows)} runs; outcomes shown only in the Step 2 report)")


if __name__ == "__main__":
    main()
