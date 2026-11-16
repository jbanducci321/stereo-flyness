"""The fix 1, step 4 report: the held-out opening (docs/notes/fix1_heldout_plan.md).

Fixed before any run. Checks first, then the verdicts:
- **checks:** every one of the 360 runs present (the 40 iteration-2 held-out levels and iteration 1's 20
  held-out cube levels, x 2 arms x seeds 0-2); right driver, suite, seed and encoding; one clean commit
  (no "-dirty") across all of them; every run replays exactly from its logged holds; stuck runs counted,
  not re-run; and, per level and seed, the two arms identical up to the first frame fix 1 changed
  (its logged `predicted` flag), so identical throughout where it changed none (Shannyn, 2026-11-16).
  If any check fails, nothing is reported, only what failed.
- **1. the test (D55's bar), iteration-2 held-out:** step 3's main measure (gets past the first fix-case
  drop, at least 2 of 3 seeds), fixed vs unfixed, two-sided sign test, p < 0.05; beside it, as step 3.
- **2. the no-harm check, iteration 1's held-out cube levels:** each level's median (over seeds) of
  obstacle groups passed, fixed vs unfixed; no significant drop, and worse on no more levels than better;
  jumps while on top of plain step-downs; completions, progress, deaths; the frames fix 1 changed per
  level, and the levels where it changed any, with what happened. Beside it: whether the fresh
  unfixed runs match Part 1's Step 4 intact runs tick for tick (reported, not used to judge).
- **fix 1 counts** only if it passes both.

Usage:
    uv run python scripts/fix1_heldout_report.py            # writes results/iteration2/fix1_heldout_report.md
    uv run python scripts/fix1_heldout_report.py --show     # and prints it
"""

import argparse
import json
import sys
import tomllib
from pathlib import Path

import pandas as pd

from analyse_pathway_tests import md_table
from inspect_encoding import LEVELS as IT1_LEVELS
from inspect_encoding import job
from stereo_flyness.experiments.fix1_heldout import arms_diverge, bar_verdict, compare, groups_passed, level_score, no_harm_verdict
from stereo_flyness.experiments.fix1_step3 import drop_k, level_past, read_run, replay_jumps
from stereo_flyness.experiments.obstacles import groups
from stereo_flyness.game.suites import load_level

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results" / "iteration2" / "closed_loop"
PART1 = ROOT / "results" / "closed_loop"
OUT = ROOT / "results" / "iteration2" / "fix1_heldout_report.md"
SEEDS = (0, 1, 2)
ARMS = {"unfixed": "", "fix1 (ii)": "_fix1-ii"}
SUITES = {  # levels folder, suite, runs subfolder (play_level.py's out_base), level count
    "test": {"levels": ROOT / "results" / "iteration2" / "levels", "suite": "held_out", "sub": "held_out", "n": 40},
    "no_harm": {"levels": IT1_LEVELS, "suite": "held_out", "sub": "iteration1_held_out", "n": 20},
}


def settings_name(arm: str, seed: int) -> str:
    theta = tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())["theta_full_deg"]
    return f"{theta:g}deg_collision{ARMS[arm]}_R150{'' if seed == 0 else f'_seed{seed}'}"


def run_dir(network: str, key: str, arm: str, seed: int) -> Path:
    return RUNS / network / SUITES[key]["sub"] / settings_name(arm, seed) / "fly"


def part1_dir(network: str, seed: int) -> Path:
    """Part 1's Step 4 intact whole-brain runs on iteration 1's held-out cube levels (D51)."""
    return PART1 / network / "held_out" / f"200deg_collision_R150{'' if seed == 0 else f'_seed{seed}'}_step4" / "fly"


def names(key: str) -> list[str]:
    s = SUITES[key]
    return sorted(p.stem for p in (s["levels"] / s["suite"]).glob("cube-*.json") if not p.stem.endswith(".meta"))


