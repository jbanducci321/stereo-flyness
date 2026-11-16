"""The fix 1, step 3 report: the fly on the iteration-2 training levels, with and without fix 1 (ii).

Fixed before the runs (docs/notes/fix1_step3_plan.md). Checks first, then the measures:
- **checks:** every one of the 300 runs present (50 levels x 2 arms x seeds 0-2); right driver,
  seed and encoding; one clean commit (no "-dirty"); every run replays exactly from its logged
  holds; stuck runs counted, not re-run. If any check fails, nothing is reported, only what failed.
- **main measure:** levels that get past their first fix-case drop (at least 2 of 3 seeds), fixed vs
  unfixed, sign test (descriptive on training levels; D55's bar is the held-out suite);
- **beside it:** each level's feature with its k; every fix-case drop reached, by k and pit width;
  controls; jumps while on top of a plain step-down (no harm; any jump on top, not only at the edge);
  progress, completions, deaths by obstacle type, stuck runs.

Usage:
    uv run python scripts/fix1_step3_report.py            # writes results/iteration2/fix1_step3_report.md
    uv run python scripts/fix1_step3_report.py --show     # and prints it
"""

import argparse
import json
import sys
import tomllib
from pathlib import Path

import pandas as pd

from analyse_pathway_tests import md_table
from inspect_encoding import job
from stereo_flyness.experiments.fix1_step3 import drop_k, level_past, read_run, replay_jumps, sign_test
from stereo_flyness.experiments.obstacles import groups
from stereo_flyness.game.suites import load_level

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ROOT / "results" / "iteration2" / "levels"
RUNS = ROOT / "results" / "iteration2" / "closed_loop"
OUT = ROOT / "results" / "iteration2" / "fix1_step3_report.md"
SEEDS = (0, 1, 2)
ARMS = {"unfixed": "", "fix1 (ii)": "_fix1-ii"}


def run_dir(network: str, arm: str, seed: int) -> Path:
    theta = tomllib.loads((ROOT / "configs" / "recruitment.toml").read_text())["theta_full_deg"]
    return (RUNS / network / f"{theta:g}deg_collision{ARMS[arm]}_R150{'' if seed == 0 else f'_seed{seed}'}"
            / "fly")


def collect(network: str, names: list[str]):
    rows, problems, commits = [], [], set()
    for arm in ARMS:
        for seed in SEEDS:
            base = run_dir(network, arm, seed)
            for name in names:
                d = base / name
                if not (d / "run.json").exists():
                    problems.append(f"{arm}, seed {seed}, {name}: missing")
                    continue
                run = json.loads((d / "run.json").read_text(encoding="utf-8"))
                view = run.get("view")
                if run.get("driver") != "fly" or run.get("seed") != seed or run.get("rate_hz") != 150.0 \
                        or (arm == "unfixed") != (view is None) or (arm != "unfixed" and view != "landing"):
                    problems.append(f"{arm}, seed {seed}, {name}: wrong settings")
                    continue
                commits.add(run.get("commit", ""))
                level, _ = load_level(LEVELS, job(name, "training"))
                held = pd.read_parquet(d / "ticks.parquet")["held"].to_numpy(bool)
                try:
                    game, jumps = replay_jumps(level, held)
                except ValueError as e:
                    problems.append(str(e))
                    continue
                if game.finished != run["completed"] or abs(game.progress - run["progress"]) > 1e-9:
                    problems.append(f"{arm}, seed {seed}, {name}: the replay doesn't match the record")
                    continue
                gs = groups(level)
                r = read_run(gs, game.finished, None if game.death is None else game.death.x, jumps)
                rows.append({"arm": arm, "seed": seed, "level": name, "difficulty": name.split("-")[1],
                             "completed": game.finished, "progress": game.progress,
                             "stuck": run.get("stuck_from_frame") is not None, "reading": r, "groups": gs})
    if len(commits) != 1 or any(c.endswith("-dirty") or not c for c in commits):
        problems.append(f"runs aren't from one clean commit: {sorted(commits)}")
    return rows, problems, commits


