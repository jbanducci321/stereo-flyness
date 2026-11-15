"""The ideal-fly reference ceiling: how far the encoding alone can get, with no brain.

The ideal fly presses on every tick after one where the nearest looming object's θ reaches a
fixed threshold (one tick late, as in D40/D42). At the calibration target (39°, D43) it is the
reference the real runs are read against: what a fly whose Giant Fiber fires exactly at 39°
would do with this encoding. Each death is classified (a) invisible to the encoding, (b)
visible, but the threshold is the wrong moment to jump, or (c) short run-up: the object was
already past the threshold when it started looming (D45).

`--sweep` also tries other fixed thresholds. That shows whether 39° is a fair ceiling or whether
another moment would clear more. It's a check, never a way to pick a threshold (D43 fixes 39°).

`--by-obstacle` (iteration 2, fix 2's threshold check; training levels only) also reports results
per obstacle type (spike1/2/3, stairs, platforms, slab hops, ...; experiments/obstacles.py):
- **in the levels:** how often each type is cleared when the cube reaches it, and how it killed;
- **in isolation:** each distinct obstacle shape alone after a full run-up, to show at which
  thresholds it can be cleared at all, whatever came before it.

Training levels by default. `--suite held_out` runs the 20 held-out cube levels, at 39° only and
with no sweep: it is run once, together with the Step 2 baseline (D44), and never before.

Usage:
    uv run python scripts/ideal_fly.py                       # the 10 recruitment levels (D43)
    uv run python scripts/ideal_fly.py --all --sweep 20 80 5 # all 50 cube training levels
    uv run python scripts/ideal_fly.py --all --sweep 10 175 5 --by-obstacle   # per obstacle type
    uv run python scripts/ideal_fly.py --suite held_out --quiet  # Step 2 only: the 20 held-out levels, blind

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
from stereo_flyness.experiments.obstacles import groups, isolated, outcomes, shape_key
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
                             "progress": round(r["progress"], 3), "death": r["death"], "death_x": r["death_x"],
                             "class": None if r["completed"] else ("a" if cause.startswith(INVISIBLE) else "c" if cause.startswith(SHORT_RUN_UP) else "b"),
                             "cause": r["cause"]})
    return pd.DataFrame(rows)


def per_group(df: pd.DataFrame, suite: str = "training") -> pd.DataFrame:
    """Each run's outcome at each obstacle group of its level (from the runs already made)."""
    rows = []
    for name, runs in df.groupby("level"):
        level, _ = load_level(LEVELS, job(name, suite))
        gs = groups(level)
        for r in runs.to_dict("records"):
            death_x = None if pd.isna(r["death_x"]) else r["death_x"]
            for i, (g, out) in enumerate(zip(gs, outcomes(gs, r["completed"], death_x))):
                rows.append({"level": name, "group": i, "type": g.type, "mode": r["mode"],
                             "threshold": r["threshold"], "outcome": out,
                             "class": r["class"] if out == "died" else None})
    return pd.DataFrame(rows)


def alone(names, thresholds, modes, suite="training") -> pd.DataFrame:
    """Every distinct obstacle shape in the levels, alone after a full run-up, at each threshold."""
    shapes = {}
    for name in names:
        level, _ = load_level(LEVELS, job(name, suite))
        for g in groups(level):
            key = shape_key(g)
            if key in shapes:
                shapes[key][1] += 1
            else:
                shapes[key] = [g, 1]
    rows = []
    for i, (g, count) in enumerate(shapes.values()):
        lone = isolated(g)
        for mode in modes:
            enc = CubeEncoder(lone, NO_PATCHES, 180.0, 150.0, mode)
            for th in thresholds:
                rows.append({"shape": i, "type": g.type, "occurrences": count, "mode": mode,
                             "threshold": th, "cleared": threshold_fly(enc, lone, th)["completed"]})
    return pd.DataFrame(rows)


