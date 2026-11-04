"""Step 3 report: the tuning grid scored by the rule fixed before the runs (configs/step3.toml).

Per rate: levels completed by difficulty, mean progress (the score), D48's death classes (so it
shows where any gain comes from; R can't change (a) deaths), stuck runs, and the open-loop check
(`step3_grid.py check`): where that rate makes the Giant Fiber first fire and in how many
trials, flagged if outside the fly's 39° ± 14°.

The pick (stereo_flyness.experiments.tuning.pick_rate) needs every rate's 50 runs, the
tie-margin run (`step3_grid.py margin`) and, for a tie, the open-loop check; otherwise nothing is
picked. The tie margin is max(1 point, the seed 0 vs seed 1 difference at the default rate).

`--held-out R`: the held-out check at the picked rate, against the Step 2 baseline at the same
seeds: per level, each setting's median run across seeds, compared by D48's "equal", then the
sign test. Blind (D33): it writes the files and shows nothing.

Usage:
    uv run python scripts/step3_report.py
    uv run python scripts/step3_report.py --held-out 75

Writes results/step3/grid.md and grid.csv, or held_out.md and held_out.csv (git-ignored).
"""

import argparse
import json
import sys

import pandas as pd

from inspect_encoding import LEVELS, job
from run_pathway_tests import ROOT
from step2_report import CARRY_OVER_MS, read_run
from step3_grid import TAG, config, levels
from stereo_flyness.experiments.step2_analysis import CLASSES, compare, sign_test
from stereo_flyness.experiments.tuning import OpenLoop, pick_rate, tie_margin
from stereo_flyness.game.suites import load_level

RUNS = ROOT / "results" / "closed_loop"
CALIBRATION = ROOT / "results" / "calibration"
OUT = ROOT / "results" / "step3"
DIFFICULTIES = ("easy", "medium", "hard")


def folder(cfg, rate, seed, suite="training", tag=TAG):
    """play_cube.py's folder for one rate and seed (Step 3 runs are tagged; Step 2's aren't)."""
    base = RUNS / cfg["network"] if suite == "training" else RUNS / cfg["network"] / suite
    return base / f"{cfg['theta_full_deg']:g}deg_collision_R{rate:g}{'' if seed == 0 else f'_seed{seed}'}{tag}" / "fly"


def collect(cfg, runs, suite="training", tag=TAG) -> pd.DataFrame:
    """Every recorded run of `runs` [(rate, seed)], replayed and classified as in Step 2."""
    rows = []
    for rate, seed in runs:
        for name in levels(suite):
            d = folder(cfg, rate, seed, suite, tag) / name
            if not (d / "run.json").exists():
                continue
            if json.loads((d / "run.json").read_text(encoding="utf-8")).get("seed") != seed:
                raise ValueError(f"{d} isn't a seed-{seed} run")
            level, _ = load_level(LEVELS, job(name, suite))
            row, appr = read_run(d, level, "collision")
            spiked = appr[appr["first_spike_theta"].notna()]
            carry = spiked["since_gf_ms"] < CARRY_OVER_MS  # a burst carrying over (D48 amendment)
            rows.append({"rate": rate, "seed": seed, "level": name, "difficulty": name.split("-")[1], **row,
                         "spiked": len(spiked), "carry_over": int(carry.sum()),
                         "fresh_theta_sum": float(spiked[~carry]["first_spike_theta"].sum())})
    return pd.DataFrame(rows)


def open_loop(cfg, rate) -> OpenLoop | None:
    """First-spike θ on the calibration loom at this rate (`step3_grid.py check`), or None if not run."""
    f = CALIBRATION / cfg["network"] / f"gap{cfg['check_start_gap']:g}_R{rate:g}_scaled{TAG}" / "results.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    d = d[d["theta_full"] == cfg["theta_full_deg"]]
    if d.empty:
        return None
    fired = d["first_spike_theta"].dropna()
    return OpenLoop(float(fired.mean()) if len(fired) else None, len(fired), len(d))


def open_loop_text(cfg, o: OpenLoop | None) -> tuple[str, str]:
    if o is None:
        return "not run", "–"
    if o.mean_theta is None:
        return f"never fired (0 of {o.trials})", "**yes**"
    lo, hi = cfg["fly_threshold_deg"]
    text = f"{o.mean_theta:.1f}° ({o.fired} of {o.trials} fired)"
    return text, "**yes**" if not lo <= o.mean_theta <= hi else "no"


def carry_text(g) -> str:
    """Share of approaches whose first Giant Fiber spike is a burst carried over from the previous
    object, and the mean first-spike θ without them (D48 amendment; D49 framing)."""
    spiked, carry = g["spiked"].sum(), g["carry_over"].sum()
    fresh = spiked - carry
    share = f"{carry / spiked:.0%} of {int(spiked)}" if spiked else "–"
    return f"{share} | " + (f"{g['fresh_theta_sum'].sum() / fresh:.1f}°" if fresh else "–")


