"""The ship baseline report (Step 5): the fly on ship and mixed levels, read against no-brain references.

Written before the ship design, so it holds only what doesn't depend on it
(stereo_flyness.experiments.ship_analysis). Death classes and timing against the fly's readout
are added once the design is logged. **The comparisons and bars here are proposals** until Step 5's
decision fixes them with Shannyn.

Reads the runs from scripts/play_level.py (`--ship <design>`), at the given seeds. Every run is first
replayed from its logged holds and must end exactly as recorded, else the report stops. Then:
- **Results:** completed and mean progress, by kind (ship, mixed) and difficulty; stuck runs.
- **Deaths:** what killed it (block or spike), and in which mode.
- **Holding in ship mode:** share of ship ticks held, median hold and release lengths, switches
  per second. A fly that always holds or never holds plays like a reference below, not like a pilot.
- **Mixed levels:** ship sections reached and got through.
- **Against the references, ship levels only:** never hold and always hold, replayed here
  (deterministic, so no file is needed). Per level the fly's median run across seeds, D48's
  "equal", and the two-sided sign test. Random holds wait for the baseline's own hold rate (D48).

Blind on held_out (D33): only the checks are printed. Run on training first, as the check.

Usage:
    uv run python scripts/ship_report.py --ship <design> --suite training --seeds 0
    uv run python scripts/ship_report.py --ship <design> --suite held_out

Writes results/ship/<network>_<design>_<suite>.md and _runs.csv (git-ignored).
"""

import argparse
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from inspect_encoding import LEVELS, job
from run_pathway_tests import ROOT
from stereo_flyness.experiments.references import always, never
from stereo_flyness.experiments.ship_analysis import (
    compare_runs, death_mode, hold_stats, replay_run, sections_reached)
from stereo_flyness.experiments.step2_analysis import sign_test
from stereo_flyness.experiments.step4_analysis import ALPHA, median_runs
from stereo_flyness.game.engine import Game
from stereo_flyness.game.suites import load_level

RUNS = ROOT / "results" / "closed_loop"
OUT = ROOT / "results" / "ship"
KINDS = ("ship", "mixed")
DIFFICULTIES = ("easy", "medium", "hard")
REFERENCES = {"never hold": never, "always hold": always}


def suite_levels(suite, kind) -> list[str]:
    return sorted(p.stem for p in (LEVELS / suite).glob(f"{kind}-*.json") if not p.stem.endswith(".meta"))


def run_folder(args, seed) -> Path:
    tf = args.theta_full or tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())["theta_full_deg"]
    base = RUNS / args.network if args.suite == "training" else RUNS / args.network / args.suite
    return base / (f"{tf:g}deg_collision_R{args.rate:g}_ship-{args.ship}"
                   f"{'' if seed == 0 else f'_seed{seed}'}{args.tag}") / "fly"


def reference(level, policy) -> dict:
    """A no-brain player in ship mode only (as references.play), with the object it died on."""
    game, held = Game(level), False
    while not game.over:
        game.tick(held)
        held = game.player.mode == "ship" and policy(game)
    d = game.death
    return {"completed": game.finished, "progress": game.progress,
            "death_source_id": None if d is None else d.source_id}


def collect(args):
    rows, missing = [], []
    for seed in args.seeds:
        folder = run_folder(args, seed)
        for kind in KINDS:
            for name in suite_levels(args.suite, kind):
                d = folder / name
                if not (d / "run.json").exists():
                    missing.append(f"{name} seed {seed}")
                    continue
                run = json.loads((d / "run.json").read_text(encoding="utf-8"))
                if run.get("driver") != "fly" or run.get("seed") != seed or run.get("ship_design") != args.ship:
                    raise ValueError(f"{d} isn't a fly-driven seed-{seed} run of ship design {args.ship!r}")
                level, _ = load_level(LEVELS, job(name, args.suite))
                ticks = pd.read_parquet(d / "ticks.parquet")
                game = replay_run(level, ticks["held"].to_numpy(bool), run)
                sec = sections_reached(level, game.player.x, run["completed"])
                rows.append({"level": name, "kind": kind, "difficulty": name.split("-")[1], "seed": seed,
                             "completed": run["completed"], "progress": run["progress"], "ticks": run["ticks"],
                             "death_kind": run.get("death_kind"), "death_source_id": run.get("death_source_id"),
                             "death_mode": death_mode(ticks, run["completed"]),
                             "stuck": run.get("stuck_from_frame") is not None, "commit": run.get("commit", ""),
                             "sections": len(sec), "sections_reached": sum(s["reached"] for s in sec),
                             "sections_passed": sum(s["passed"] for s in sec),
                             **{f"ship_{k}": v for k, v in hold_stats(ticks).items()}})
    return pd.DataFrame(rows), missing


def checks(df, missing, args) -> tuple[list[str], bool]:
    n = sum(len(suite_levels(args.suite, k)) for k in KINDS) * len(args.seeds)
    lines = ["## Checks (before any result)", "",
             f"- Runs (need {n}: every ship and mixed level of {args.suite} at seeds {', '.join(map(str, args.seeds))}): "
             f"{len(df)}" + (" — **all complete**" if len(df) == n else " — **INCOMPLETE: nothing is compared**")]
    lines += [f"  - missing: {m}" for m in missing[:10]] + (["  - ..."] if len(missing) > 10 else [])
    lines.append(f"- Every run replayed exactly from its logged holds ({len(df)} runs).")
    commits = sorted(df["commit"].unique()) if len(df) else []
    dirty = [c for c in commits if c.endswith("-dirty")]
    lines.append(f"- Commits: {', '.join(c[:7] + ('-dirty' if c.endswith('-dirty') else '') for c in commits) or '–'}"
                 + (" — **some runs are -dirty**" if dirty else ""))
    lines.append(f"- Stuck runs: {int(df['stuck'].sum()) if len(df) else 0}")
    return lines + [""], len(df) == n and n > 0


