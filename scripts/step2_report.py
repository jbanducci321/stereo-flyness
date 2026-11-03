"""The Step 2 report (D48): the untuned fly on the held-out cube levels, read against the references.

Reads the fly-driven runs from scripts/play_cube.py (baseline at seeds 0-2, the two comparisons
at seed 0), the ideal fly from scripts/ideal_fly.py and the no-brain references from
scripts/reference_flies.py. Every run is first replayed from its logged presses and must rebuild
the recording exactly (else the report stops). Then, all as fixed in D48:
- **Results:** runs completed (of 60, per level of 3, and seed 0 alone), mean progress, by difficulty.
- **Death classes:** (s) stuck, (a) invisible, (c) short run-up, (b) the ideal fly dies there too,
  (d1/d2/d3) the fly's timing: jumped earlier / later / not at all
  (`stereo_flyness.experiments.step2_analysis`).
- **Timing per approach:** θ at the first Giant Fiber spike, jumps against the single-spike
  window, presses with nothing looming.
- **Comparisons,** paired by level against the baseline at seed 0, with the sign test, plus the
  noise line (seeds 1 and 2 against seed 0).
- **Stuck runs:** included, and left out, and the stuck rate per simulated second.
- **Replays** for the write-up, picked by rule.

Nothing here chooses anything. On the held-out suite nothing is printed but the files written
(D33): the results are opened together, after the report has passed its check on training runs.

Usage:
    uv run python scripts/step2_report.py --suite training   # the check, on training runs only
    uv run python scripts/step2_report.py                    # Step 2: writes the files, shows nothing

Writes results/step2/<network>_<suite>.md, _runs.csv and _approaches.csv (git-ignored).
"""

import argparse
import json
import sys
import tomllib

import numpy as np
import pandas as pd

from analyse_pathway_tests import md_table
from inspect_encoding import LEVELS, job
from run_pathway_tests import ROOT
from stereo_flyness.experiments.step2_analysis import (
    CLASSES, MODEL_SD_DEG, THRESHOLD_DEG, approach_timing, check_replay, classify_death, compare, describe,
    presses_nothing_looming, replay, sign_test)
from stereo_flyness.game.physics import TICKS_PER_SECOND
from stereo_flyness.game.suites import load_level

RUNS = ROOT / "results" / "closed_loop"
IDEAL = ROOT / "results" / "ideal_fly"
REFERENCES = ROOT / "results" / "references"
OUT = ROOT / "results" / "step2"
DIFFICULTIES = ("easy", "medium", "hard")
SEEDS = (0, 1, 2)  # the baseline's seeds (D48); the comparisons run at seed 0
FLY_SD_DEG = 14.0  # the real fly's spread around 39° (von Reyn et al. 2014)
BASELINE = "baseline"


def settings() -> dict:
    """The Step 2 settings (D43, D45, D48) as play_cube.py names their folders: (folder, mode, seeds)."""
    cfg = tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())
    tf, flat = cfg["theta_full_deg"], cfg["flat_theta_full_deg"]
    return {BASELINE: (f"{tf:g}deg_collision_R150", "collision", SEEDS),
            "comparison 1 (pre-D45 flat R)": (f"{flat:g}deg_collision_R150_flat", "collision", (0,)),
            "comparison 2 (every object looms)": (f"{tf:g}deg_all_R150", "all", (0,))}


def suite_levels(suite) -> list[str]:
    return sorted(p.stem for p in (LEVELS / suite).glob("cube-*.json") if not p.stem.endswith(".meta"))


def read_run(folder, level, mode) -> tuple[dict, pd.DataFrame]:
    """One recorded fly-driven run, replayed and classified."""
    run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    if run.get("driver") != "fly":
        raise ValueError(f"{folder} isn't a fly-driven run")
    brain = pd.read_parquet(folder / "brain.parquet")
    ticks = pd.read_parquet(folder / "ticks.parquet", columns=["held"])
    rep = replay(level, ticks["held"].to_numpy(bool), mode)
    check_replay(rep, run, brain)
    stuck = brain["stuck_flag"].to_numpy(bool)
    death = classify_death(rep, stuck_at_death=bool(len(stuck) and stuck[-1]))
    row = {"completed": run["completed"], "progress": run["progress"], "ticks": run["ticks"],
           "seconds": run["ticks"] / TICKS_PER_SECOND, "jumps": run["jumps"], "presses": run["presses"],
           "stuck": run["stuck_from_frame"] is not None, "stuck_from_frame": run["stuck_from_frame"],
           "stuck_frames": int(stuck.sum()), "nothing_looming_presses": presses_nothing_looming(brain),
           "commit": run["commit"], **death,
           "killer_text": None if death["killer"] is None else describe(death["killer_kind"], death["killer"])}
    return row, approach_timing(rep, brain)


