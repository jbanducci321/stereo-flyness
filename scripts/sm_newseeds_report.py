"""Stereo Madness on new seeds, the report (D60; docs/notes/sm_newseeds_plan.md). Fixed before any run.

- **Checks first:** every run in configs/iteration2/stereo_madness.toml present; fly-driven with the
  config's settings and seed, fix 1 (ii) on, the original connectome; every run replays exactly from
  its logged holds; one clean commit; stuck runs counted. If any check fails, nothing is reported.
- **Results:** completed (k of N) and the median progress (the mean of the 50th and 51st runs for
  N = 100; quartiles, range), never the best run as the headline; where runs ended, by place; P8's
  milestones; the frames fix 1 changed; the showcase pick (D54's rule).
- **Context, not a comparison:** Part 1's 100 record runs (seeds 0-99, D54), by the same measures.
- **Prediction 8's measures** (Shannyn's fix 1 note; D60's rule), scored when the report is opened.

It shows only how far the fly gets; it judges nothing (D55). Blind (D33): only the checks are
printed; the rest goes to results/iteration2/stereo_madness/report.md.

Usage:
    uv run python scripts/sm_newseeds_report.py
"""

import json
import sys
import tomllib
from pathlib import Path

import pandas as pd

from ship_baseline_report import death_object
from stereo_flyness.experiments.ship_analysis import replay_run
from stereo_flyness.experiments.sm_newseeds import milestones, prediction8, strip_at, strip_end
from stereo_flyness.experiments.stereo_madness import showcase, spread, where
from stereo_flyness.game.level import Level

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "iteration2" / "stereo_madness.toml"
LEVEL = ROOT / "data" / "gd" / "stereo_madness.json"
OUT = ROOT / "results" / "iteration2" / "stereo_madness"
PART1 = ROOT / "results" / "stereo_madness"
PART1_SEEDS = range(100)
CONNECTOME = "Connectivity_783.parquet"


def theta() -> float:
    return tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())["theta_full_deg"]


def folder(cfg, seed) -> Path:
    v = next(iter(cfg["variants"].values()))
    return (OUT / cfg["network"] / (f"{theta():g}deg_collision_fix1-{cfg['fix1']}_R{v['rate_hz']:g}"
            f"_ship-{cfg['ship_design']}{'' if seed == 0 else f'_seed{seed}'}") / "fly" / "stereo_madness")


def part1_folder(seed) -> Path:
    """D54's record runs: seeds 0-9 (pre-registered) and 10-99 (the extra runs, tagged _explore)."""
    tag = "" if seed < 10 else "_explore"
    return (PART1 / "whole_brain" / f"200deg_collision_R150_ship-B{'' if seed == 0 else f'_seed{seed}'}{tag}"
            / "fly" / "stereo_madness")


def collect(level, cfg, seeds, where_of, fixed: bool):
    v = next(iter(cfg["variants"].values()))
    rows, problems = [], []
    for seed in seeds:
        d = where_of(seed)
        if not (d / "run.json").exists():
            problems.append(f"seed {seed}: missing")
            continue
        run = json.loads((d / "run.json").read_text(encoding="utf-8"))
        cube, ship = run.get("modes", {}).get("cube", {}), run.get("modes", {}).get("ship", {})
        if run.get("driver") != "fly" or run.get("seed") != seed or run.get("ship_design") != cfg["ship_design"] \
                or ship.get("ship_rate_hz") != cfg["ship_rate_hz"] or cube.get("rate_hz") != v["rate_hz"] \
                or run.get("signs", "original") != "original" or run.get("connectome", {}).get("file") != CONNECTOME \
                or (cube.get("view") == "landing") != fixed:
            problems.append(f"seed {seed}: wrong settings")
            continue
        held = pd.read_parquet(d / "ticks.parquet")["held"].to_numpy(bool)
        try:
            game = replay_run(level, held, run)
        except ValueError as e:
            problems.append(f"seed {seed}: {e}")
            continue
        x = level.length if run["completed"] else float(run.get("death_x") or game.player.x)
        changed = int(pd.read_parquet(d / "brain.parquet", columns=["predicted"])["predicted"].sum()) if fixed else 0
        strip = None if run["completed"] else strip_at(level, x)
        place = ("completed" if run["completed"] else
                 f"{run.get('death_kind')} strip, x {strip[0]:g}–{strip[1]:g}" if strip else
                 f"{run.get('death_kind')} at x {30 * (x // 30):g}")
        rows.append({"seed": seed, "completed": run["completed"], "progress": run["progress"], "x": x,
                     "stuck": run.get("stuck_from_frame") is not None, "commit": run.get("commit", ""),
                     "death_object": death_object(level, game), "place": place, "changed": changed,
                     **where(level, x, run["completed"])})
    df = pd.DataFrame(rows)
    commits = sorted(df["commit"].unique()) if len(df) else []
    if len(commits) != 1 or any(c.endswith("-dirty") or not c for c in commits):
        problems.append(f"runs aren't from one clean commit: {commits}")
    return df, problems