def _ranges(values) -> str:
    """Sorted thresholds as compact ranges, e.g. 35-50, 60."""
    vals = sorted(values)
    if not vals:
        return "never"
    step = float(np.median(np.diff(vals))) if len(vals) > 1 else 0  # the sweep's step (39° sits inside it)
    out, start, prev = [], vals[0], vals[0]
    for v in vals[1:]:
        if v - prev > step + 1e-9:
            out.append(f"{start:g}" if start == prev else f"{start:g}-{prev:g}")
            start = v
        prev = v
    out.append(f"{start:g}" if start == prev else f"{start:g}-{prev:g}")
    return ", ".join(out)


def obstacle_report(pg: pd.DataFrame, lone: pd.DataFrame, thresholds) -> list[str]:
    lines = ["", "## By obstacle type (iteration 2, fix 2's threshold check)\n",
             f"**In the levels, at {THRESHOLD_DEG:g}°:** of the times the cube reached each type, how often it "
             "cleared it, and how it died there ((a) invisible, (b) wrong moment, (c) short run-up). "
             "A death at one obstacle ends the run, so later obstacles go unreached.\n"]
    at = pg[(pg["threshold"] == THRESHOLD_DEG) & (pg["outcome"] != "not reached")]
    rows = []
    for (mode, typ), d in at.groupby(["mode", "type"]):
        died = d[d["outcome"] == "died"]
        rows.append({"mode": mode, "type": typ, "reached": len(d),
                     "cleared": int((d["outcome"] == "cleared").sum()),
                     "died (a/b/c)": "/".join(str(int((died["class"] == c).sum())) for c in "abc")})
    lines.append(md_table(pd.DataFrame(rows), 0))
    lines += ["", "**In isolation:** each distinct shape alone after a 600-unit run-up: the thresholds at "
              "which **every** shape of that type is cleared, and at which **at least one** is.\n"]
    rows = []
    for (mode, typ), d in lone.groupby(["mode", "type"]):
        per_th = d.groupby("threshold")["cleared"].agg(["all", "any"])
        rows.append({"mode": mode, "type": typ, "shapes": d["shape"].nunique(),
                     "in levels": int(d.drop_duplicates("shape")["occurrences"].sum()),
                     f"all at {THRESHOLD_DEG:g}°": "yes" if per_th.loc[THRESHOLD_DEG, "all"] else "no",
                     "all cleared at": _ranges(per_th.index[per_th["all"]]),
                     "some cleared at": _ranges(per_th.index[per_th["any"]])})
    lines.append(md_table(pd.DataFrame(rows), 0))
    lines.append(f"\nThresholds tried: {_ranges(thresholds)}°. A check of the encoding's limits, not a way "
                 "to choose a threshold (D43 fixes 39°).")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="all 50 cube training levels, not just the 10")
    parser.add_argument("--sweep", type=float, nargs=3, metavar=("FROM", "TO", "STEP"),
                        help="also try these fixed thresholds (degrees)")
    parser.add_argument("--suite", default="training", choices=["training", "held_out"],
                        help="held_out: Step 2 only, all 20 cube levels at 39° (D44)")
    parser.add_argument("--quiet", action="store_true", help="blind runs (D48, D33): write the files, show nothing")
    parser.add_argument("--by-obstacle", action="store_true",
                        help="also report results per obstacle type, in the levels and in isolation (training only)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.suite == "held_out" and args.sweep:
        sys.exit("No threshold sweep on the held-out suite: it's run at 39 degrees only, with the Step 2 baseline (D44).")
    if args.suite == "held_out" and args.by_obstacle:
        sys.exit("No per-obstacle check on the held-out suite: it's for designing fixes, on training levels only.")

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
        tag = (("all50" if args.all else "recruitment10") + ("_sweep" if args.sweep else "")
               + ("_obstacles" if args.by_obstacle else ""))
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
    if args.by_obstacle:
        pg = per_group(df.drop(columns="difficulty"), args.suite)
        lone = alone(names, thresholds, ["collision", "all"], args.suite)
        pg.to_csv(OUT / f"{tag}_groups.csv", index=False)
        lone.to_csv(OUT / f"{tag}_isolated.csv", index=False)
        lines += obstacle_report(pg, lone, thresholds)
    (OUT / f"{tag}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {(OUT / tag).relative_to(ROOT)}.csv and .md (outcomes not shown: --quiet)" if args.quiet
          else "\n".join(lines))


if __name__ == "__main__":
    main()