def collect(network, suite) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = RUNS / network if suite == "training" else RUNS / network / suite
    runs, appr = [], []
    for name, (folder, mode, seeds) in settings().items():
        for seed in seeds:
            fly = base / f"{folder}{'' if seed == 0 else f'_seed{seed}'}" / "fly"
            for level_dir in sorted(fly.glob("cube-*")) if fly.is_dir() else []:
                level, _ = load_level(LEVELS, job(level_dir.name, suite))
                row, t = read_run(level_dir, level, mode)
                key = {"setting": name, "seed": seed, "level": level_dir.name}
                runs.append({**key, **row})
                appr.append(t.assign(**key))
    if not runs:
        sys.exit(f"No fly-driven Step 2 runs under {base}. Run scripts/play_cube.py first.")
    df = pd.DataFrame(runs)
    df["difficulty"] = df["level"].str.split("-").str[1]
    return df, pd.concat(appr, ignore_index=True)


def references(network, suite, levels) -> pd.DataFrame:
    """The ideal fly (D44) and the no-brain references (D48), on the levels that were run."""
    rows = []
    ideal_file = IDEAL / ("all50.csv" if suite == "training" else "held_out20.csv")
    if ideal_file.exists():
        ideal = pd.read_csv(ideal_file)
        ideal = ideal[(ideal["threshold"] == THRESHOLD_DEG) & ideal["level"].isin(levels)]
        for mode, label in (("collision", "ideal fly (collision course)"), ("all", "ideal fly (every object looms)")):
            for r in ideal[ideal["mode"] == mode].to_dict("records"):
                rows.append({"setting": label, "draw": None, "level": r["level"], "completed": r["completed"],
                             "progress": r["progress"], "class": r["class"] if isinstance(r["class"], str) else None})
    ref_file = REFERENCES / f"{network}_{suite}.csv"
    if ref_file.exists():
        ref = pd.read_csv(ref_file)
        for r in ref[ref["level"].isin(levels)].to_dict("records"):
            rows.append({"setting": r["reference"], "draw": r["draw"], "level": r["level"],
                         "completed": r["completed"], "progress": r["progress"], "class": None})
    out = pd.DataFrame(rows, columns=["setting", "draw", "level", "completed", "progress", "class"])
    out["difficulty"] = out["level"].str.split("-").str[1]
    return out


def pct(x) -> str:
    return "–" if x is None or pd.isna(x) else f"{100 * x:.0f}%"


def results_table(df, refs) -> list[str]:
    head = ["| Setting | " + " | ".join(DIFFICULTIES) + " | All | Mean progress | Deaths " +
            " / ".join(f"({c})" for c in CLASSES) + " | Stuck runs |",
            "|---|" + "---|" * (len(DIFFICULTIES) + 5)]
    lines = []

    def row(label, g, draws=1, classes=True, stuck=True):
        cells = []
        for d in DIFFICULTIES:
            gd = g[g["difficulty"] == d]
            n = len(gd) // draws
            done = gd["completed"].astype(bool).sum() / draws
            cells.append(f"{done:g}/{n}" if n else "–")
        n = len(g) // draws
        dead = g[~g["completed"].astype(bool)]
        cls = " / ".join(str(int((dead["class"] == c).sum())) for c in CLASSES) if classes else "–"
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {g['completed'].astype(bool).sum() / draws:g}/{n} | "
                     f"{pct(g['progress'].mean())} | {cls} | {int(g['stuck'].sum()) if stuck else '–'} |")

    base = df[df["setting"] == BASELINE]
    if base["seed"].nunique() > 1:
        row(f"**baseline, seeds {', '.join(map(str, sorted(base['seed'].unique())))}**", base)
    for (name, seed), g in df.groupby(["setting", "seed"], sort=False):
        row(f"{name}, seed {seed}", g)
    for name in ("ideal fly (collision course)", "ideal fly (every object looms)"):
        g = refs[refs["setting"] == name]
        if len(g):
            row(f"{name} (no brain)", g.assign(stuck=False), stuck=False)
    nev = refs[refs["setting"] == "never press"]
    if len(nev):
        row("never press (the floor)", nev.assign(stuck=False), classes=False, stuck=False)
    rnd = refs[refs["setting"] == "random presses"]
    if len(rnd):
        row(f"random presses (chance), mean of {rnd['draw'].nunique()} draws", rnd.assign(stuck=False),
            draws=rnd["draw"].nunique(), classes=False, stuck=False)
    note = ("(s) stuck, (a) invisible, (c) short run-up, (b) the ideal fly dies there too, (d1) jumped earlier "
            "than the ideal fly, (d2) later, (d3) not at all. The ideal fly's own deaths have (a)/(b)/(c) only.")
    return head + lines + ["", note]