def collect(network: str, key: str):
    s, rows, problems, commits = SUITES[key], [], [], set()
    for arm in ARMS:
        for seed in SEEDS:
            base = run_dir(network, key, arm, seed)
            for name in names(key):
                d, where = base / name, f"{key}, {arm}, seed {seed}, {name}"
                if not (d / "run.json").exists():
                    problems.append(f"{where}: missing")
                    continue
                run = json.loads((d / "run.json").read_text(encoding="utf-8"))
                view = run.get("view")
                if run.get("driver") != "fly" or run.get("seed") != seed or run.get("rate_hz") != 150.0 \
                        or run.get("suite") != s["suite"] \
                        or (arm == "unfixed") != (view is None) or (arm != "unfixed" and view != "landing"):
                    problems.append(f"{where}: wrong settings")
                    continue
                commits.add(run.get("commit", ""))
                level, _ = load_level(s["levels"], job(name, s["suite"]))
                held = pd.read_parquet(d / "ticks.parquet")["held"].to_numpy(bool)
                try:
                    game, jumps = replay_jumps(level, held)
                except ValueError as e:
                    problems.append(f"{where}: {e}")
                    continue
                if game.finished != run["completed"] or abs(game.progress - run["progress"]) > 1e-9:
                    problems.append(f"{where}: the replay doesn't match the record")
                    continue
                pred = pd.read_parquet(d / "brain.parquet", columns=["predicted"])["predicted"].to_numpy(bool)                     if arm != "unfixed" else None
                gs = groups(level)
                r = read_run(gs, game.finished, None if game.death is None else game.death.x, jumps)
                rows.append({"suite": key, "arm": arm, "seed": seed, "level": name, "completed": game.finished,
                             "progress": game.progress, "stuck": run.get("stuck_from_frame") is not None,
                             "reading": r, "groups": gs, "passed": groups_passed(r.outs), "held": held,
                             "predicted": pred, "changed": None if pred is None else int(pred.sum())})
    return rows, problems, commits


def identical_until_changed(rows) -> list[str]:
    """Same level and seed: the fixed run's holds equal the unfixed run's up to the first frame fix 1
    changed, and throughout if it changed none (the two arms then get identical input)."""
    unfixed = {(r["suite"], r["level"], r["seed"]): r["held"] for r in rows if r["arm"] == "unfixed"}
    problems = []
    for r in rows:
        if r["arm"] == "unfixed" or (r["suite"], r["level"], r["seed"]) not in unfixed:
            continue
        why = arms_diverge(unfixed[(r["suite"], r["level"], r["seed"])], r["held"], r["predicted"])
        if why:
            problems.append(f"{r['suite']}, seed {r['seed']}, {r['level']}: {why}")
    return problems


def changed_by_level(rows) -> dict[str, str]:
    """Frames fix 1 changed, per level, as 'seed 0/1/2'."""
    out = {}
    for r in sorted((r for r in rows if r["arm"] != "unfixed"), key=lambda r: r["seed"]):
        out.setdefault(r["level"], []).append(str(r["changed"]))
    return {lv: " / ".join(v) for lv, v in out.items()}


def changed_line(rows) -> str:
    ch = changed_by_level(rows)
    any_ = [lv for lv, v in ch.items() if any(int(x) for x in v.split(" / "))]
    return (f"- Fix 1 changed the input (frames shown via its predicted path) on **{len(any_)}** of {len(ch)} levels "
            f"(any seed). On the other {len(ch) - len(any_)}, both arms got identical input and played identically "
            "(checked), so only the levels it changed can differ.")


def part1_match(network: str, rows) -> tuple[int, int, list[str]]:
    """Fresh unfixed runs on iteration 1's held-out levels against Part 1's, tick for tick."""
    same, total, missing = 0, 0, []
    for r in rows:
        if r["suite"] != "no_harm" or r["arm"] != "unfixed":
            continue
        f = part1_dir(network, r["seed"]) / r["level"] / "ticks.parquet"
        if not f.exists():
            missing.append(f"seed {r['seed']}, {r['level']}")
            continue
        total += 1
        old = pd.read_parquet(f)["held"].to_numpy(bool)
        same += len(old) == len(r["held"]) and bool((old == r["held"]).all())
    return same, total, missing


def common_tables(rows) -> list[str]:
    """Drops by k and width, no harm, progress, completions, stuck runs, deaths: as step 3."""
    lines, drops = [], []
    for r in rows:
        for g, o in zip(r["groups"], r["reading"].outs):
            if o != "not reached" and ("drop" in g.type or "step_down_pits" in g.type):
                drops.append({"arm": r["arm"], "case": "fix" if g.type.endswith("(fix)") else "control",
                              "k": drop_k(g), "pits": sum(b.kind == "pit" for b in g.boxes), "cleared": o == "cleared"})
    dd = pd.DataFrame(drops)
    if len(dd):
        t = dd.groupby(["case", "k", "arm"])["cleared"].agg(["sum", "count"]).reset_index()
        t["cleared"] = t["sum"].astype(int).astype(str) + " / " + t["count"].astype(str)
        lines += ["**Every drop reached, by k** (ground cells before the pits):", "",
                  md_table(t[["case", "k", "arm", "cleared"]], 0), ""]
        fix = dd[dd["case"] == "fix"]
        if len(fix):
            w = fix.groupby(["pits", "arm"])["cleared"].agg(["sum", "count"]).reset_index()
            w["cleared"] = w["sum"].astype(int).astype(str) + " / " + w["count"].astype(str)
            lines += ["**Fix-case drops reached, by pit width (cells):**", "", md_table(w[["pits", "arm", "cleared"]], 0), ""]
    df, summary = pd.DataFrame(rows), []
    for arm, d in df.groupby("arm"):
        done = d.groupby("level")["completed"].sum()
        summary.append({"arm": arm, "runs": len(d), "runs completed": int(d["completed"].sum()),
                        "levels completed (2 of 3 seeds)": int((done >= 2).sum()),
                        "median progress (per level, median)": f"{100 * d.groupby('level')['progress'].median().median():.1f}%",
                        "plain step-downs reached": sum(r.plain_reached for r in d["reading"]),
                        "jumps while on top": sum(r.plain_jumps for r in d["reading"]),
                        "stuck runs": int(d["stuck"].sum())})
    lines += ["**No harm at plain step-downs, progress, completions, stuck runs:**", "",
              md_table(pd.DataFrame(summary), 0), ""]
    deaths = [{"arm": r["arm"], "type": g.type} for r in rows
              for g, o in zip(r["groups"], r["reading"].outs) if o == "died"]
    if deaths:
        t = pd.DataFrame(deaths).value_counts().unstack("arm", fill_value=0).reset_index()
        lines += ["**Deaths by obstacle type (all runs):**", "", md_table(t, 0), ""]
    return lines