def report(df, margin_runs, cfg) -> str:
    n_levels = len(levels(cfg["suite"]))
    lo, hi = cfg["fly_threshold_deg"]
    default = cfg["default_rate_hz"]
    grid = df[df["seed"] == cfg["seed"]] if len(df) else df
    lines = [f"# Step 3: tuning R on {n_levels} cube {cfg['suite']} levels (`{cfg['network']}`)\n",
             f"Fly-driven closed loop, collision course, R × f, θ_full = {cfg['theta_full_deg']:g}° (not revisited), "
             f"seed {cfg['seed']}. Score: mean progress. Ties (within the measured margin) go to the rate whose "
             "open-loop first Giant Fiber spike is closest to 39°; a rate where fewer than half the trials fire "
             "ranks last. Fixed before the runs.\n",
             "| R (Hz) | Levels run | " + " | ".join(DIFFICULTIES) + " | Completed | **Mean progress** | Deaths "
             + " / ".join(f"({c})" for c in CLASSES) + " | Stuck runs | Carry-over | First-spike θ without carry-over | Open loop: first-spike θ (trials fired) | "
             f"Outside {lo:g}–{hi:g}°? |",
             "|---|---|" + "---|" * len(DIFFICULTIES) + "---|---|---|---|---|---|---|---|"]
    scores, ol, complete = {}, {}, True
    for rate in cfg["rates_hz"]:
        g = grid[grid["rate"] == rate] if len(grid) else grid
        o = open_loop(cfg, rate)
        if o is not None:
            ol[rate] = o
        theta, flag = open_loop_text(cfg, o)
        if g.empty:
            complete = False
            lines.append(f"| {rate:g} | 0/{n_levels} | " + " | ".join("–" for _ in DIFFICULTIES)
                         + f" | – | – | – | – | – | – | {theta} | {flag} |")
            continue
        complete &= len(g) == n_levels
        cells = [f"{int(gd['completed'].sum())}/{len(gd)}" for d in DIFFICULTIES for gd in [g[g["difficulty"] == d]]]
        dead = g[~g["completed"].astype(bool)]
        classes = " / ".join(str(int((dead["class"] == c).sum())) for c in CLASSES)
        scores[rate] = g["progress"].mean()
        lines.append(f"| {rate:g} | {len(g)}/{n_levels} | " + " | ".join(cells) + f" | {int(g['completed'].sum())} | "
                     f"**{100 * scores[rate]:.1f}%** | {classes} | {int(g['stuck'].sum())} | {carry_text(g)} | {theta} | {flag} |")
    lines += ["", "(s) stuck; from the last approach where the cube could still jump: (c) short run-up; the ideal 39° "
              "fly dies there too, (a) on something that never loomed in its game, (b) on something that did; or the "
              "fly's timing: (d1) jumped earlier than the ideal fly, (d2) later, (d3) not at all; (u) unclassified (D48). "
              "(a), (b) and (c) are limits of the encoding; R works through (d). Carry-over: approaches whose first "
              f"Giant Fiber spike came < {CARRY_OVER_MS} ms after the previous one (a burst carrying over from the "
              "previous object), with first-spike θ given without them (D48 amendment).", ""]

    m = margin_runs
    if len(m) == n_levels and default in scores and len(grid[grid["rate"] == default]) == n_levels:
        margin = tie_margin(scores[default], m["progress"].mean(), cfg["tie_margin_floor"])
        lines.append(f"**Tie margin: {100 * margin:.1f} points** = max({100 * cfg['tie_margin_floor']:g} point, "
                     f"|{100 * scores[default]:.1f}% at seed {cfg['seed']} − {100 * m['progress'].mean():.1f}% at seed "
                     f"{cfg['margin_seed']}|, both at {default:g} Hz).\n")
    else:
        margin = None
        lines.append(f"**Tie margin not measured yet:** needs the seed-{cfg['margin_seed']} run at {default:g} Hz "
                     f"({len(m)}/{n_levels} levels) and the grid's {default:g} Hz run.\n")
    if not complete or margin is None:
        lines.append("**Incomplete: no rate is picked.**")
        return "\n".join(lines)
    best = max(scores.values())
    tied = [r for r, s in scores.items() if s >= best - margin - 1e-12]
    if len(tied) > 1 and any(r not in ol for r in tied):
        lines.append(f"**Tied ({', '.join(f'{r:g}' for r in sorted(tied))} Hz), and the open-loop check hasn't been "
                     "run at every tied rate: no rate is picked.**")
        return "\n".join(lines)
    winner, tied = pick_rate(scores, ol, default, margin)
    theta, flag = open_loop_text(cfg, ol.get(winner))
    lines.append(f"**Picked: R = {winner:g} Hz**, mean progress {100 * scores[winner]:.1f}%; at this rate the Giant "
                 f"Fiber first fires at **{theta}** on the calibration loom (the fly: 39 ± 14°)."
                 + (f" Tied: {', '.join(f'{r:g}' for r in tied)} Hz." if len(tied) > 1 else ""))
    if winner == default:
        lines.append("\nThe untuned default wins: tuning didn't help, and the held-out run isn't repeated.")
    elif winner in (min(cfg["rates_hz"]), max(cfg["rates_hz"])):
        lines.append("\nThe winner is at the edge of the range, which isn't widened (D43).")
    if flag == "**yes**":
        lines.append(f"\n**Flag:** at this rate the Giant Fiber first fires outside the fly's {lo:g}–{hi:g}° on the "
                     "calibration loom: \"the tuned fly jumps outside the range measured in real flies\".")
    if winner < default:
        lines.append("\n**For the write-up:** below 150 Hz the fly jumps later than it was calibrated to. Part of any "
                     "gain may make up for slabs not looming (D47), so it isn't simply the fly getting better.")
    commits = sorted(df["commit"].dropna().unique())
    if len(commits) > 1:
        lines.append(f"\nNote: these runs were recorded at {len(commits)} commits: {', '.join(c[:7] for c in commits)}.")
    return "\n".join(lines)


