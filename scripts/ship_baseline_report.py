"""The ship baseline report (Step 5): D53's designs judged by docs/notes/ship_analysis_plan.md.

Per design (B, the design of record; C, its control; B90, the faster-anchor variant), on the 20 ship
levels of a suite at seeds 0-2, whole brain:
- **Checks first:** every run present and fly-driven with the right design, seed and R_ship; every run
  replays exactly from its logged holds; commits clean; stuck runs counted. If any check fails,
  nothing is compared.
- **Results:** levels and runs completed, mean progress, by difficulty.
- **Against the references:** never hold, always hold, and random holds (10 draws per level, from the
  design's own hold and release lengths). Per level, the median run across seeds; D48's "equal" (both
  completed, or both died on the same object); two-sided sign test, "better"/"worse" only at p < 0.05.
- **Against its ideal ship** (described), **death classes** (the plan's order), **how it flies**
  (holding, DNp22 against the input, which side releases, lag, tracking) and the **seed-against-seed
  noise line**.
- **Between designs** (when their runs are complete): C against B ("does the fly's stabiliser improve
  steering?") and B90 against B ("does the anchor's state matter?").

Blind on held_out (D33): only the checks are printed; everything goes to the files. Test it on
training runs first (they don't count).

Usage:
    uv run python scripts/ship_baseline_report.py --suite training --seeds 0 --tag _smoke --designs B \n        --levels ship-easy-0 ship-medium-0           # the check, on the smoke-test runs
    uv run python scripts/ship_baseline_report.py                       # held_out, all three designs

Writes results/ship_baseline/<suite>/report.md and runs.csv (git-ignored).
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from analyse_pathway_tests import md_table
from inspect_encoding import LEVELS, job
from stereo_flyness.experiments.references import always, never
from stereo_flyness.experiments.ship_analysis import compare_runs, hold_stats, replay_run
from stereo_flyness.experiments.ship_baseline import (
    CLASSES, classify_death, ideal_encoder, ideal_holds, input_output, lags, lengths, random_holds,
    release_sides, tracking)
from stereo_flyness.experiments.step2_analysis import sign_test
from stereo_flyness.experiments.step4_analysis import ALPHA, median_runs
from stereo_flyness.game.engine import Game
from stereo_flyness.game.suites import load_level

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results" / "closed_loop" / "whole_brain"
OUT = ROOT / "results" / "ship_baseline"
DESIGNS = {"B": "B, the design of record", "C": "C, control (no stabiliser)", "B90": "B90, faster anchor (90°/s)"}
DIFFICULTIES = ("easy", "medium", "hard")
RANDOM_DRAWS = 10
R_SHIP = 150.0


def folder(suite, design, seed, tag) -> Path:
    base = RUNS if suite == "training" else RUNS / suite
    return base / f"200deg_collision_R150_ship-{design}{'' if seed == 0 else f'_seed{seed}'}{tag}" / "fly"


def levels(suite) -> list[str]:
    return sorted((p.stem for p in (LEVELS / suite).glob("ship-*.json") if not p.stem.endswith(".meta")),
                  key=lambda n: (DIFFICULTIES.index(n.split("-")[1]), int(n.split("-")[2])))


def death_object(level, game) -> str | None:
    """The killing box, as "x0,y0" (generated levels have no GD object IDs)."""
    d = game.death
    if d is None:
        return None
    hits = [b for b in level.boxes if b.kind == d.kind and not (
        d.x + 15 < b.x0 or b.x1 < d.x - 15 or d.y + 15 < b.y0 or b.y1 < d.y - 15)]
    if not hits:
        return None
    b = min(hits, key=lambda b: abs((b.x0 + b.x1) / 2 - d.x) + abs((b.y0 + b.y1) / 2 - d.y))
    return f"{b.x0:g},{b.y0:g}"


def play(level, policy) -> dict:
    """A no-brain player; the decision after tick i holds tick i + 1, as for the fly."""
    game, held = Game(level), False
    while not game.over:
        game.tick(held)
        held = game.player.mode == "ship" and policy(game)
    return {"completed": game.finished, "progress": game.progress, "death_source_id": death_object(level, game)}


def collect(args, design, names):
    runs, brains, problems = [], {}, []
    for seed in args.seeds:
        for name in names:
            d = folder(args.suite, design, seed, args.tag) / name
            if not (d / "run.json").exists():
                problems.append(f"{design}: {name} seed {seed} missing")
                continue
            run = json.loads((d / "run.json").read_text(encoding="utf-8"))
            ship = run.get("modes", {}).get("ship", {})
            if run.get("driver") != "fly" or run.get("seed") != seed or run.get("ship_design") != design \
                    or ship.get("ship_rate_hz") != R_SHIP:
                problems.append(f"{design}: {name} seed {seed} has the wrong settings")
                continue
            level, _ = load_level(LEVELS, job(name, args.suite))
            ticks = pd.read_parquet(d / "ticks.parquet")
            held = ticks["held"].to_numpy(bool)
            try:
                game = replay_run(level, held, run)
            except ValueError as e:
                problems.append(f"{design}: {e}")
                continue
            stuck = run.get("stuck_from_frame") is not None
            cls, detail = ("completed", {}) if run["completed"] else classify_death(level, held, design, stuck)
            hs = hold_stats(ticks)
            runs.append({"design": design, "level": name, "difficulty": name.split("-")[1], "seed": seed,
                         "completed": run["completed"], "progress": run["progress"], "seconds": run["seconds"],
                         "death_source_id": death_object(level, game), "class": cls, "stuck": stuck,
                         "commit": run.get("commit", ""), **{f"ship_{k}": v for k, v in hs.items()}})
            brains[(name, seed)] = (pd.read_parquet(d / "brain.parquet"), held)
    return pd.DataFrame(runs), brains, problems


def checks(design, df, problems, n_needed, allow_dirty=False) -> tuple[list[str], bool]:
    commits = sorted(df["commit"].unique()) if len(df) else []
    dirty = [c for c in commits if c.endswith("-dirty")]
    lines = [f"### Checks: {DESIGNS[design]}", "",
             f"- Runs (need {n_needed}): {len(df)}" + (" — all complete" if len(df) == n_needed else " — **INCOMPLETE**"),
             f"- Every run replayed exactly from its logged holds; settings as fixed (fly-driven, design {design}, R_ship {R_SHIP:g} Hz).",
             f"- Commits: {', '.join(c[:7] + ('-dirty' if c.endswith('-dirty') else '') for c in commits) or '–'}"
             + (" — **some runs are -dirty**" if dirty else " (all clean)"),
             f"- Stuck runs: {int(df['stuck'].sum()) if len(df) else 0}"]
    lines += [f"- **Problem:** {p}" for p in problems[:10]]
    return lines + [""], len(df) == n_needed and not problems and (allow_dirty or not dirty)


def compare(a: dict, b: dict) -> str:
    """a against b (median runs per level), as a table row."""
    signs = [compare_runs(a[lv], b[lv]) for lv in sorted(a)]
    better, worse, equal = signs.count(1), signs.count(-1), signs.count(0)
    p = sign_test(better, worse)
    reading = ("better" if better > worse else "worse") if p < ALPHA else "no clear difference"
    return f"{better} | {worse} | {equal} | {p:.3f} | {reading}"


def results(df) -> list[str]:
    med = median_runs(df.to_dict("records"))
    lines = ["| | " + " | ".join(DIFFICULTIES) + " | All | Mean progress |", "|---|---|---|---|---|---|"]
    for label, data in (("Runs completed", df), ("Levels completed (median run)", pd.DataFrame(med.values()))):
        cells = [f"{int(data.loc[data['difficulty'] == d, 'completed'].sum())}/{int((data['difficulty'] == d).sum())}"
                 for d in DIFFICULTIES]
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {int(data['completed'].sum())}/{len(data)} | "
                     f"{100 * data['progress'].mean():.1f}% |")
    return lines + [""]


def references(args, design, df, names) -> list[str]:
    fly = median_runs(df.to_dict("records"))
    holds, rels = [], []
    for _, held in [v for v in args.brains.values()]:
        h, r = lengths(held)
        holds, rels = holds + h, rels + r
    lines = ["| Reference | Its completions | Its mean progress | Fly better | Fly worse | Equal | p | Reading |",
             "|---|---|---|---|---|---|---|---|"]
    level_objs = {n: load_level(LEVELS, job(n, args.suite))[0] for n in names}
    for ref_name, policy in (("never hold", never), ("always hold", always)):
        refs = {n: {**play(level_objs[n], policy), "level": n} for n in names}
        lines.append(f"| {ref_name} | {sum(r['completed'] for r in refs.values())}/{len(refs)} | "
                     f"{100 * np.mean([r['progress'] for r in refs.values()]):.1f}% | {compare(fly, refs)} |")
    rng = np.random.default_rng(53)
    draws = [{n: play(level_objs[n], random_holds(holds, rels, rng)) for n in names} for _ in range(RANDOM_DRAWS)]
    readings = [compare(fly, d).split(" | ")[-1] for d in draws]
    mean_ref = {n: {"completed": np.mean([d[n]["completed"] for d in draws]) >= 0.5,
                    "progress": float(np.mean([d[n]["progress"] for d in draws])), "death_source_id": None} for n in names}
    lines.append(f"| random holds, mean of {RANDOM_DRAWS} draws | {sum(r['completed'] for r in mean_ref.values())}/{len(names)} | "
                 f"{100 * np.mean([r['progress'] for r in mean_ref.values()]):.1f}% | {compare(fly, mean_ref)} |")
    lines += ["", f"Random holds per draw: " + ", ".join(f"{readings.count(r)} {r}" for r in sorted(set(readings))) +
              f" (drawn from the fly's own {len(holds)} hold and {len(rels)} release stretches).", ""]
    ideal = {n: play(level_objs[n], (lambda e: lambda g: ideal_holds(e, g))(ideal_encoder(level_objs[n], design)))
             for n in names}
    lines.append(f"**Its ideal ship** (described): completes {sum(r['completed'] for r in ideal.values())}/{len(names)}, "
                 f"mean progress {100 * np.mean([r['progress'] for r in ideal.values()]):.1f}%; fly against it: "
                 f"{compare(fly, ideal).replace(' | ', ' / ')} (better / worse / equal / p / reading).")
    return lines + [""]


def deaths(df) -> list[str]:
    dead = df[~df["completed"]]
    counts = dead["class"].value_counts()
    return ["| " + " | ".join(CLASSES) + " |", "|" + "---|" * len(CLASSES),
            "| " + " | ".join(str(int(counts.get(c, 0))) for c in CLASSES) + " |", "",
            "(s) stuck, (a) unseen, (b) the encoding's limit, (d_up)/(d_down) the fly's control (too high / too low "
            "against the ideal ship), (u) unclassified.", ""]


def flying(df, brains) -> list[str]:
    b = pd.concat([v[0] for v in brains.values()], ignore_index=True)
    share = (df["ship_held_share"] * df["ship_ticks"]).sum() / df["ship_ticks"].sum()
    lag = [x for v in brains.values() for x in lags(v[0])]
    sides = release_sides(b)
    tr = tracking(b)
    io = input_output(b).round(1).reset_index().rename(columns={"f": "input (signed f)"})
    return [f"- **Holding:** {share:.0%} of ship ticks held; median hold {df['ship_median_hold_ticks'].median():.0f} ticks, "
            f"median release {df['ship_median_release_ticks'].median():.0f} ticks; {df['ship_switches_per_s'].median():.1f} switches per s.",
            f"- **Which side releases:** of {sides['releases']} release frames, right only {sides['right only']}, "
            f"left only {sides['left only']}, both {sides['both']}.",
            f"- **Lag** from the motion turning downward to the next release: median {np.median(lag) if lag else float('nan'):.0f} ticks "
            f"(n = {len(lag)}).",
            f"- **Tracking:** median |vy − v_req| {tr['median |vy - v_req| (units/s)'] or float('nan'):.1f} units/s; "
            f"median |error| at the column {tr['median |error| at the column (units)'] or float('nan'):.1f} units ({tr['columns passed']} columns).",
            "", "**DNp22 against the input** (all ship ticks pooled):", "", md_table(io, 1), ""]


def noise(df) -> list[str]:
    seeds = sorted(df["seed"].unique())
    out = []
    for i, a in enumerate(seeds):
        for b in seeds[i + 1:]:
            x = {r["level"]: r for r in df[df["seed"] == a].to_dict("records")}
            y = {r["level"]: r for r in df[df["seed"] == b].to_dict("records")}
            out.append(f"- seed {a} against seed {b}: " + compare(x, y).replace(" | ", " / "))
    return (["**Noise line** (better / worse / equal / p / reading):"] + out + [""]) if out else []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--suite", default="held_out", choices=["training", "held_out"])
    ap.add_argument("--designs", nargs="+", default=list(DESIGNS), choices=list(DESIGNS))
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--tag", default="")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--levels", nargs="+", default=None, help="a subset of levels (testing on training runs only)")
    ap.add_argument("--allow-dirty", action="store_true", help="training only: test on runs from an uncommitted tree")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    out = args.out or OUT / args.suite
    names = levels(args.suite)
    if args.levels:
        if args.suite == "held_out":
            sys.exit("--levels is for testing on training runs; the held-out report uses all 20 levels.")
        names = [n for n in names if n in args.levels]
    if args.allow_dirty and args.suite == "held_out":
        sys.exit("--allow-dirty is for testing on training runs only.")
    lines = ["# Ship baseline (D53): whole brain, R_ship = 150 Hz", "",
             f"{len(names)} {args.suite} ship levels × seeds {', '.join(map(str, args.seeds))}. Judged by "
             "docs/notes/ship_analysis_plan.md, fixed with D53 before any run.", ""]
    printed, all_runs, medians = [], [], {}
    for design in args.designs:
        df, brains, problems = collect(args, design, names)
        check_lines, ok = checks(design, df, problems, len(names) * len(args.seeds), args.allow_dirty)
        printed += check_lines
        lines += [f"## {DESIGNS[design]}", ""] + check_lines
        if not ok:
            lines += ["**Checks failed for this design: nothing is compared.**", ""]
            continue
        args.brains = brains
        medians[design] = median_runs(df.to_dict("records"))
        lines += ["### Results", ""] + results(df) + ["### Against the references", ""] + references(args, design, df, names)
        lines += ["### Death classes", ""] + deaths(df) + ["### How it flies", ""] + flying(df, brains) + noise(df)
        all_runs.append(df)
    pairs = [("C", "B", "does the fly's stabiliser improve steering? (B better: yes)"),
             ("B90", "B", "does the anchor's state matter? (B stays the headline either way)")]
    done = [(a, b, q) for a, b, q in pairs if a in medians and b in medians]
    if done:
        lines += ["## Between designs", "", "| Comparison | Better | Worse | Equal | p | Reading |", "|---|---|---|---|---|---|"]
        lines += [f"| {a} against {b}: {q} | {compare(medians[a], medians[b])} |" for a, b, q in done] + [""]
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if all_runs:
        pd.concat(all_runs, ignore_index=True).to_csv(out / "runs.csv", index=False)
    print("\n".join(printed))
    if args.suite == "held_out":
        print(f"Wrote report.md and runs.csv to {out} (outcomes not shown: blind, D33)")
    else:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
