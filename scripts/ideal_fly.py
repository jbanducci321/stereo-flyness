"""The ideal-fly reference ceiling: how far the encoding alone can get, with no brain.

The ideal fly presses on every tick after one where the nearest looming object's θ reaches a
fixed threshold (one tick late, as in D40/D42). At the calibration target (39°, D43) it is the
reference the real runs are read against: what a fly whose Giant Fiber fires exactly at 39°
would do with this encoding. Each death is classified (a) invisible to the encoding, (b)
visible, but the threshold is the wrong moment to jump, or (c) short run-up: the object was
already past the threshold when it started looming (D45).

`--sweep` also tries other fixed thresholds. That shows whether 39° is a fair ceiling or whether
another moment would clear more. It's a check, never a way to pick a threshold (D43 fixes 39°).

Training levels by default. `--suite held_out` runs the 20 held-out cube levels, at 39° only and
with no sweep: it is run once, together with the Step 2 baseline (D44), and never before.

Usage:
    uv run python scripts/ideal_fly.py                       # the 10 recruitment levels (D43)
    uv run python scripts/ideal_fly.py --all --sweep 20 80 5 # all 50 cube training levels
    uv run python scripts/ideal_fly.py --suite held_out      # Step 2 only: the 20 held-out levels

Writes results/ideal_fly/<name>.csv and .md (git-ignored).
"""

import argparse
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from analyse_pathway_tests import md_table
from inspect_encoding import INVISIBLE, LEVELS, SHORT_RUN_UP, THRESHOLD_DEG, job, threshold_fly
from stereo_flyness.game.suites import load_level
from stereo_flyness.interface.encoding import SIDES, TYPES, CubeEncoder

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "ideal_fly"
NO_PATCHES = {s: {t: [] for t in TYPES} for s in SIDES}  # θ doesn't depend on the patches


def run(names, thresholds, modes, suite="training") -> pd.DataFrame:
    rows = []
    for name in names:
        level, _ = load_level(LEVELS, job(name, suite))
        for mode in modes:
            enc = CubeEncoder(level, NO_PATCHES, 180.0, 150.0, mode)
            for th in thresholds:
                r = threshold_fly(enc, level, th)
                cause = r["cause"] or ""
                rows.append({"level": name, "mode": mode, "threshold": th, "completed": r["completed"],
                             "progress": round(r["progress"], 3), "death": r["death"],
                             "class": None if r["completed"] else ("a" if cause.startswith(INVISIBLE) else "c" if cause.startswith(SHORT_RUN_UP) else "b"),
                             "cause": r["cause"]})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="all 50 cube training levels, not just the 10")
    parser.add_argument("--sweep", type=float, nargs=3, metavar=("FROM", "TO", "STEP"),
                        help="also try these fixed thresholds (degrees)")
    parser.add_argument("--suite", default="training", choices=["training", "held_out"],
                        help="held_out: Step 2 only, all 20 cube levels at 39° (D44)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.suite == "held_out" and args.sweep:
        sys.exit("No threshold sweep on the held-out suite: it's run at 39 degrees only, with the Step 2 baseline (D44).")

    if args.all or args.suite == "held_out":
        names = sorted(p.stem for p in (LEVELS / args.suite).glob("cube-*.json") if not p.stem.endswith(".meta"))
    else:
        names = tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())["levels"]
    thresholds = [THRESHOLD_DEG]
    if args.sweep:
        a, b, step = args.sweep
        thresholds = sorted(set(thresholds) | set(np.round(np.arange(a, b + step / 2, step), 3)))
    df = run(names, thresholds, ["collision", "all"], args.suite)
    if args.suite == "held_out":
        tag = f"held_out{len(names)}"
    else:
        tag = ("all50" if args.all else "recruitment10") + ("_sweep" if args.sweep else "")
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"{tag}.csv", index=False)

    df["difficulty"] = df["level"].str.split("-").str[1]
    at = df[df["threshold"] == THRESHOLD_DEG]
    lines = [f"# Ideal {THRESHOLD_DEG:g}° fly: reference ceiling ({len(names)} cube {args.suite.replace('_', '-')} levels)\n",
             f"No brain: presses whenever θ ≥ {THRESHOLD_DEG:g}°, one tick late. Not a model result.\n",
             "## Levels completed\n"]
    done = at.pivot_table(index="difficulty", columns="mode", values="completed", aggfunc="sum")
    total = at[at["mode"] == "collision"].groupby("difficulty").size()
    for d in ("easy", "medium", "hard"):
        if d in total:
            lines.append(f"- {d}: collision {int(done.loc[d, 'collision'])}/{total[d]}, "
                         f"every object looms {int(done.loc[d, 'all'])}/{total[d]}")
    lines += ["", "## Deaths\n"]
    deaths = at[~at["completed"]]
    for mode in ("collision", "all"):
        dm = deaths[deaths["mode"] == mode]
        lines.append(f"- {mode}: {len(dm)} deaths, (a) invisible {int((dm['class'] == 'a').sum())}, "
                     f"(b) wrong moment {int((dm['class'] == 'b').sum())}, "
                     f"(c) short run-up {int((dm['class'] == 'c').sum())}")
    lines += ["", md_table(deaths[["level", "mode", "progress", "cause"]], 2)]
    if args.sweep:
        lines += ["", "## Threshold sweep (check only; 39° is fixed by D43)\n"]
        sw = df.pivot_table(index="threshold", columns="mode", values="completed", aggfunc="sum").reset_index()
        lines.append(md_table(sw, 0))
        best = df[df["completed"]].groupby(["mode", "level"]).size().reset_index()[["mode", "level"]]
        lines.append(f"\nLevels completed at **some** threshold: collision "
                     f"{int((best['mode'] == 'collision').sum())}/{len(names)}, all "
                     f"{int((best['mode'] == 'all').sum())}/{len(names)}.")
    (OUT / f"{tag}.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