def per_level(df, refs) -> str:
    cell = lambda r: pct(r["progress"]) + ("" if r["completed"] else f" ({r['class']})")  # noqa: E731
    table = pd.DataFrame(index=sorted(set(df["level"])))
    for (name, seed), g in df.groupby(["setting", "seed"], sort=False):
        short = "baseline" if name == BASELINE else name.split(" (")[0]
        table[f"{short} s{seed}"] = pd.Series({r["level"]: cell(r) for r in g.to_dict("records")})
    base = df[df["setting"] == BASELINE]
    if base["seed"].nunique() > 1:
        table["baseline completed"] = base.groupby("level").apply(
            lambda g: f"{int(g['completed'].sum())}/{len(g)}", include_groups=False)
    for name, short in (("ideal fly (collision course)", "ideal fly"), ("never press", "never press")):
        g = refs[refs["setting"] == name]
        if len(g):
            table[short] = pd.Series({r["level"]: pct(r["progress"]) + ("" if r["completed"] else
                                      f" ({r['class']})" if r["class"] else "") for r in g.to_dict("records")})
    rnd = refs[refs["setting"] == "random presses"]
    if len(rnd):
        table["random presses"] = rnd.groupby("level").apply(
            lambda g: f"{pct(g['progress'].mean())}, {int(g['completed'].sum())}/{len(g)} done", include_groups=False)
    return md_table(table.fillna("–").rename_axis("level").reset_index(), 0)


def comparisons(df) -> list[str]:
    """D48: paired by level against the baseline at seed 0; the noise line from seeds 1 and 2."""
    ref = df[(df["setting"] == BASELINE) & (df["seed"] == 0)].set_index("level")
    pairs = [(name, seed) for name, seed in df[["setting", "seed"]].drop_duplicates().itertuples(index=False)
             if not (name == BASELINE and seed == 0)]
    lines = ["| Against the baseline, seed 0 | Levels | Better | Worse | Equal | Sign test p | Reading |",
             "|---|---|---|---|---|---|---|"]
    for name, seed in sorted(pairs, key=lambda p: p[0] == BASELINE):
        g = df[(df["setting"] == name) & (df["seed"] == seed)].set_index("level")
        both = [lv for lv in g.index if lv in ref.index]
        signs = [compare(g.loc[lv].to_dict(), ref.loc[lv].to_dict()) for lv in both]
        better, worse, equal = signs.count(1), signs.count(-1), signs.count(0)
        p = sign_test(better, worse)
        noise = name == BASELINE
        reading = ("noise line (reported only)" if noise else
                   "better" if p < 0.05 and better > worse else "worse" if p < 0.05 else "no clear difference")
        label = f"baseline, seed {seed}" if noise else f"{name}, seed {seed}"
        lines.append(f"| {label} | {len(both)} | {better} | {worse} | {equal} | {p:.3f} | {reading} |")
    lines += ["", "Equal = both completed, or both died on the same object (D48). Two-sided sign test, equal levels "
              "left out; \"better\" only at p < 0.05. The two comparisons are tested separately, with no correction "
              "for testing two. The noise line changes no rule: it shows what a change of seed does by itself."]
    return lines


def timing(df, appr) -> list[str]:
    lines = ["| Setting | Approaches | With a Giant Fiber spike | First-spike θ, mean ± s.d. | Median | "
             f"Within 39 ± {FLY_SD_DEG:g}° | Lone spikes jumped | In the window (gap 1–73) | Presses, nothing looming |",
             "|---|---|---|---|---|---|---|---|---|"]
    for (name, seed), a in appr.groupby(["setting", "seed"], sort=False):
        th = a["first_spike_theta"].dropna()
        lone = a[a["lone_spike"] & a["jump_gap"].notna()]
        within = ((th - THRESHOLD_DEG).abs() <= FLY_SD_DEG).mean() if len(th) else None
        nothing = int(df[(df["setting"] == name) & (df["seed"] == seed)]["nothing_looming_presses"].sum())
        lines.append(f"| {name}, seed {seed} | {len(a)} | {len(th)} | "
                     + (f"{th.mean():.1f} ± {th.std():.1f}° | {th.median():.1f}° | {pct(within)}" if len(th) else "– | – | –")
                     + f" | {len(lone)} | {int(lone['in_window'].sum())}/{len(lone)} | {nothing} |")
    lines += ["", f"Calibration (open loop): 39°, model s.d. {MODEL_SD_DEG:g}°; the real fly: 39 ± {FLY_SD_DEG:g}°. "
              "Closed loop should match the calibration; if it doesn't, that's a finding. θ is read per tick "
              "(4.2 ms), as in the calibration. Lone spikes: a one-cell ground spike with nothing from one cell "
              "before to four after, where the press window (gap 1–73 at the jump) is known."]
    stuck = appr[appr["stuck"]]["first_spike_theta"].dropna()
    normal = appr[~appr["stuck"]]["first_spike_theta"].dropna()
    if len(stuck):
        lines.append(f"\nFirst-spike θ in stuck stretches: {stuck.mean():.1f} ± {stuck.std():.1f}° ({len(stuck)} "
                     f"approaches), against {normal.mean():.1f} ± {normal.std():.1f}° ({len(normal)}) otherwise.")
    else:
        lines.append("\nNo approach started in a stuck stretch.")
    return lines


