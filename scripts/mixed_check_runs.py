"""The mixed-level check's runs (Step 6, docs/notes/step6_proposal.md §5 step 2): before Stereo Madness,
the first fly-driven runs that switch between cube and ship at portals.

The 20 held-out mixed levels × seeds 0, 1, 2 (60 runs), on Stereo Madness's record settings: whole
brain, original signs, the cube as D41-D47 at R = 150 Hz (D50), the ship as D53's B at R_ship =
150 Hz. Through scripts/play_level.py with `--quiet` (blind, D33) and `--resume` (after a killed batch,
the same command plays only what's missing at this commit).

Refuses a dirty tree (every run records its commit) or a ship open-loop gate that hasn't passed.

Usage:
    uv run python scripts/mixed_check_runs.py --dry-run
    uv run python scripts/mixed_check_runs.py
"""

import argparse
import subprocess
import sys
from pathlib import Path

from ship_baseline_runs import GATES, gate_passed

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ROOT / "results" / "levels" / "held_out"
SEEDS = (0, 1, 2)


def held_out_mixed_levels() -> list[str]:
    return sorted(p.stem for p in LEVELS.glob("mixed-*.json") if not p.stem.endswith(".meta"))


def commands(jobs: int) -> list[list[str]]:
    names = held_out_mixed_levels()
    if len(names) != 20:
        sys.exit(f"Expected 20 held-out mixed levels, found {len(names)}.")
    return [["uv", "run", "python", "-u", "scripts/play_level.py", *names, "--suite", "held_out",
             "--network", "whole_brain", "--rate", "150", "--ship", "B", "--ship-rate", "150",
             "--signs", "original", "--seed", str(seed), "--jobs", str(jobs), "--quiet", "--resume"]
            for seed in SEEDS]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cmds = commands(args.jobs)
    if args.dry_run:
        for c in cmds:
            print(" ".join(c[:5]), "<20 held-out mixed levels>", " ".join(c[25:]))
        return
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        sys.exit("Refused: the tree has uncommitted changes, so every run would be -dirty. Commit first.")
    if not gate_passed(GATES["original"]):
        sys.exit("Refused: the ship open-loop gate hasn't passed. Run scripts/ship_open_loop.py first.")
    for i, c in enumerate(cmds, 1):
        print(f"== mixed seed {SEEDS[i - 1]} ({i}/{len(cmds)})", flush=True)
        if subprocess.run(c, cwd=ROOT).returncode:
            sys.exit(f"Stopped: seed {SEEDS[i - 1]} failed. Run the same command again to resume.")
    print(f"Mixed check: all {len(cmds) * 20} runs done (outcomes not shown: blind).")


if __name__ == "__main__":
    main()
