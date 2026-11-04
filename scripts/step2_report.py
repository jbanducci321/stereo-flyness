"""The Step 2 report (D48): the untuned fly on the held-out cube levels, read against the references.

Reads the fly-driven runs from scripts/play_cube.py (baseline at seeds 0-2, the two comparisons
at seed 0), the ideal fly from scripts/ideal_fly.py and the no-brain references from
scripts/reference_flies.py. Every run is first replayed from its logged presses and must rebuild
the recording exactly (else the report stops). Then, all as fixed in D48:
- **Results:** runs completed (of 60, per level of 3, and seed 0 alone), mean progress, by difficulty.
- **Death classes,** from the last approach where the cube could still jump: (s) stuck, (c) short
  run-up, (a)/(b) the ideal fly dies there too (on something that never loomed / that did),
  (d1/d2/d3) the fly's timing: jumped earlier / later / not at all, (u) unclassified
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
    note = ("(s) stuck; from the last approach where the cube could still jump: (c) short run-up; the ideal 39° fly "
            "dies there too, (a) on something that never loomed in its game, (b) on something that did; or the "
            "fly's timing: (d1) jumped earlier than the ideal fly, (d2) later, (d3) not at all; (u) unclassified (D48). "
            "The ideal fly's own rows use D44's (a)/(b)/(c).")
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
                                      f" ({r['class']})" if isinstance(r["class"], str) else "") for r in g.to_dict("records")})
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


CARRY_OVER_MS = 150  # descriptive split for the leftover-activity check, chosen on training runs; decides nothing


def leftover(appr, svg_name) -> list[str]:
    """Shannyn's leftover-activity check (2026-11-03, exploratory): is the first spike earlier when
    the Giant Fiber fired recently? The model has no adaptation, so activity from the previous
    object could carry into the next approach. Baseline runs only."""
    a = appr[(appr["setting"] == BASELINE) & appr["first_spike_theta"].notna()]
    if a.empty:
        return ["No baseline approach with a Giant Fiber spike."]
    bins = [(None, "never fired before"), ((0, CARRY_OVER_MS), f"< {CARRY_OVER_MS} ms"), ((CARRY_OVER_MS, 300), f"{CARRY_OVER_MS}–300 ms"),
            ((300, 450), "300–450 ms"), ((450, np.inf), "≥ 450 ms")]
    lines = ["| Giant Fiber last fired before the approach | Approaches | First-spike θ, mean ± s.d. | Median | "
             "First spike, median ticks into the approach | Start θ, median |", "|---|---|---|---|---|---|"]
    for rng, label in bins:
        g = a[a["since_gf_ms"].isna()] if rng is None else a[(a["since_gf_ms"] >= rng[0]) & (a["since_gf_ms"] < rng[1])]
        if len(g):
            th = g["first_spike_theta"]
            lines.append(f"| {label} | {len(g)} | {th.mean():.1f} ± {th.std():.1f}° | {th.median():.1f}° | "
                         f"{g['first_spike_tick'].median():g} | {g['theta_start'].median():.1f}° |")
    carry = a["since_gf_ms"] < CARRY_OVER_MS
    fresh = a[~carry]["first_spike_theta"]
    quiet = a[~carry & a["since_gf_ms"].notna()]
    rho = quiet["since_gf_ms"].rank().corr(quiet["first_spike_theta"].rank()) if len(quiet) > 2 else float("nan")
    rho_start = quiet["theta_start"].rank().corr(quiet["first_spike_theta"].rank()) if len(quiet) > 2 else float("nan")
    prev = a.dropna(subset=["since_prev_ms"])
    back_to_back = prev[prev["since_prev_ms"] == 0]["first_spike_theta"]
    gap_before = prev[prev["since_prev_ms"] > 0]["first_spike_theta"]
    lines += ["",
              f"- **Carry-over:** {int(carry.sum())} of {len(a)} approaches ({carry.mean():.0%}) start while the Giant Fiber "
              f"is still firing from the previous object (last spike < {CARRY_OVER_MS} ms before). Their first spike comes "
              "in the first few ticks, at whatever θ the new object has then: a burst carrying over, not a response to it.",
              f"- **Without them:** first-spike θ {fresh.mean():.1f} ± {fresh.std():.1f}° (n {len(fresh)}), against the "
              f"open-loop calibration's 38.0 ± 6.3° at 150 Hz (D49 draft) and {a['first_spike_theta'].mean():.1f}° with them.",
              f"- **No graded effect beyond that:** rank correlation of first-spike θ with time since the last spike "
              f"{rho:+.2f} (n {len(quiet)}), and with the θ the approach starts at {rho_start:+.2f}.",
              f"- By time since the previous approach ended: back to back (0 ms) {back_to_back.mean():.1f}° (n {len(back_to_back)}), "
              f"after a gap {gap_before.mean():.1f}° (n {len(gap_before)}).",
              f"- The {CARRY_OVER_MS} ms split is descriptive, chosen on training runs; it decides nothing. "
              f"Plot: `{svg_name}` (first-spike θ against time since the Giant Fiber last fired)."]
    return lines


def leftover_svg(appr) -> str:
    """A small scatter plot, no plotting library: first-spike θ against time since the Giant Fiber
    last fired (log scale), coloured by the θ the approach started at."""
    a = appr[(appr["setting"] == BASELINE) & appr["first_spike_theta"].notna() & appr["since_gf_ms"].notna()]
    w, h, left, bottom, top, right = 640, 360, 60, 40, 20, 20
    x0, x1, y1 = np.log10(4), np.log10(2000), 90
    sx = lambda v: left + (np.log10(max(v, 4)) - x0) / (x1 - x0) * (w - left - right)  # noqa: E731
    sy = lambda v: h - bottom - min(v, y1) / y1 * (h - top - bottom)  # noqa: E731
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="sans-serif" font-size="11">',
           f'<rect width="{w}" height="{h}" fill="white"/>']
    for ms in (10, 30, 100, 300, 1000):
        out.append(f'<line x1="{sx(ms):.1f}" y1="{top}" x2="{sx(ms):.1f}" y2="{h - bottom}" stroke="#ddd"/>'
                   f'<text x="{sx(ms):.1f}" y="{h - bottom + 14}" text-anchor="middle">{ms}</text>')
    for deg in (0, 20, 39, 60, 80):
        out.append(f'<line x1="{left}" y1="{sy(deg):.1f}" x2="{w - right}" y2="{sy(deg):.1f}" '
                   f'stroke="{"#999" if deg == 39 else "#eee"}"{" stroke-dasharray=\"4 3\"" if deg == 39 else ""}/>'
                   f'<text x="{left - 6}" y="{sy(deg) + 4:.1f}" text-anchor="end">{deg}°</text>')
    sx_c = lambda v: sx(v) if not pd.isna(v) else left  # noqa: E731
    for r in a.itertuples():
        colour = "#1f77b4" if r.theta_start < 8 else "#d62728"
        out.append(f'<circle cx="{sx_c(r.since_gf_ms):.1f}" cy="{sy(r.first_spike_theta):.1f}" r="2.5" fill="{colour}" fill-opacity="0.6"/>')
    out += [f'<line x1="{sx(CARRY_OVER_MS):.1f}" y1="{top}" x2="{sx(CARRY_OVER_MS):.1f}" y2="{h - bottom}" stroke="#555" stroke-dasharray="2 3"/>',
            f'<text x="{(left + w - right) / 2}" y="{h - 8}" text-anchor="middle">time since the Giant Fiber last fired (ms, log scale)</text>',
            f'<text x="14" y="{(top + h - bottom) / 2}" text-anchor="middle" transform="rotate(-90 14 {(top + h - bottom) / 2})">first-spike θ</text>',
            f'<text x="{w - right}" y="{top + 12}" text-anchor="end"><tspan fill="#1f77b4">● starts below 8°</tspan>  '
            '<tspan fill="#d62728">● starts at 8° or more</tspan>  dashed: 39° and the 150 ms split</text>', "</svg>"]
    return "\n".join(out)


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
              "", "## Leftover activity (exploratory check, added before the held-out results were opened)\n",
              *leftover(appr, f"{network}_{suite}_leftover.svg"), "", "## Stuck runs\n", *stuck_section(df), "", "## Replays for the write-up (picked by rule)\n", *replays(df),
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
    (OUT / f"{stem.name}_leftover.svg").write_text(leftover_svg(appr), encoding="utf-8")
    (OUT / f"{stem.name}.md").write_text(text + "\n", encoding="utf-8")
    if args.suite == "held_out":  # blind (D33): opened together, after the training check
        print(f"Wrote {stem.relative_to(ROOT)}.md, _runs.csv and _approaches.csv (outcomes not shown)")
    else:
        print(text)


if __name__ == "__main__":
    main()
