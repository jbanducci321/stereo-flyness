"""The mixed-level check's report (Step 6): did the brain switch cleanly between cube and ship?

On the 20 mixed levels of a suite at seeds 0-2, whole brain, Stereo Madness's record settings
(scripts/mixed_check_runs.py):
- **Checks** (any failure means a switching bug to fix before Stereo Madness): every run present,
  fly-driven with the right settings and seed, replaying exactly from its logged holds, clean
  commits, stuck runs counted; and the **switching checks** (`experiments/mixed_check.py`): every
  tick's logged mode matches the replayed game, every press follows the shown mode's rule, every
  tick logs only its own mode's encoding.
- **Described:** each mode's input neurons' rate when shown and when not; levels and runs completed,
  progress, where runs died (cube or ship section); never press and always press, for context. Nothing
  here was predicted, so nothing is tested: this is a check, not a result.

Blind on held_out (D33): only the checks are printed; the rest goes to the files.

Usage:
    uv run python scripts/mixed_check_report.py                         # held_out
    uv run python scripts/mixed_check_report.py --suite training --seeds 0 --tag _mixsmoke \
        --levels mixed-easy-0 --driver bot --allow-dirty             # testing the report

Writes results/mixed_check/<suite>/report.md and runs.csv (git-ignored).
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from analyse_pathway_tests import md_table
from find_target_neurons import fetch_annotations
from inspect_encoding import LEVELS, job
from reproduce_sugar import PATH_COMP
from ship_baseline_report import death_object
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.experiments.mixed_check import (
    encoding_mismatches, input_rates, mode_mismatches, rule_mismatches)
from stereo_flyness.experiments.ship_analysis import replay_run
from stereo_flyness.experiments.step4_analysis import median_runs
from stereo_flyness.game.engine import Game
from stereo_flyness.game.suites import load_level
from stereo_flyness.interface.fly_log import load_fly_run

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results" / "closed_loop" / "whole_brain"
OUT = ROOT / "results" / "mixed_check"
DIFFICULTIES = ("easy", "medium", "hard")
SHIP_TYPES = ("T4c", "T4d", "T5c", "T5d")
# Input groups for the described table: label -> (the mode that drives them, cell types; None = the rest)
INPUT_GROUPS = {"cube: LC4": ("cube", ("LC4",)), "cube: LPLC2": ("cube", ("LPLC2",)), "ship: T4/T5 c, d": ("ship", SHIP_TYPES)}


def folder(suite, seed, tag, driver) -> Path:
    base = RUNS if suite == "training" else RUNS / suite
    return base / f"200deg_collision_R150_ship-B{'' if seed == 0 else f'_seed{seed}'}{tag}" / driver


def levels(suite) -> list[str]:
    return sorted((p.stem for p in (LEVELS / suite).glob("mixed-*.json") if not p.stem.endswith(".meta")),
                  key=lambda n: (DIFFICULTIES.index(n.split("-")[1]), int(n.split("-")[2])))


def play_constant(level, held: bool) -> dict:
    game = Game(level)
    while not game.over:
        game.tick(held)
    return {"completed": game.finished, "progress": game.progress}


def collect(args, names, type_ids):
    runs, problems, shown = [], [], {g: [] for g in INPUT_GROUPS}
    for seed in args.seeds:
        for name in names:
            d = folder(args.suite, seed, args.tag, args.driver) / name
            if not (d / "run.json").exists():
                problems.append(f"{name} seed {seed} missing")
                continue
            run = json.loads((d / "run.json").read_text(encoding="utf-8"))
            modes = run.get("modes", {})
            if run.get("driver") != args.driver or run.get("seed") != seed or run.get("ship_design") != "B" \
                    or modes.get("ship", {}).get("ship_rate_hz") != 150.0 or modes.get("cube", {}).get("rate_hz") != 150.0 \
                    or run.get("signs", "original") != "original":
                problems.append(f"{name} seed {seed} has the wrong settings")
                continue
            level, _ = load_level(LEVELS, job(name, args.suite))
            ticks = pd.read_parquet(d / "ticks.parquet")
            held = ticks["held"].to_numpy(bool)
            try:
                game = replay_run(level, held, run)
            except ValueError as e:
                problems.append(str(e))
                continue
            brain = pd.read_parquet(d / "brain.parquet")
            spikes = load_fly_run(d)["spikes"]
            stim = set(int(i) for i in spikes["stimulated"])
            for g, (mode, types) in INPUT_GROUPS.items():
                ids = sorted(stim & set().union(*(type_ids[t] for t in types)))
                shown[g].append(input_rates(spikes, brain["mode"].to_numpy(), {mode: ids})[mode])
            switches = int((brain["mode"].to_numpy()[1:] != brain["mode"].to_numpy()[:-1]).sum())
            runs.append({"level": name, "difficulty": name.split("-")[1], "seed": seed, "completed": run["completed"],
                         "progress": run["progress"], "death_mode": None if run["completed"] else game.player.mode,
                         "death_source_id": death_object(level, game), "stuck": run.get("stuck_from_frame") is not None,
                         "commit": run.get("commit", ""), "mode_switches": switches,
                         "mode_mismatches": mode_mismatches(level, held, brain), "rule_mismatches": rule_mismatches(brain),
                         "encoding_mismatches": encoding_mismatches(brain)})
    return pd.DataFrame(runs), problems, shown


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--suite", default="held_out", choices=["training", "held_out"])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--tag", default="")
    ap.add_argument("--levels", nargs="+", default=None, help="a subset (testing on training runs only)")
    ap.add_argument("--driver", default="fly", choices=["fly", "bot"], help="bot: testing on training runs only")
    ap.add_argument("--allow-dirty", action="store_true", help="training only")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.suite == "held_out" and (args.levels or args.allow_dirty or args.driver != "fly"):
        sys.exit("--levels, --driver bot and --allow-dirty are for testing on training runs only.")
    names = levels(args.suite)
    if args.levels:
        names = [n for n in names if n in args.levels]
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    type_ids = {t: set(int(i) for i in cells.ids(t)) for g in INPUT_GROUPS.values() for t in g[1]}
    df, problems, shown = collect(args, names, type_ids)

    need = len(names) * len(args.seeds)
    commits = sorted(df["commit"].unique()) if len(df) else []
    dirty = [c for c in commits if c.endswith("-dirty")]
    sums = {k: int(df[k].sum()) if len(df) else 0 for k in ("mode_mismatches", "rule_mismatches", "encoding_mismatches")}
    switching_ok = len(df) > 0 and not any(sums.values())
    checks = ["## Checks", "",
              f"- Runs (need {need}): {len(df)}" + (" — all complete" if len(df) == need else " — **INCOMPLETE**"),
              f"- Every run replayed exactly from its logged holds; settings as fixed ({args.driver}-driven, cube R 150 Hz, "
              "ship B at 150 Hz, original signs).",
              f"- Commits: {', '.join(c[:7] + ('-dirty' if c.endswith('-dirty') else '') for c in commits) or '–'}"
              + (" — **some runs are -dirty**" if dirty else " (all clean)"),
              f"- Stuck runs: {int(df['stuck'].sum()) if len(df) else 0}",
              f"- **Switching** ({int(df['mode_switches'].sum()) if len(df) else 0} mode switches in all): "
              f"mode mismatches {sums['mode_mismatches']}, rule mismatches {sums['rule_mismatches']}, "
              f"encoding mismatches {sums['encoding_mismatches']} — **{'PASS' if switching_ok else 'FAIL'}**"]
    checks += [f"- **Problem:** {p}" for p in problems[:10]] + [""]
    ok = len(df) == need and not problems and (args.allow_dirty or not dirty) and switching_ok
    lines = ["# Mixed-level check (Step 6): whole brain, Stereo Madness's record settings", "",
             f"{len(names)} {args.suite} mixed levels × seeds {', '.join(map(str, args.seeds))}. A check, not a result: "
             "nothing here was predicted, so nothing is tested.", ""] + checks
    if not ok:
        lines += ["**Checks failed: nothing else is reported.**", ""]
    else:
        iso = pd.DataFrame({m: {k: np.nanmean([r[k] for r in v if r[k] is not None] or [np.nan]) for k in ("shown", "not shown")}
                            for m, v in shown.items()}).T.round(2).reset_index().rename(columns={"index": "input neurons of"})
        med = pd.DataFrame(median_runs(df.to_dict("records")).values())
        res = ["| | " + " | ".join(DIFFICULTIES) + " | All | Mean progress |", "|---|---|---|---|---|---|"]
        for label, data in (("Runs completed", df), ("Levels completed (median run)", med)):
            cells_ = [f"{int(data.loc[data['difficulty'] == d, 'completed'].sum())}/{int((data['difficulty'] == d).sum())}"
                      for d in DIFFICULTIES]
            res.append(f"| {label} | " + " | ".join(cells_) + f" | {int(data['completed'].sum())}/{len(data)} | "
                       f"{100 * data['progress'].mean():.1f}% |")
        dead = df[~df["completed"]]
        objs = {n: load_level(LEVELS, job(n, args.suite))[0] for n in names}
        refs = {label: [play_constant(objs[n], h) for n in names] for label, h in (("never press", False), ("always press", True))}
        lines += ["## Input neurons, by the mode shown (mean Hz per neuron, described)", "", md_table(iso, 2), "",
                  "Our input to a mode is off whenever that mode isn't shown (no tick logs the other mode's encoding: the "
                  "encoding check). Cells can still fire then from the brain's own wiring: **LPLC2 gets ~27,000 synapses "
                  "from the ship's T4/T5**, so it fires during ship sections; LC4 gets few and goes nearly quiet.", "",
                  "## Results (described)", ""] + res + ["",
                  f"- **Where runs died:** cube section {int((dead['death_mode'] == 'cube').sum())}, "
                  f"ship section {int((dead['death_mode'] == 'ship').sum())} (of {len(dead)} deaths).",
                  *[f"- **{k}** (context): {sum(r['completed'] for r in v)}/{len(v)} completed, mean progress "
                    f"{100 * np.mean([r['progress'] for r in v]):.1f}%." for k, v in refs.items()], ""]
    out = OUT / args.suite
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if len(df):
        df.to_csv(out / "runs.csv", index=False)
    print("\n".join(checks))
    print(f"Wrote report.md and runs.csv to {out}" + (" (outcomes not shown: blind, D33)" if args.suite == "held_out" else ""))
    if args.suite != "held_out":
        print("\n".join(lines[len(checks) + 4:]))


if __name__ == "__main__":
    main()