def headline(df) -> str:
    s = spread(df.to_dict("records"))
    return (f"completed **{s['completed']} of {s['runs']}**; median progress **{100 * s['median']:.1f}%** "
            f"(quartiles {100 * s['q1']:.1f}–{100 * s['q3']:.1f}%, range {100 * s['min']:.1f}–{100 * s['max']:.1f}%)")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    level = Level.load(LEVEL)
    df, problems = collect(level, cfg, cfg["seeds"], lambda s: folder(cfg, s), fixed=True)
    p1, p1_problems = collect(level, {**cfg, "variants": {"record": {"rate_hz": 150.0}}}, PART1_SEEDS, part1_folder,
                              fixed=False)
    checks = [f"- Runs (need {len(cfg['seeds'])}): {len(df)}", f"- Stuck runs: {int(df['stuck'].sum()) if len(df) else 0}"]
    if problems or len(df) != len(cfg["seeds"]):
        print("Checks failed, nothing reported:\n- " + "\n- ".join(problems[:40] or ["runs missing"]))
        sys.exit(1)
    if p1_problems or not len(p1):
        print("Part 1's context runs failed their checks; the context is left out:\n- " + "\n- ".join(p1_problems[:10]))
    commit = df["commit"].iloc[0]

    # Part 1's furthest point: the far edge of the hazard strip where its furthest run died (D60)
    far = p1.loc[p1["x"].idxmax()] if len(p1) else None
    edge = strip_end(level, far["x"]) if far is not None else None
    lines = [f"# Stereo Madness on new seeds ({cfg['decision']})", "",
             "*Exploratory: interface adjusted after seeing Stereo Madness; brain wiring unchanged (D55). "
             f"The fly of record with fix 1 (ii), ship {cfg['ship_design']} at {cfg['ship_rate_hz']:g} Hz, whole brain, "
             f"seeds {cfg['seeds'][0]}–{cfg['seeds'][-1]}, commit `{commit}`. **It shows only how far the fly gets; "
             "it judges nothing.** Fixed in D60 before any run.*", "",
             "## Checks", ""] + checks + ["- Every run replayed exactly from its logged holds; settings as configured; "
                                          "one clean commit.", "",
             "## The headline", "", f"Fix 1 (ii), seeds {cfg['seeds'][0]}–{cfg['seeds'][-1]}: {headline(df)}.", ""]
    if len(p1):
        lines += [f"*Context, not a comparison: Part 1's record runs, seeds 0–99 (D54): {headline(p1)}.*", ""]

    places = df["place"].value_counts().rename("fix 1 (ii)")
    table = places.to_frame()
    if len(p1):
        table = table.join(p1["place"].value_counts().rename("Part 1 (context)"), how="outer").fillna(0).astype(int)
    first = pd.concat([df, p1]).groupby("place")["x"].min()
    table = table.loc[sorted(table.index, key=lambda p: first.get(p, 0))]
    lines += ["## Where runs ended", "", "| Place | fix 1 (ii) | " + ("Part 1 (context) |" if len(p1) else ""),
              "|---|---|" + ("---|" if len(p1) else "")]
    for place, r in table.iterrows():
        lines.append(f"| {place} | {r['fix 1 (ii)']} | " + (f"{r['Part 1 (context)']} |" if len(p1) else ""))
    lines += ["", "Places are the hazard strip (pits or spikes a cell or less apart) the run died in, or the "
                  "30-unit cell where it died if it wasn't a strip.", ""]

    if edge is not None:
        m, m1 = milestones(df.to_dict("records"), edge), milestones(p1.to_dict("records"), edge)
        lines += ["## Milestones (runs reaching each)", "",
                  f"Part 1's furthest point: alive past the hazard strip ending at x {edge:g} "
                  f"(Part 1's furthest run, {100 * far['progress']:.1f}%).", "",
                  "| Milestone | fix 1 (ii) | Part 1 (context) |", "|---|---|---|"]
        lines += [f"| {k} | {m[k]} of {len(df)} | {m1[k]} of {len(p1)} |" for k in m] + [""]

    ch = df["changed"]
    lines += ["## Frames fix 1 changed", "",
              f"- Runs where fix 1 changed any frame: **{int((ch > 0).sum())} of {len(df)}**; frames changed per run: "
              f"median {ch.median():g}, range {ch.min():g}–{ch.max():g}.", ""]

    pick = showcase(df.to_dict("records"))
    best = df.sort_values(["progress", "seed"], ascending=[False, True]).iloc[0]
    lines += ["## Showcase replay (D54's rule)", "",
              f"- **Closest to the median, ties to the lowest seed:** seed {pick['seed']}, {100 * pick['progress']:.1f}%.",
              f"- Optional, labelled \"the furthest of {len(df)}\": seed {best['seed']}, {100 * best['progress']:.1f}%.", ""]

    if edge is not None:
        p8 = prediction8(spread(df.to_dict("records"))["median"], milestones(df.to_dict("records"), edge)[
            "past Part 1's furthest point"] > 0)
        lines += ["## Measures for Shannyn's fix 1 prediction 8 (scored when opened, D60)", "",
                  f"- Median within ±1 point of 9.2% (8.2–10.2%): **{'yes' if p8['median unchanged'] else 'no'}**.",
                  f"- A run past Part 1's furthest point: **{'yes' if p8['a run past Part 1' + chr(39) + 's furthest point'] else 'no'}**.",
                  ""]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(["Checks passed:"] + checks))
    print(f"Wrote {OUT / 'report.md'} (outcomes not shown: blind, D33)")


if __name__ == "__main__":
    main()