def results(df) -> list[str]:
    lines = ["## Results", "", "| Kind | " + " | ".join(DIFFICULTIES) + " | All | Mean progress |", "|---|---|---|---|---|---|"]
    for kind in KINDS:
        g = df[df["kind"] == kind]
        cells = [f"{int(g.loc[g['difficulty'] == d, 'completed'].sum())}/{int((g['difficulty'] == d).sum())}"
                 for d in DIFFICULTIES]
        lines.append(f"| {kind} | " + " | ".join(cells) + f" | {int(g['completed'].sum())}/{len(g)} | "
                     f"{100 * g['progress'].mean():.1f}% |")
    dead = df[~df["completed"]]
    lines += ["", "**Deaths:** " + (", ".join(f"{n} on a {k} in {m} mode" for (k, m), n in
                                              dead.groupby(["death_kind", "death_mode"]).size().items()) or "none"), ""]
    return lines


def holding(df) -> list[str]:
    lines = ["## Holding in ship mode", "",
             "| Kind | Ship ticks held | Median hold | Median release | Switches per s |", "|---|---|---|---|---|"]
    ms = 1000 / 240
    for kind in KINDS:
        g = df[(df["kind"] == kind) & (df["ship_ticks"] > 0)]
        if g.empty:
            lines.append(f"| {kind} | never reached ship mode | – | – | – |")
            continue
        share = (g["ship_held_share"] * g["ship_ticks"]).sum() / g["ship_ticks"].sum()
        hold, rel = g["ship_median_hold_ticks"].median(), g["ship_median_release_ticks"].median()
        lines.append(f"| {kind} | {share:.0%} | {'–' if pd.isna(hold) else f'{hold * ms:.0f} ms'} | "
                     f"{'–' if pd.isna(rel) else f'{rel * ms:.0f} ms'} | {g['ship_switches_per_s'].median():.1f} |")
    lines += ["", "Per run medians, then the median across runs. Full climb from rest takes 93 ticks of holding "
              "(390 ms); full fall from full climb, 170 ticks of release (710 ms) (docs/notes/ship_brief.md §1).", ""]
    mixed = df[df["kind"] == "mixed"]
    if len(mixed):
        lines += ["## Mixed levels: ship sections", "",
                  f"- Reached {int(mixed['sections_reached'].sum())} and got through {int(mixed['sections_passed'].sum())} "
                  f"of {int(mixed['sections'].sum())} ship sections ({len(mixed)} runs).", ""]
    return lines


def against_references(df, args) -> list[str]:
    ship = df[df["kind"] == "ship"]
    fly = median_runs(ship.to_dict("records"))
    lines = ["## Against the references (ship levels; proposed comparisons, fixed in Step 5's decision)", "",
             "| Reference | Its completions | Its mean progress | Fly better | Fly worse | Equal | p | Reading |",
             "|---|---|---|---|---|---|---|---|"]
    for name, policy in REFERENCES.items():
        refs = {lv: reference(load_level(LEVELS, job(lv, args.suite))[0], policy) for lv in fly}
        signs = [compare_runs(fly[lv], refs[lv]) for lv in sorted(fly)]
        better, worse = signs.count(1), signs.count(-1)
        p = sign_test(better, worse)
        reading = ("better" if better > worse else "worse") if p < ALPHA else "no clear difference"
        lines.append(f"| {name} | {sum(r['completed'] for r in refs.values())}/{len(refs)} | "
                     f"{100 * np.mean([r['progress'] for r in refs.values()]):.1f}% | {better} | {worse} | "
                     f"{signs.count(0)} | {p:.3f} | {reading} |")
    return lines + ["", "Random holds (chance) wait for the baseline's hold rate, as D48 did for the cube.", ""]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ship", required=True, help="the ship design, as play_level.py names it")
    ap.add_argument("--suite", default="training", choices=["training", "held_out"])
    ap.add_argument("--network", default="final")
    ap.add_argument("--rate", type=float, default=150.0)
    ap.add_argument("--theta-full", type=float, default=None)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--tag", default="")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    df, missing = collect(args)
    check_lines, ok = checks(df, missing, args)
    lines = [f"# Ship baseline ({args.ship}, {args.network}, {args.suite})", "",
             f"R = {args.rate:g} Hz for the cube sections (D50); ship design {args.ship!r}. Seeds "
             f"{', '.join(map(str, args.seeds))}. Comparisons and bars are proposals until Step 5's decision.", ""]
    lines += check_lines + (results(df) + holding(df) + against_references(df, args) if ok
                            else ["**Checks failed: nothing is compared.**"])
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"{args.network}_{args.ship}_{args.suite}"
    (args.out / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    df.to_csv(args.out / f"{stem}_runs.csv", index=False)
    print("\n".join(check_lines))
    if args.suite == "held_out":
        print(f"Wrote {stem}.md and _runs.csv to {args.out} (outcomes not shown: blind, D33)")
    else:
        print("\n".join(lines[len(check_lines) + 4:]))


if __name__ == "__main__":
    main()