def median_runs(df) -> dict:
    """Per level, the run with the median progress across seeds (an actual run, so it has a killing object)."""
    out = {}
    for name, g in df.groupby("level"):
        g = g.sort_values(["progress", "seed"]).reset_index(drop=True)
        out[name] = g.iloc[(len(g) - 1) // 2].to_dict()
    return out


def held_out(cfg, rate, training_score) -> str:
    seeds = cfg["held_out_seeds"]
    tuned = collect(cfg, [(rate, s) for s in seeds], "held_out")
    untuned = collect(cfg, [(cfg["default_rate_hz"], s) for s in seeds], "held_out", tag="")
    n = len(levels("held_out"))
    lines = [f"# Step 3: the held-out check at R = {rate:g} Hz\n",
             f"Tuned (R = {rate:g} Hz) against the Step 2 baseline (R = {cfg['default_rate_hz']:g} Hz), both at seeds "
             f"{', '.join(map(str, seeds))} on the {n} held-out cube levels. Per level, each setting's median run across "
             "seeds; equal = both completed or both died on the same object (D48); two-sided sign test, equal levels "
             "left out, \"better\" only at p < 0.05.\n",
             f"- Runs read: tuned {len(tuned)}/{n * len(seeds)}, untuned {len(untuned)}/{n * len(seeds)}."]
    if len(tuned) < n * len(seeds) or len(untuned) < n * len(seeds):
        return "\n".join(lines + ["", "**Incomplete: nothing is compared.**"])
    t, u = median_runs(tuned), median_runs(untuned)
    signs = {lv: compare(t[lv], u[lv]) for lv in t}
    better, worse, equal = (sum(1 for s in signs.values() if s == v) for v in (1, -1, 0))
    p = sign_test(better, worse)
    diff = sum(t[lv]["progress"] - u[lv]["progress"] for lv in t) / n
    reading = "better" if p < 0.05 and better > worse else "worse" if p < 0.05 else "no clear difference"
    lines += [f"- **Better {better}, worse {worse}, equal {equal}; sign test p = {p:.3f}: {reading}.**",
              f"- Paired difference in median progress, tuned − untuned: {100 * diff:+.1f} points.",
              f"- Runs completed: tuned {int(tuned['completed'].sum())}/{len(tuned)}, "
              f"untuned {int(untuned['completed'].sum())}/{len(untuned)}.",
              f"- Mean progress at R = {rate:g} Hz: training {100 * training_score:.1f}%, held-out "
              f"{100 * tuned['progress'].mean():.1f}% (so overfitting to the training levels shows).", "",
              "| level | tuned (median) | untuned (median) | |", "|---|---|---|---|"]
    mark = {1: "better", -1: "worse", 0: "equal"}
    for lv in sorted(t):
        cell = lambda r: f"{100 * r['progress']:.0f}%" + ("" if r["completed"] else f" ({r['class']})")  # noqa: E731
        lines.append(f"| {lv} | {cell(t[lv])} | {cell(u[lv])} | {mark[signs[lv]]} |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--held-out", type=float, metavar="R", help="the held-out check at the picked rate (blind)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = config()
    OUT.mkdir(parents=True, exist_ok=True)
    df = collect(cfg, [(r, cfg["seed"]) for r in cfg["rates_hz"]] + [(cfg["default_rate_hz"], cfg["margin_seed"])])
    if args.held_out is not None:
        grid = df[(df["rate"] == args.held_out) & (df["seed"] == cfg["seed"])] if len(df) else df
        if len(grid) != len(levels(cfg["suite"])):
            sys.exit(f"R = {args.held_out:g} Hz doesn't have its full training run.")
        text = held_out(cfg, args.held_out, grid["progress"].mean())
        (OUT / "held_out.md").write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {(OUT / 'held_out.md').relative_to(ROOT)} (outcomes not shown: blind, D33)")
        return
    margin_runs = df[(df["seed"] == cfg["margin_seed"]) & (df["rate"] == cfg["default_rate_hz"])] if len(df) else df
    text = report(df, margin_runs, cfg)
    df.to_csv(OUT / "grid.csv", index=False)
    (OUT / "grid.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