def report(rows, commit) -> list[str]:
    df = pd.DataFrame(rows)
    lines = ["# Fix 1, step 3: the fly on the iteration-2 training levels", "",
             "*Exploratory: interface adjusted after seeing Stereo Madness; brain wiring unchanged (D55). "
             f"Whole brain, the record's settings, seeds {', '.join(map(str, SEEDS))}, commit `{commit}`. "
             "Measures fixed in docs/notes/fix1_step3_plan.md before any run. Descriptive: D55's bar is the "
             "held-out suite.*", ""]

    # main measure
    per = {}
    for (arm, level), d in df.groupby(["arm", "level"]):
        pasts = [r.past for r in d["reading"]]
        per[(arm, level)] = None if pasts[0] is None else level_past(pasts)
    levels = sorted(df["level"].unique())
    with_feature = [lv for lv in levels if per[("unfixed", lv)] is not None]
    better = sum(per[("fix1 (ii)", lv)] and not per[("unfixed", lv)] for lv in with_feature)
    worse = sum(per[("unfixed", lv)] and not per[("fix1 (ii)", lv)] for lv in with_feature)
    lines += ["## Main measure: gets past the feature (first fix-case drop, at least 2 of 3 seeds)", "",
              f"- Levels with a fix-case drop: **{len(with_feature)}** of {len(levels)} "
              f"({len(levels) - len(with_feature)} left out: no fix-case drop).",
              f"- Get past it: unfixed **{sum(per[('unfixed', lv)] for lv in with_feature)}**, "
              f"fix 1 (ii) **{sum(per[('fix1 (ii)', lv)] for lv in with_feature)}**.",
              f"- Fixed better on **{better}**, worse on **{worse}**, tied on {len(with_feature) - better - worse}; "
              f"sign test p = **{sign_test(better, worse):.3g}** (descriptive).", ""]

    # each level's feature, with its k (Shannyn, 2026-11-15: helps read ties, e.g. k = 2)
    feat = []
    for lv in with_feature:
        r0 = df[(df["level"] == lv)].iloc[0]
        g = r0["groups"][r0["reading"].feature]
        seeds = {arm: sum(r.past for r in df[(df["level"] == lv) & (df["arm"] == arm)]["reading"]) for arm in ARMS}
        feat.append({"level": lv, "feature": g.type.split(" (")[0], "k": drop_k(g),
                     "pits": sum(b.kind == "pit" for b in g.boxes),
                     "unfixed (seeds past)": f"{seeds['unfixed']}/{len(SEEDS)}",
                     "fix 1 (ii) (seeds past)": f"{seeds['fix1 (ii)']}/{len(SEEDS)}",
                     "result": ("better" if per[("fix1 (ii)", lv)] and not per[("unfixed", lv)]
                                else "worse" if per[("unfixed", lv)] and not per[("fix1 (ii)", lv)] else "tied")})
    ft = pd.DataFrame(feat).sort_values(["k", "level"])
    by_k = ft.groupby("k")["result"].value_counts().unstack(fill_value=0).reset_index()
    lines += ["**By the feature's k** (ground cells before the pits; all levels kept, as the measure is fixed):", "",
              md_table(by_k, 0), "", "**Each level's feature:**", "", md_table(ft, 0), ""]

    # every fix-case drop reached, by k and width; controls
    drops = []
    for r in rows:
        for g, o in zip(r["groups"], r["reading"].outs):
            if o != "not reached" and ("drop" in g.type or "step_down_pits" in g.type):
                drops.append({"arm": r["arm"], "case": "fix" if g.type.endswith("(fix)") else "control",
                              "k": drop_k(g), "pits": sum(b.kind == "pit" for b in g.boxes), "cleared": o == "cleared"})
    dd = pd.DataFrame(drops)
    if len(dd):
        t = dd.groupby(["case", "k", "arm"])["cleared"].agg(["sum", "count"]).reset_index()
        t["cleared"] = t["sum"].astype(int).astype(str) + " / " + t["count"].astype(str)
        lines += ["## Every drop reached, by k (ground cells before the pits)", "",
                  md_table(t[["case", "k", "arm", "cleared"]], 0), ""]
        w = dd[dd["case"] == "fix"].groupby(["pits", "arm"])["cleared"].agg(["sum", "count"]).reset_index()
        w["cleared"] = w["sum"].astype(int).astype(str) + " / " + w["count"].astype(str)
        lines += ["## Fix-case drops reached, by pit width (cells)", "", md_table(w[["pits", "arm", "cleared"]], 0), ""]

    # no harm, progress, completions, stuck
    rows2 = []
    for arm, d in df.groupby("arm"):
        reached = sum(r.plain_reached for r in d["reading"])
        jumps = sum(r.plain_jumps for r in d["reading"])
        med = d.groupby("level")["progress"].median()
        rows2.append({"arm": arm, "runs": len(d), "completed": int(d["completed"].sum()),
                      "median progress (per level, median)": f"{100 * med.median():.1f}%",
                      "plain step-downs reached": reached, "jumps while on top": jumps, "stuck runs": int(d["stuck"].sum())})
    lines += ["## No harm, progress, completions, stuck runs", "", md_table(pd.DataFrame(rows2), 0), ""]

    # deaths by obstacle type
    deaths = []
    for r in rows:
        for g, o in zip(r["groups"], r["reading"].outs):
            if o == "died":
                deaths.append({"arm": r["arm"], "type": g.type})
    if deaths:
        t = pd.DataFrame(deaths).value_counts().unstack("arm", fill_value=0).reset_index()
        lines += ["## Deaths by obstacle type (all runs)", "", md_table(t, 0), ""]
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--network", default="whole_brain")
    parser.add_argument("--show", action="store_true", help="print the report as well as writing it")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    names = sorted(p.stem for p in (LEVELS / "training").glob("cube-*.json") if not p.stem.endswith(".meta"))
    if len(names) != 50:
        sys.exit(f"Expected the 50 frozen iteration-2 training levels, found {len(names)}.")
    rows, problems, commits = collect(args.network, names)
    if problems:
        sys.exit("Checks failed, nothing reported:\n- " + "\n- ".join(problems[:40])
                 + (f"\n- ... and {len(problems) - 40} more" if len(problems) > 40 else ""))
    lines = report(rows, next(iter(commits)))
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines) if args.show else f"Wrote {OUT.relative_to(ROOT)} (all checks passed).")


if __name__ == "__main__":
    main()
