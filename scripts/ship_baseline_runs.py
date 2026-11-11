"""The ship baseline runs (Step 5, D53, docs/notes/ship_analysis_plan.md): one batch per design.

Each batch is the 20 held-out ship levels × seeds 0, 1, 2 (60 runs), whole brain, original signs,
R_ship = 150 Hz, through scripts/play_level.py with `--quiet` (blind, D33: only progress and stuck
flags are printed). Designs: `B` (the design of record), `C` (its control) and `B90` (the 90°/s
faster-anchor variant). Run one batch per night; nothing is opened until all are done and the
report's checks pass.

Before a batch starts, this checks that the tree is clean (every run records its commit, and a
`-dirty` run can't be reported) and that the open-loop gate passed (check 1: zero input gives
0 DNp22 spikes, `scripts/ship_open_loop.py`).

Usage:
    uv run python scripts/ship_baseline_runs.py B --dry-run     # print the commands only
    uv run python scripts/ship_baseline_runs.py B               # tonight's batch
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ROOT / "results" / "levels" / "held_out"
GATE = ROOT / "results" / "ship_open_loop" / "summary.md"
DESIGNS = ("B", "C", "B90")
SEEDS = (0, 1, 2)


def held_out_ship_levels() -> list[str]:
    return sorted(p.stem for p in LEVELS.glob("ship-*.json") if not p.stem.endswith(".meta"))


def commands(design: str, jobs: int) -> list[list[str]]:
    names = held_out_ship_levels()
    if len(names) != 20:
        sys.exit(f"Expected 20 held-out ship levels, found {len(names)}.")
    return [["uv", "run", "python", "-u", "scripts/play_level.py", *names, "--suite", "held_out",
             "--network", "whole_brain", "--ship", design, "--ship-rate", "150", "--seed", str(seed),
             "--jobs", str(jobs), "--quiet"] for seed in SEEDS]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("design", choices=DESIGNS)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cmds = commands(args.design, args.jobs)
    if args.dry_run:
        for c in cmds:
            print(" ".join(c[:5]), "<20 held-out ship levels>", " ".join(c[25:]))
        return
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        sys.exit("Refused: the tree has uncommitted changes, so every run would be -dirty. Commit first.")
    if not GATE.exists() or "(the gate)" not in (text := GATE.read_text(encoding="utf-8")) or "PASS" not in text.split("(the gate)")[1].split("\n")[0]:
        sys.exit("Refused: the open-loop gate (check 1) hasn't passed. Run scripts/ship_open_loop.py first.")
    for i, c in enumerate(cmds, 1):
        print(f"== {args.design} seed {SEEDS[i - 1]} ({i}/{len(cmds)})", flush=True)
        if subprocess.run(c, cwd=ROOT).returncode:
            sys.exit(f"Stopped: seed {SEEDS[i - 1]} failed.")
    print(f"{args.design}: all {len(cmds) * 20} runs done (outcomes not shown: blind).")


if __name__ == "__main__":
    main()