def test_section(rows) -> tuple[list[str], bool]:
    df = pd.DataFrame(rows)
    per = {}
    for (arm, level), d in df.groupby(["arm", "level"]):
        pasts = [r.past for r in d["reading"]]
        per[(arm, level)] = None if pasts[0] is None else level_past(pasts)
    levels = sorted(df["level"].unique())
    feat_levels = [lv for lv in levels if per[("unfixed", lv)] is not None]
    better = sum(per[("fix1 (ii)", lv)] and not per[("unfixed", lv)] for lv in feat_levels)
    worse = sum(per[("unfixed", lv)] and not per[("fix1 (ii)", lv)] for lv in feat_levels)
    passes, p = bar_verdict(better, worse)
    lines = ["## 1. The test (D55's bar): iteration-2 held-out levels", "",
             f"- Levels with a fix-case drop: **{len(feat_levels)}** of {len(levels)} "
             f"({len(levels) - len(feat_levels)} left out: no fix-case drop).",
             f"- Get past it (at least 2 of 3 seeds): unfixed **{sum(per[('unfixed', lv)] for lv in feat_levels)}**, "
             f"fix 1 (ii) **{sum(per[('fix1 (ii)', lv)] for lv in feat_levels)}**.",
             f"- Fixed better on **{better}**, worse on **{worse}**, tied on {len(feat_levels) - better - worse}; "
             f"two-sided sign test p = **{p:.3g}**.",
             f"- **The test: {'PASSED' if passes else 'NOT PASSED'}** (needs more levels better than worse, p < 0.05).",
             changed_line(rows), ""]
    ch = changed_by_level(rows)
    feat = []
    for lv in feat_levels:
        r0 = df[df["level"] == lv].iloc[0]
        g = r0["groups"][r0["reading"].feature]
        seeds = {arm: sum(r.past for r in df[(df["level"] == lv) & (df["arm"] == arm)]["reading"]) for arm in ARMS}
        feat.append({"level": lv, "feature": g.type.split(" (")[0], "k": drop_k(g),
                     "pits": sum(b.kind == "pit" for b in g.boxes), "frames changed (seeds 0/1/2)": ch[lv],
                     "unfixed (seeds past)": f"{seeds['unfixed']}/{len(SEEDS)}",
                     "fix 1 (ii) (seeds past)": f"{seeds['fix1 (ii)']}/{len(SEEDS)}",
                     "result": ("better" if per[("fix1 (ii)", lv)] and not per[("unfixed", lv)]
                                else "worse" if per[("unfixed", lv)] and not per[("fix1 (ii)", lv)] else "tied")})
    if feat:
        ft = pd.DataFrame(feat).sort_values(["k", "level"])
        by_k = ft.groupby("k")["result"].value_counts().unstack(fill_value=0).reset_index()
        lines += ["**By the feature's k:**", "", md_table(by_k, 0), "", "**Each level's feature:**", "", md_table(ft, 0), ""]
    return lines + common_tables(rows), passes


