"""Stereo Madness's report (Step 6; docs/notes/step6_proposal.md §4 and §6), per variant in
configs/stereo_madness.toml:
- **Checks first:** every run present, fly-driven with the variant's settings and seed, on the right
  connectome; every run replays exactly from its logged holds; one clean commit; stuck runs counted.
  If any check fails for a variant, nothing of it is reported.
- **Results:** completed (k of N), and median, quartiles and range of progress (the headline is the
  count and the median, never the best run); per run, where it ended (cube or ship section, and
  the killing object) and the ship sections reached and passed.
- **The showcase replay,** picked by the rule fixed before the runs: progress closest to the median,
  ties to the lowest seed.
- **Context only:** the bot's run (scripts/bot_stereo_madness.py), if it's been made.

Order: the record first; the 50 Hz variant second (D50); corrected signs alongside (D28). Blind
(D33): only the checks are printed; the rest goes to results/stereo_madness/report.md.

Usage:
    uv run python scripts/stereo_madness_report.py
"""

import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from ship_baseline_report import death_object
from stereo_flyness.experiments.ship_analysis import replay_run
from stereo_flyness.experiments.stereo_madness import showcase, spread, where
from stereo_flyness.game.level import Level

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "stereo_madness.toml"
LEVEL = ROOT / "data" / "gd" / "stereo_madness.json"
OUT = ROOT / "results" / "stereo_madness"
BOT = ROOT / "results" / "runs" / "bot_stereo_madness" / "summary.json"
CONNECTOME = {"original": "Connectivity_783.parquet", "corrected": "Connectivity_783_T4T5corrected.parquet"}


def folder(cfg, v, seed) -> Path:
    theta = tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())["theta_full_deg"]
    var = cfg["variants"][v]
    rs = "" if cfg["ship_rate_hz"] == 150 else f"_Rs{cfg['ship_rate_hz']:g}"
    return (OUT / cfg["network"] / (f"{theta:g}deg_collision_R{var['rate_hz']:g}_ship-{cfg['ship_design']}{rs}"
            f"{'' if var['signs'] == 'original' else '_' + var['signs']}{'' if seed == 0 else f'_seed{seed}'}")
            / "fly" / "stereo_madness")


def collect(cfg, v, level):
    var, rows, problems = cfg["variants"][v], [], []
    for seed in cfg["seeds"]:
        d = folder(cfg, v, seed)
        if not (d / "run.json").exists():
            problems.append(f"seed {seed} missing")
            continue
        run = json.loads((d / "run.json").read_text(encoding="utf-8"))
        modes = run.get("modes", {})
        if run.get("driver") != "fly" or run.get("seed") != seed or run.get("ship_design") != cfg["ship_design"] \
                or modes.get("ship", {}).get("ship_rate_hz") != cfg["ship_rate_hz"] \
                or modes.get("cube", {}).get("rate_hz") != var["rate_hz"] or run.get("signs", "original") != var["signs"] \
                or run.get("connectome", {}).get("file") != CONNECTOME[var["signs"]]:
            problems.append(f"seed {seed} has the wrong settings")
            continue
        held = pd.read_parquet(d / "ticks.parquet")["held"].to_numpy(bool)
        try:
            game = replay_run(level, held, run)
        except ValueError as e:
            problems.append(str(e))
            continue
        x = level.length if run["completed"] else float(run.get("death_x") or game.player.x)
        rows.append({"variant": v, "seed": seed, "completed": run["completed"], "progress": run["progress"],
                     "stuck": run.get("stuck_from_frame") is not None, "commit": run.get("commit", ""),
                     "death_object": death_object(level, game), **where(level, x, run["completed"])})
    return pd.DataFrame(rows), problems


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    level = Level.load(LEVEL)  # read only now, after the runs (hard rule 5)
    lines = [f"# Stereo Madness, the final test ({cfg.get('decision') or 'decision not logged'})", "",
             f"Whole brain, ship {cfg['ship_design']} at {cfg['ship_rate_hz']:g} Hz, seeds {cfg['seeds'][0]}-{cfg['seeds'][-1]}. "
             "The headline is the count and the median, never the best run.", ""]
    printed, frames = [], []
    for v in cfg["variants"]:
        df, problems = collect(cfg, v, level)
        need = len(cfg["seeds"])
        commits = sorted(df["commit"].unique()) if len(df) else []
        dirty = [c for c in commits if c.endswith("-dirty")]
        var = cfg["variants"][v]
        check = [f"## {v}: cube R {var['rate_hz']:g} Hz, {var['signs']} signs", "",
                 f"- Runs (need {need}): {len(df)}" + (" — all complete" if len(df) == need else " — **INCOMPLETE**"),
                 "- Every run replayed exactly from its logged holds; settings and connectome as configured.",
                 f"- Commits: {', '.join(c[:7] for c in commits) or '–'}"
                 + (" — **some runs are -dirty**" if dirty else "") + (" — **more than one commit**" if len(commits) > 1 else ""),
                 f"- Stuck runs: {int(df['stuck'].sum()) if len(df) else 0}"]
        check += [f"- **Problem:** {p}" for p in problems[:10]] + [""]
        printed += check
        lines += check
        if len(df) != need or problems or dirty or len(commits) > 1:
            lines += ["**Checks failed for this variant: nothing of it is reported.**", ""]
            continue
        s = spread(df.to_dict("records"))
        pick = showcase(df.to_dict("records"))
        lines += [f"**Completed {s['completed']} of {s['runs']}; median progress {100 * s['median']:.1f}%** "
                  f"(quartiles {100 * s['q1']:.1f}–{100 * s['q3']:.1f}%, range {100 * s['min']:.1f}–{100 * s['max']:.1f}%).", "",
                  "| Seed | Completed | Progress | Ended in | Killing object | Ship sections reached / passed | Stuck |",
                  "|---|---|---|---|---|---|---|"]
        for r in df.sort_values("seed").to_dict("records"):
            lines.append(f"| {r['seed']} | {'yes' if r['completed'] else 'no'} | {100 * r['progress']:.1f}% | "
                         f"{r['ended_in'] or '–'} | {r['death_object'] or '–'} | "
                         f"{r['ship_reached']} / {r['ship_passed']} of {r['ship_sections']} | {'yes' if r['stuck'] else ''} |")
        dead = df[~df["completed"]]
        lines += ["", f"- **Deaths by section:** cube {int((dead['ended_mode'] == 'cube').sum())}, "
                      f"ship {int((dead['ended_mode'] == 'ship').sum())}.",
                  f"- **Showcase replay** (closest to the median, ties to the lowest seed; fixed before the runs): "
                  f"seed {pick['seed']}, {100 * pick['progress']:.1f}%.", ""]
        frames.append(df)
    if BOT.exists():
        bot = json.loads(BOT.read_text(encoding="utf-8"))
        lines += ["## Context only: the bot", "",
                  f"The search bot's run (`bot_stereo_madness.py`): completed {bot.get('completed')}. "
                  "It shows the level is playable in our engine, not what a fly should do.", ""]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(OUT / "runs.csv", index=False)
    print("\n".join(printed))
    print(f"Wrote report.md and runs.csv to {OUT} (outcomes not shown: blind, D33)")


if __name__ == "__main__":
    main()