def stuck_section(df) -> list[str]:
    secs = df["seconds"].sum()
    flagged = int(df["stuck"].sum())
    lines = [f"- **Stuck runs:** {flagged} of {len(df)}; they count in every result above as they played out (D38).",
             f"- **Stuck rate:** {flagged / secs:.4f} runs flagged per simulated second ({secs:.0f} s simulated); "
             f"{100 * df['stuck_frames'].sum() / df['ticks'].sum():.2f}% of all frames had the stuck flag on."]
    if flagged:
        lines.append("- **With stuck runs left out:**")
        for (name, seed), g in df[~df["stuck"]].groupby(["setting", "seed"], sort=False):
            lines.append(f"  - {name}, seed {seed}: {int(g['completed'].sum())}/{len(g)} completed, "
                         f"mean progress {pct(g['progress'].mean())}")
    return lines


def replays(df) -> list[str]:
    """D48: replays for the write-up are picked by rule: the lowest-seed completed level, and the
    lowest-seed death of each class (ties: level name)."""
    base = df[df["setting"] == BASELINE].sort_values(["seed", "level"])
    lines = []
    done = base[base["completed"].astype(bool)]
    lines.append(f"- completed: {done.iloc[0]['level']}, seed {done.iloc[0]['seed']}" if len(done) else "- completed: none")
    for c in CLASSES:
        d = base[base["class"] == c]
        if len(d):
            lines.append(f"- ({c}): {d.iloc[0]['level']}, seed {d.iloc[0]['seed']}")
    return lines


def report(df, appr, refs, network, suite, expected) -> str:
    lines = [f"# Step 2: the untuned fly on {suite.replace('_', '-')} cube levels (`{network}`)\n",
             "Fly-driven closed loop, no tuning (D43). The baseline of record is θ_full = 200°, collision-course "
             "looming, R × f at R = 150 Hz, at seeds 0, 1 and 2; the comparisons (seed 0) sit beside it and never "
             "replace it. The ideal fly, never press and random presses have no brain (D44, D48). Analysis as fixed in D48.\n"]
    if suite != "held_out":
        lines.append("**Check only: these are training levels, not the Step 2 result.**\n")
    lines.append("## Runs read\n")
    for (name, seed), g in df.groupby(["setting", "seed"], sort=False):
        missing = sorted(set(expected) - set(g["level"])) if suite == "held_out" else []
        lines.append(f"- {name}, seed {seed}: {len(g)} runs" + (f"; **missing {len(missing)}: {', '.join(missing)}**" if missing else ""))
    commits = sorted(set(df["commit"]))
    lines.append(f"- Commits: {', '.join(commits)}" + ("  **(uncommitted changes)**" if any(c.endswith("-dirty") for c in commits) else ""))
    lines.append("- Every run replayed exactly from its logged presses.\n")
    lines += ["## Results\n", *results_table(df, refs), "", "## Per level (progress; death class)\n", per_level(df, refs),
              "", "## Comparisons\n", *comparisons(df), "", "## Timing per approach\n", *timing(df, appr),
              "", "## Stuck runs\n", *stuck_section(df), "", "## Replays for the write-up (picked by rule)\n", *replays(df),
              "", "## Deaths\n"]
    dead = df[~df["completed"].astype(bool)].copy()
    dead["progress"] = dead["progress"].map(pct)
    lines.append(md_table(dead[["setting", "seed", "level", "progress", "class", "killer_text", "why"]]
                          .rename(columns={"killer_text": "killed by"}).fillna("–"), 0))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--network", default="final")
    parser.add_argument("--suite", default="held_out", choices=["held_out", "training"])
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    df, appr = collect(args.network, args.suite)
    refs = references(args.network, args.suite, set(df["level"]))
    text = report(df, appr, refs, args.network, args.suite, suite_levels(args.suite))
    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / f"{args.network}_{args.suite}"
    df.to_csv(f"{stem}_runs.csv", index=False)
    appr.to_csv(f"{stem}_approaches.csv", index=False)
    (OUT / f"{stem.name}.md").write_text(text + "\n", encoding="utf-8")
    if args.suite == "held_out":  # blind (D33): opened together, after the training check
        print(f"Wrote {stem.relative_to(ROOT)}.md, _runs.csv and _approaches.csv (outcomes not shown)")
    else:
        print(text)


if __name__ == "__main__":
    main()