def no_harm_section(rows, match) -> tuple[list[str], bool]:
    df = pd.DataFrame(rows)
    score = {arm: {lv: level_score(list(d["passed"])) for lv, d in df[df["arm"] == arm].groupby("level")} for arm in ARMS}
    better, worse, tied = compare(score["fix1 (ii)"], score["unfixed"])
    no_drop, not_worse, p = no_harm_verdict(better, worse)
    jumps = {arm: sum(r.plain_jumps for r in df[df["arm"] == arm]["reading"]) for arm in ARMS}
    lines = ["## 2. The no-harm check: iteration 1's held-out cube levels", "",
             "*These levels were seen in Part 1, so this is a check, not a test (D55).*", "",
             f"- Each level's score: the median, over 3 seeds, of obstacle groups passed. Fixed better on **{better}**, "
             f"worse on **{worse}**, tied on {tied}; two-sided sign test p = **{p:.3g}**.",
             f"- (a) No significant drop: **{'yes' if no_drop else 'NO'}**. "
             f"(b) Worse on no more levels than better: **{'yes' if not_worse else 'NO'}**.",
             f"- Jumps while on top of a plain step-down: unfixed {jumps['unfixed']}, fix 1 (ii) {jumps['fix1 (ii)']}.",
             f"- **The no-harm check: {'PASSED' if no_drop and not_worse else 'NOT PASSED'}** (a and b).",
             changed_line(rows), ""]
    ch = changed_by_level(rows)
    table = pd.DataFrame([{"level": lv, "frames changed (seeds 0/1/2)": ch[lv],
                           "unfixed (median groups passed)": score["unfixed"][lv],
                           "fix 1 (ii)": score["fix1 (ii)"][lv],
                           "result": "better" if score["fix1 (ii)"][lv] > score["unfixed"][lv]
                           else "worse" if score["fix1 (ii)"][lv] < score["unfixed"][lv] else "tied"}
                          for lv in sorted(score["unfixed"]) if any(int(x) for x in ch[lv].split(" / "))])
    same, total, missing = match
    lines += ["**The levels where fix 1 changed any frame** (the rest tie exactly):", "",
              md_table(table, 1) if len(table) else "None.", ""] + common_tables(rows) + [
        f"**Beside it, not used to judge:** the fresh unfixed runs match Part 1's Step 4 intact runs tick for tick "
        f"on **{same} of {total}**" + (f" ({len(missing)} of Part 1's runs not found)" if missing else "") + ".", ""]
    return lines, no_drop and not_worse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--network", default="whole_brain")
    parser.add_argument("--show", action="store_true", help="print the report as well as writing it")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    for key, s in SUITES.items():
        if len(names(key)) != s["n"]:
            sys.exit(f"Expected {s['n']} levels for {key}, found {len(names(key))}.")
    rows, problems, commits = [], [], set()
    for key in SUITES:
        r, p, c = collect(args.network, key)
        rows, problems, commits = rows + r, problems + p, commits | c
    if not problems:
        problems += identical_until_changed(rows)
    if len(commits) != 1 or any(c.endswith("-dirty") or not c for c in commits):
        problems.append(f"runs aren't from one clean commit: {sorted(commits)}")
    if problems:
        sys.exit("Checks failed, nothing reported:\n- " + "\n- ".join(problems[:40])
                 + (f"\n- ... and {len(problems) - 40} more" if len(problems) > 40 else ""))
    commit = next(iter(commits))
    test_lines, test_ok = test_section([r for r in rows if r["suite"] == "test"])
    nh = [r for r in rows if r["suite"] == "no_harm"]
    nh_lines, nh_ok = no_harm_section(nh, part1_match(args.network, nh))
    jumps = {arm: sum(r["reading"].plain_jumps for r in rows if r["arm"] == arm) for arm in ARMS}
    jumps_ok = jumps["fix1 (ii)"] <= jumps["unfixed"]
    counts = "counts" if test_ok and nh_ok and jumps_ok else "does not count by our bar"
    verdict = ["## Verdict", "",
               f"- The test (section 1): **{'passed' if test_ok else 'not passed'}**.",
               f"- The no-harm check (section 2): **{'passed' if nh_ok else 'not passed'}**.",
               f"- Fix 1's own condition, jumps while on top of a plain step-down, both suites: unfixed {jumps['unfixed']}, "
               f"fix 1 (ii) {jumps['fix1 (ii)']}: **{'met' if jumps_ok else 'NOT met'}**.",
               f"- **Fix 1 {counts}.**", ""]
    lines = ["# Fix 1, step 4: the held-out opening", "",
             "*Exploratory: interface adjusted after seeing Stereo Madness; brain wiring unchanged (D55). "
             f"Whole brain, the fly of record, seeds {', '.join(map(str, SEEDS))}, commit `{commit}`. "
             "Measures fixed in docs/notes/fix1_heldout_plan.md before any run. The iteration-2 held-out suite is "
             "opened once. Read in order: section 1, section 2, then the verdict.*", ""] + test_lines + nh_lines + verdict
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines) if args.show else f"Wrote {OUT} (all checks passed).")


if __name__ == "__main__":
    main()
