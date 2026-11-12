"""The ship baseline runs (Step 5, D53, docs/notes/ship_analysis_plan.md): one batch per design.

Each batch is the 20 held-out ship levels × seeds 0, 1, 2 (60 runs), whole brain, R_ship = 150 Hz,
through scripts/play_level.py with `--quiet` (blind, D33: only progress and stuck flags are printed).
Designs, on the original signs: `B` (the design of record), `C` (its control) and `B90` (the
90°/s faster-anchor variant). Plus `B --signs corrected`: B on the T4/T5-corrected connectome (D53's
addition of 2026-11-11, D28's sensitivity check; batch 4, last). Run one batch per night; nothing is
opened until all are done and the report's checks pass.

Before a batch starts, this checks that the tree is clean (every run records its commit, and a
`-dirty` run can't be reported) and that the open-loop gate passed on the same connectome (check 1:
zero input gives 0 DNp22 spikes; `scripts/ship_open_loop.py [--signs corrected]`).

Runs use `--resume`: after a killed batch, running the same command again plays only what's
missing at this commit (and refuses runs from another commit).

Usage:
    uv run python scripts/ship_baseline_runs.py B --dry-run     # print the commands only
    uv run python scripts/ship_baseline_runs.py B               # tonight's batch
    uv run python scripts/ship_baseline_runs.py B --signs corrected   # batch 4
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ROOT / "results" / "levels" / "held_out"
GATES = {"original": ROOT / "results" / "ship_open_loop" / "summary.md",
         "corrected": ROOT / "results" / "ship_open_loop" / "summary_corrected.md"}
DESIGNS = ("B", "C", "B90")
SEEDS = (0, 1, 2)


def held_out_ship_levels() -> list[str]:
    return sorted(p.stem for p in LEVELS.glob("ship-*.json") if not p.stem.endswith(".meta"))


def commands(design: str, jobs: int, signs: str = "original") -> list[list[str]]:
    names = held_out_ship_levels()
    if len(names) != 20:
        sys.exit(f"Expected 20 held-out ship levels, found {len(names)}.")
    return [["uv", "run", "python", "-u", "scripts/play_level.py", *names, "--suite", "held_out",
             "--network", "whole_brain", "--ship", design, "--ship-rate", "150", "--signs", signs,
             "--seed", str(seed), "--jobs", str(jobs), "--quiet", "--resume"] for seed in SEEDS]


def gate_passed(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "(the gate)" in text and "PASS" in text.split("(the gate)")[1].splitlines()[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("design", choices=DESIGNS)
    ap.add_argument("--signs", default="original", choices=["original", "corrected"])
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.signs == "corrected" and args.design != "B":
        sys.exit("Refused: the corrected-signs batch is B only (D53's addition of 2026-11-11).")
    cmds = commands(args.design, args.jobs, args.signs)
    label = args.design + ("" if args.signs == "original" else f", {args.signs} signs")
    if args.dry_run:
        for c in cmds:
            print(" ".join(c[:5]), "<20 held-out ship levels>", " ".join(c[25:]))
        return
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        sys.exit("Refused: the tree has uncommitted changes, so every run would be -dirty. Commit first.")
    if not gate_passed(GATES[args.signs]):
        sys.exit(f"Refused: the open-loop gate (check 1, {args.signs} signs) hasn't passed. "
                 f"Run scripts/ship_open_loop.py --signs {args.signs} first.")
    for i, c in enumerate(cmds, 1):
        print(f"== {label} seed {SEEDS[i - 1]} ({i}/{len(cmds)})", flush=True)
        if subprocess.run(c, cwd=ROOT).returncode:
            sys.exit(f"Stopped: seed {SEEDS[i - 1]} failed.")
    print(f"{label}: all {len(cmds) * 20} runs done (outcomes not shown: blind).")


if __name__ == "__main__":
    main()
