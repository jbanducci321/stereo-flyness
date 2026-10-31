"""Calibrate θ_full to the fly's 39° escape threshold (D43), open loop.

For each θ_full, the cube runs at game speed straight at one spike and never jumps (the brain
only watches: runs are labelled bot-driven). θ at the Giant Fiber's first spike is recorded per
trial. The calibrated θ_full is where the mean crosses 39°.

D43's official calibration runs on the whole brain at R = 150 Hz. Runs on a subcircuit are dry
runs and are labelled as such.

`--rate-scaling` uses the proposed R x f rates (2026-10-31). Several `--start-gap` values can be
run at once. The report then checks the encoding against the bar agreed before the dry run:
θ_full <= 360°, s.d. of the first-spike θ at the calibrated θ_full <= 28° (2 x the fly's), and
a shift in the first-spike θ of < 5° between start gaps 600 and 1,200.

Usage:
    uv run python scripts/calibrate_theta_full.py --network interim --trials 5          # dry run
    uv run python scripts/calibrate_theta_full.py --network interim --rate-scaling \\
        --start-gap 600 1200 270 --grid 45 90 180 360 720 1440 --trials 10            # R x f dry run
    uv run python scripts/calibrate_theta_full.py --network whole_brain --trials 10     # official

Writes results/calibration/<network>/gap<gap>_R<R>[_scaled]/ (git-ignored): one recorded run
per θ_full x trial, results.csv and report.md, plus checks_R<R>[_scaled].md for several gaps.
"""

import argparse
import math
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from find_target_neurons import fetch_annotations
from reproduce_sugar import PATH_COMP, PATH_CON
from run_pathway_tests import CONFIG, git_commit, network
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.experiments.cascades import load_stuck_state
from stereo_flyness.experiments.pathway_tests import loom_patches
from stereo_flyness.game.engine import Game
from stereo_flyness.interface.calibration import TARGET_DEG, approach_level, crossing, first_spike_theta
from stereo_flyness.interface.closed_loop import play
from stereo_flyness.interface.encoding import CubeEncoder

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "calibration"
GRID = [180, 360, 720, 1440, 2880, 5760, 11520]
# The bar agreed before the R x f dry run (2026-10-31)
CHECKS = {"max_theta_full": 360.0, "max_sd": 28.0, "max_shift": 5.0, "shift_gaps": (600.0, 1200.0)}


def trial(theta_full, t, gap, path_comp, path_con, patches, gf, stuck_ids, args, out):
    from stereo_flyness.brain.stepper import BrainStepper

    level = approach_level(gap)
    enc = CubeEncoder(level, patches, theta_full, args.rate, rate_scaling=args.rate_scaling)
    seed = 1000 * t + int(theta_full)  # fixed per (θ_full, trial)
    st = BrainStepper(path_comp, path_con, inputs={"loom": enc.ids}, watch=gf, seed=seed)
    meta = {"network": args.network, "seed": seed, "commit": git_commit(), "purpose": "theta_full calibration (D43)",
            "status": "official" if args.network == "whole_brain" else "dry run (subcircuit)"}
    rec = play(Game(level), st, enc, policy=lambda g: False, stuck_ids=stuck_ids, meta=meta)
    rec.save(out / f"{theta_full:g}deg" / f"trial_{t:02d}")
    theta = first_spike_theta(rec.brain)
    hit = None if theta is None else rec.brain.loc[(rec.brain["spikes_GF_R"] + rec.brain["spikes_GF_L"]) > 0].iloc[0]
    return {"start_gap": gap, "theta_full": theta_full, "trial": t, "first_spike_theta": theta,
            "gap_at_spike": None if hit is None else hit["gap"],
            "driven_at_spike": None if hit is None else int(sum(hit[c] for c in rec.brain.columns if c.startswith("driven_"))),
            "stuck": rec.stuck_from is not None}


def at(theta_full: float, grid, values) -> float:
    """`values` (one per grid point) at `theta_full`, interpolated linearly in log θ_full."""
    pts = [(g, v) for g, v in zip(grid, values) if not math.isnan(v)]
    return float(np.interp(math.log(theta_full), [math.log(g) for g, _ in pts], [v for _, v in pts]))


