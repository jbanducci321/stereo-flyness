"""Step 3 report: the tuning grid scored by the rule fixed before the runs (configs/step3.toml).

Per rate: levels completed by difficulty, mean progress (the score), stuck runs, and, if the
open-loop check has been run (`step3_grid.py check`), where that rate makes the Giant Fiber first
fire, flagged if outside the fly's 39° ± 14°. The winner is picked by
stereo_flyness.experiments.tuning.pick_rate only when every rate has all its levels; otherwise
the report says it's incomplete and picks nothing.

Usage:
    uv run python scripts/step3_report.py

Writes results/step3/grid.md and grid.csv (git-ignored).
"""

import argparse
import json
import math
import sys

import pandas as pd

from run_pathway_tests import ROOT
from step3_grid import TAG, config, levels
from stereo_flyness.experiments.tuning import pick_rate

RUNS = ROOT / "results" / "closed_loop"
CALIBRATION = ROOT / "results" / "calibration"
OUT = ROOT / "results" / "step3"
DIFFICULTIES = ("easy", "medium", "hard")


def folder(cfg, rate):
    """play_cube.py's folder for one grid rate (training runs have no suite folder; Step 3 runs are tagged)."""
    return RUNS / cfg["network"] / f"{cfg['theta_full_deg']:g}deg_collision_R{rate:g}{TAG}" / "fly"


def collect(cfg) -> pd.DataFrame:
    rows = []
    for rate in cfg["rates_hz"]:
        for name in levels(cfg["suite"]):
            d = folder(cfg, rate) / name
            if not (d / "summary.json").exists():
                continue
            run = json.loads((d / "run.json").read_text(encoding="utf-8"))
            s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
            if run.get("driver") != "fly" or run.get("seed") != cfg["seed"]:
                raise ValueError(f"{d} isn't a fly-driven seed-{cfg['seed']} run")
            rows.append({"rate": rate, "level": name, "difficulty": name.split("-")[1], "completed": s["completed"],
                         "progress": s["progress"], "jumps": s["jumps"],
                         "stuck": run.get("stuck_from_frame") is not None, "commit": run.get("commit")})
    return pd.DataFrame(rows)


def open_loop(cfg, rate) -> tuple[str, bool | None]:
    """First-spike θ on the calibration loom at this rate, and whether it's outside the fly's band."""
    f = CALIBRATION / cfg["network"] / f"gap{cfg['check_start_gap']:g}_R{rate:g}_scaled{TAG}" / "results.csv"
    if not f.exists():
        return "not run", None
    d = pd.read_csv(f)
    d = d[d["theta_full"] == cfg["theta_full_deg"]]
    if d.empty:
        return "not run", None
    fired = d["first_spike_theta"].dropna()
    if fired.empty:
        return f"never fired (0/{len(d)})", True
    lo, hi = cfg["fly_threshold_deg"]
    mean = fired.mean()
    return f"{mean:.1f} ± {fired.std():.1f}° ({len(fired)}/{len(d)} fired)", not lo <= mean <= hi


def report(df, cfg) -> str:
    n_levels = len(levels(cfg["suite"]))
    lo, hi = cfg["fly_threshold_deg"]
    lines = [f"# Step 3: tuning R on {n_levels} cube {cfg['suite']} levels (`{cfg['network']}`)\n",
             f"Fly-driven closed loop, collision course, R × f, θ_full = {cfg['theta_full_deg']:g}° (not revisited), "
             f"seed {cfg['seed']}. Score: mean progress. Ties (within {100 * cfg['tie_margin']:g} percentage point of "
             f"the best) go to the rate closest to {cfg['default_rate_hz']:g} Hz on a log scale. Fixed before the runs.\n",
             "| R (Hz) | Levels run | " + " | ".join(DIFFICULTIES) + " | Completed | **Mean progress** | Stuck runs | "
             f"Open loop: first Giant Fiber spike θ | Outside {lo:g}–{hi:g}°? |",
             "|---|---|" + "---|" * len(DIFFICULTIES) + "---|---|---|---|---|"]
    scores, complete = {}, True
    for rate in cfg["rates_hz"]:
        g = df[df["rate"] == rate] if len(df) else df
        theta, outside = open_loop(cfg, rate)
        flag = "–" if outside is None else ("**yes**" if outside else "no")
        if g.empty:
            complete = False
            lines.append(f"| {rate:g} | 0/{n_levels} | " + " | ".join("–" for _ in DIFFICULTIES)
                         + f" | – | – | – | {theta} | {flag} |")
            continue
        complete &= len(g) == n_levels
        cells = [f"{int(gd['completed'].sum())}/{len(gd)}" for d in DIFFICULTIES for gd in [g[g["difficulty"] == d]]]
        scores[rate] = g["progress"].mean()
        lines.append(f"| {rate:g} | {len(g)}/{n_levels} | " + " | ".join(cells) + f" | {int(g['completed'].sum())} | "
                     f"**{100 * scores[rate]:.1f}%** | {int(g['stuck'].sum())} | {theta} | {flag} |")
    lines.append("")
    if not complete:
        lines.append("**Incomplete: not every rate has all its levels, so no rate is picked.**")
    else:
        winner, tied = pick_rate(scores, cfg["default_rate_hz"], cfg["tie_margin"])
        lines.append(f"**Picked: R = {winner:g} Hz** (mean progress {100 * scores[winner]:.1f}%)."
                     + (f" Tied: {', '.join(f'{r:g}' for r in tied)} Hz." if len(tied) > 1 else ""))
        if winner == cfg["default_rate_hz"]:
            lines.append("\nThe untuned default wins: tuning didn't help, and the held-out run isn't repeated.")
        elif winner in (min(cfg["rates_hz"]), max(cfg["rates_hz"])):
            lines.append("\nThe winner is at the edge of the range, which isn't widened (D43).")
        if open_loop(cfg, winner)[1]:
            lines.append(f"\n**Flag:** at this rate the Giant Fiber first fires outside the fly's {lo:g}–{hi:g}° "
                         "on the calibration loom.")
    commits = sorted(df["commit"].dropna().unique()) if len(df) else []
    if len(commits) > 1:
        lines.append(f"\nNote: these runs were recorded at {len(commits)} commits: {', '.join(c[:7] for c in commits)}.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = config()
    df = collect(cfg)
    text = report(df, cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "grid.csv", index=False)
    (OUT / "grid.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