def report(df, gap, patches, args) -> tuple[list[str], float | None, float | None]:
    """The report for one start gap: its lines, the calibrated θ_full, and the s.d. there."""
    per = df.groupby("theta_full").agg(
        mean=("first_spike_theta", "mean"), sd=("first_spike_theta", "std"),
        fired=("first_spike_theta", lambda s: int(s.notna().sum())), trials=("trial", "size"),
        mean_gap=("gap_at_spike", "mean"), driven=("driven_at_spike", "median"), stuck=("stuck", "sum")).reset_index()
    cal = crossing(list(per["theta_full"]), list(per["mean"]))
    total = sum(len(patches[s][t]) for s in patches for t in patches[s])
    status = "OFFICIAL (whole brain)" if args.network == "whole_brain" else "DRY RUN (subcircuit; not the D43 calibration)"
    rates = "R x f (rate scaling)" if args.rate_scaling else "R for every driven neuron"
    lines = [f"# θ_full calibration: {status}\n",
             f"Network `{args.network}`, R = {args.rate:g} Hz, {rates}, the spike starts {gap:g} units ahead of the "
             f"eye, {args.trials} trials per θ_full. Target: first Giant Fiber spike at θ = {TARGET_DEG:g}°. "
             f"Open loop: the cube never jumps (runs labelled bot-driven).\n",
             "| θ_full (°) | first-spike θ, mean ± s.d. (°) | trials that fired | gap at spike (units) | neurons driven at spike (of "
             f"{total}) | stuck |", "|---|---|---|---|---|---|"]
    for r in per.itertuples():
        m = "none" if math.isnan(r.mean) else f"{r.mean:.1f} ± {0 if math.isnan(r.sd) else r.sd:.1f}"
        lines.append(f"| {r.theta_full:g} | {m} | {r.fired}/{r.trials} | "
                     f"{'–' if math.isnan(r.mean_gap) else f'{r.mean_gap:.0f}'} | "
                     f"{'–' if math.isnan(r.driven) else f'{r.driven:.0f}'} | {r.stuck} |")
    if cal is None:
        lines.append(f"\n**No crossing of {TARGET_DEG:g}° in this grid.** Extend `--grid`.")
        return lines, None, None
    sd = at(cal, list(per["theta_full"]), list(per["sd"])) if per["sd"].notna().any() else math.nan  # needs 2+ trials
    f = TARGET_DEG / cal
    n = {f"{s} {t}": int(round(f * len(patches[s][t]))) for s in patches for t in patches[s]}
    lines += [f"\n**Calibrated θ_full ≈ {cal:,.0f}°** (log-interpolated), s.d. there ≈ {sd:.1f}°. At θ = "
              f"{TARGET_DEG:g}° that drives f = {f:.4f} of each population: " + ", ".join(f"{k} {v}" for k, v in n.items())
              + f" ({sum(n.values())} of {total} neurons)"
              + (f", each at {args.rate * f:.1f} Hz." if args.rate_scaling else ".")]
    return lines, cal, sd


def checks(results, args) -> None:
    """The bar agreed before the dry run, judged at the first start gap's calibrated θ_full."""
    g0 = args.start_gap[0]
    _, cal, sd = results[g0]
    lines = [f"# Encoding checks ({'R x f' if args.rate_scaling else 'flat R'}, network `{args.network}`)\n",
             f"Judged at the calibrated θ_full from start gap {g0:g}. Bar agreed before the run (2026-10-31).\n"]
    if cal is None:
        lines.append("No calibrated θ_full at the first gap: extend the grid.")
    else:
        mean_at = {}
        for g, (d, _, _) in results.items():
            per = d.groupby("theta_full")["first_spike_theta"].mean()
            mean_at[g] = at(cal, list(per.index), list(per.values))
        lines += [f"- θ_full ≈ {cal:,.0f}° (bar ≤ {CHECKS['max_theta_full']:g}°): "
                  f"**{'pass' if cal <= CHECKS['max_theta_full'] else 'fail'}**",
                  f"- s.d. at the calibrated value ≈ {sd:.1f}° (bar ≤ {CHECKS['max_sd']:g}°): "
                  f"**{'needs 2+ trials' if math.isnan(sd) else 'pass' if sd <= CHECKS['max_sd'] else 'fail'}**"]
        a, b = CHECKS["shift_gaps"]
        if a in mean_at and b in mean_at:
            shift = abs(mean_at[a] - mean_at[b])
            lines.append(f"- first-spike θ at gap {a:g} vs {b:g}: {mean_at[a]:.1f}° vs {mean_at[b]:.1f}°, shift "
                         f"{shift:.1f}° (bar < {CHECKS['max_shift']:g}°): "
                         f"**{'pass' if shift < CHECKS['max_shift'] else 'fail'}**")
        else:
            lines.append(f"- gap shift: needs start gaps {a:g} and {b:g}")
        lines.append("- first-spike θ at that θ_full, per start gap: "
                     + ", ".join(f"{g:g} → {m:.1f}°" for g, m in mean_at.items()))
        for g, (_, c, _) in results.items():
            lines.append(f"- calibrated θ_full from gap {g:g} alone: " + ("none in grid" if c is None else f"{c:,.0f}°"))
    out = OUT / args.network / f"checks_R{args.rate:g}{'_scaled' if args.rate_scaling else ''}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--network", default="interim", help="subcircuit name, or whole_brain")
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--rate", type=float, default=150.0)
    parser.add_argument("--start-gap", type=float, nargs="+", default=[600.0],
                        help="units from the eye to the spike at the start (several allowed)")
    parser.add_argument("--grid", type=float, nargs="+", default=GRID, help="θ_full values, degrees")
    parser.add_argument("--rate-scaling", action="store_true", help="driven neurons fire at R x f (proposed)")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = tomllib.loads(CONFIG.read_text())
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    con = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
    patches = loom_patches(con, cells, cfg["probes"]["p5"]["seed"])
    gf = {"GF_R": cells.ids("DNp01", side="right"), "GF_L": cells.ids("DNp01", side="left")}
    stuck_ids = load_stuck_state(ROOT / cfg["cascade"]["stuck_state"])
    path_comp, con_paths, _ = network(None if args.network == "whole_brain" else args.network)
    tag = "_scaled" if args.rate_scaling else ""
    outs = {g: OUT / args.network / f"gap{g:g}_R{args.rate:g}{tag}" for g in args.start_gap}

    rows = Parallel(n_jobs=args.jobs)(
        delayed(trial)(tf, t, g, path_comp, con_paths["original"], patches, gf, stuck_ids, args, outs[g])
        for g in args.start_gap for tf in args.grid for t in range(args.trials))
    df = pd.DataFrame(rows)
    results = {}
    for g, out in outs.items():
        d = df[df["start_gap"] == g]
        d.to_csv(out / "results.csv", index=False)
        lines, cal, sd = report(d, g, patches, args)
        results[g] = (d, cal, sd)
        (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines) + "\n")
    if len(outs) > 1:
        checks(results, args)


if __name__ == "__main__":
    main()
