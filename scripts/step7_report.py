"""Step 7 report (docs/notes/step7_proposal.md, D52 once logged): the whole brain against the
subcircuit in closed loop, from runs that already exist. No new runs.

- Subcircuit: the Step 2 baseline (D48), results/closed_loop/final/held_out/200deg_collision_R150[_seedN].
- Whole brain: the Step 4 intact runs (D51), results/closed_loop/whole_brain/held_out/200deg_collision_R150[_seedN]_step4.
Same encoding, settings, levels and Poisson seeds: 60 pairs.

Blind (D33): it writes results/step7/report.md, pairs.csv and splits.csv and prints only what it
checked, never an outcome. It reads the intact whole brain's runs, so it's opened together after
the Step 4 opening.

Both candidate bars are computed (stereo_flyness.experiments.step7_analysis), because D52 hasn't
picked one yet. The report labels which one D52 fixed; until then, both are "proposed".

Usage:
    uv run python scripts/step7_report.py
    uv run python scripts/step7_report.py --out <folder>   # somewhere else (e.g. a dry run)
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

from inspect_encoding import LEVELS, job
from run_pathway_tests import ROOT
from step2_report import CARRY_OVER_MS, read_run
from step3_grid import levels
from step4_report import run_folder as whole_brain_folder
from step4_runs import RATE, SEEDS, THETA_FULL
from stereo_flyness.experiments.step2_analysis import CLASSES, approach_spans, compare, replay
from stereo_flyness.experiments.step4_analysis import paired
from stereo_flyness.experiments.step7_analysis import first_split, shared_approaches
from stereo_flyness.game.physics import TICKS_PER_SECOND
from stereo_flyness.game.suites import load_level

SUB_RUNS = ROOT / "results" / "closed_loop" / "final" / "held_out"
OUT = ROOT / "results" / "step7"
MODE = "collision"
NETWORKS = ("subcircuit", "whole brain")
# Bars proposed in docs/notes/step7_proposal.md §1 and question 1; D52 fixes which one decides.
GAME_BAR = 57  # identical games, of 60
APPROACH_BAR = 0.95  # share of compared approaches with the first press within ±1 frame (rule 5)
# Settings both runs of a pair must share (run.json); the network and stuck-state lists differ by design (D38).
SAME = ("driver", "mode", "rate_hz", "rate_scaling", "theta_full_deg", "seed", "suite", "level")


def sub_folder(seed) -> Path:
    return SUB_RUNS / f"{THETA_FULL:g}deg_collision_R{RATE:g}{'' if seed == 0 else f'_seed{seed}'}" / "fly"


def load(d: Path, level):
    meta = json.loads((d / "run.json").read_text(encoding="utf-8"))
    row, appr = read_run(d, level, MODE)  # replays the run and stops if it doesn't rebuild exactly
    brain = pd.read_parquet(d / "brain.parquet")
    held = pd.read_parquet(d / "ticks.parquet", columns=["held"])["held"].to_numpy(bool)
    return meta, row, appr, brain, held


def where(rep, brain, k) -> dict:
    """What the fly saw on the split tick (the same for both networks up to there)."""
    if k >= len(brain):
        return {"split_theta": None, "split_gap": None, "split_object": "after the shorter run ended"}
    o = rep.obstacle[k]
    return {"split_theta": float(brain["theta_deg"].iloc[k]), "split_gap": float(brain["gap"].iloc[k]),
            "split_object": "nothing looming" if o is None else f"x {o.x0:.0f}, y {o.bottom:.0f}-{o.top:.0f}"}


def outcome(row) -> str:
    return "completed" if row["completed"] else f"died ({row['class']}) on {row['killer_text']}"


def collect():
    pairs, runs, appr, problems = [], [], [], []
    for seed in SEEDS:
        for name in levels("held_out"):
            ds = {"subcircuit": sub_folder(seed) / name, "whole brain": whole_brain_folder("", seed) / name}
            missing = [n for n, d in ds.items() if not (d / "run.json").exists()]
            if missing:
                problems.append(f"{name} seed {seed}: no {' or '.join(missing)} run")
                continue
            level, _ = load_level(LEVELS, job(name, "held_out"))
            got = {n: load(d, level) for n, d in ds.items()}
            (ms, rs, a_s, bs, hs), (mw, rw, a_w, bw, hw) = got["subcircuit"], got["whole brain"]
            differ = [k for k in SAME if ms.get(k) != mw.get(k)]
            if ms.get("seed") != seed:
                differ.append("seed (not the folder's)")
            if differ:
                problems.append(f"{name} seed {seed}: settings differ ({', '.join(differ)})")
                continue
            for n, (_, row, a, _, _) in got.items():
                key = {"network": n, "seed": seed, "level": name}
                runs.append({**key, **row, "difficulty": name.split("-")[1]})
                appr.append(a.assign(**key, carry_over=(a["since_gf_ms"] < CARRY_OVER_MS).to_numpy()))
            split = first_split(hw, hs)
            rep = replay(level, hs, MODE)
            agree = shared_approaches(bw, bs, approach_spans(rep), split)
            p = {"level": name, "seed": seed, "identical": split is None,
                 "approaches_compared": agree["compared"], "approaches_matched": agree["matched"],
                 "approaches_shared": agree["approaches"], "approaches_neither": agree["neither"]}
            if split is not None:
                p.update({"split_tick": split, "split_s": split / TICKS_PER_SECOND,
                          "pressed_whole": bool(hw[split]) if split < len(hw) else None,
                          "pressed_sub": bool(hs[split]) if split < len(hs) else None,
                          **where(rep, bs, split), "outcome_whole": outcome(rw), "outcome_sub": outcome(rs),
                          "outcome_changed": compare(rw, rs) != 0})
            p["commits"] = f"{ms['commit'][:7]} / {mw['commit'][:7]}"
            pairs.append(p)
    if not pairs:
        sys.exit("No Step 7 pairs found. It needs the Step 2 baseline and the Step 4 intact runs.")
    return pd.DataFrame(pairs), pd.DataFrame(runs), pd.concat(appr, ignore_index=True), problems


def checks(pairs, runs, problems) -> tuple[list[str], bool]:
    n = len(levels("held_out")) * len(SEEDS)
    lines = ["## Checks (before any comparison)", "",
             f"- Pairs (need {n}): {len(pairs)}" + (" — **all complete**" if len(pairs) == n else " — **INCOMPLETE**"),
             f"- Every run replayed exactly from its logged presses ({len(runs)} runs).",
             f"- Settings shared within every pair ({', '.join(SAME)}): "
             + ("yes" if not any("settings" in p for p in problems) else "**NO**")]
    commits = sorted(runs["commit"].unique())
    dirty = [c for c in commits if c.endswith("-dirty")]
    lines.append(f"- Commits: {', '.join(c[:7] for c in commits)}" + (" — **some runs are -dirty**" if dirty else " (all clean)"))
    lines += [f"- **Problem:** {p}" for p in problems]
    return lines + [""], len(pairs) == n and not problems and not dirty


def bars(pairs) -> list[str]:
    same = int(pairs["identical"].sum())
    compared, matched = int(pairs["approaches_compared"].sum()), int(pairs["approaches_matched"].sum())
    share = matched / compared if compared else float("nan")
    return ["## The bars (both computed; D52 fixes which one decides — until then both are proposals)", "",
            f"- **Identical games, tick for tick:** {same} of {len(pairs)} (proposed bar ≥ {GAME_BAR}): "
            f"**{'meets it' if same >= GAME_BAR else 'misses it'}**.",
            f"- **Per approach (rule 5 on the shared part of each game):** {matched} of {compared} compared approaches "
            f"with the first press within ±1 frame ({share:.1%}; proposed bar ≥ {APPROACH_BAR:.0%}): "
            f"**{'meets it' if share >= APPROACH_BAR else 'misses it'}**. "
            f"{int(pairs['approaches_neither'].sum())} shared approaches had no press from either and aren't in the share. "
            "Approaches after a split aren't compared (a different game).", ""]


def splits_table(pairs) -> list[str]:
    s = pairs[~pairs["identical"]]
    lines = ["## Every game that split (described)", ""]
    if s.empty:
        return lines + ["None: every pair played the same game.", ""]
    lines += ["| Level | Seed | Split at | Pressed (whole / sub) | θ, gap there | Object in view | Whole brain | Subcircuit | Outcome changed |",
              "|---|---|---|---|---|---|---|---|---|"]
    yn = {True: "yes", False: "no", None: "–"}
    for r in s.sort_values(["level", "seed"]).to_dict("records"):
        th = "–" if r["split_theta"] is None or pd.isna(r["split_theta"]) else f"{r['split_theta']:.1f}°, {r['split_gap']:.1f}"
        lines.append(f"| {r['level']} | {r['seed']} | tick {r['split_tick']} ({r['split_s']:.2f} s) | "
                     f"{yn[r['pressed_whole']]} / {yn[r['pressed_sub']]} | {th} | {r['split_object']} | "
                     f"{r['outcome_whole']} | {r['outcome_sub']} | {yn[r['outcome_changed']]} |")
    return lines + [""]


def same_outcome(runs) -> list[str]:
    rec = {n: runs[runs["network"] == n].to_dict("records") for n in NETWORKS}
    r = paired(rec["subcircuit"], rec["whole brain"])
    return ["## (b) Same outcome per level (reported, not the main bar)", "",
            "Per level, each network's median run across seeds 0–2; D48's \"equal\"; two-sided sign test, equal levels left out.", "",
            f"- Subcircuit against whole brain: better {r.better}, worse {r.worse}, equal {r.equal}; p = {r.p:.3f} "
            f"(**{r.reading}**).", ""]


def described(runs, appr) -> list[str]:
    lines = ["## (c) Described", "",
             "| Network | Mean progress | Completed easy / medium / hard | Deaths " + " / ".join(f"({c})" for c in CLASSES)
             + " | Stuck runs | Presses per s | First-spike θ, median (all / without carry-over) |",
             "|---|---|---|---|---|---|---|"]
    for n in NETWORKS:
        g, a = runs[runs["network"] == n], appr[appr["network"] == n]
        done = " / ".join(f"{int(g.loc[g['difficulty'] == d, 'completed'].sum())}/{int((g['difficulty'] == d).sum())}"
                          for d in ("easy", "medium", "hard"))
        deaths = Counter(g.loc[~g["completed"], "class"])
        spiked = a["first_spike_theta"].dropna()
        fresh = a.loc[~a["carry_over"], "first_spike_theta"].dropna()
        theta = "never fired" if spiked.empty else f"{spiked.median():.1f}° / " + (f"{fresh.median():.1f}°" if len(fresh) else "–")
        lines.append(f"| {n} | {100 * g['progress'].mean():.1f}% | {done} | " + " / ".join(str(deaths.get(c, 0)) for c in CLASSES)
                     + f" | {int(g['stuck'].sum())} | {g['presses'].sum() / g['seconds'].sum():.2f} | {theta} |")
    return lines + ["", "Wall-clock speed per network is in the Step 6 planning, from the runs' timestamps.", ""]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    out = ap.parse_args().out
    pairs, runs, appr, problems = collect()
    check_lines, ok = checks(pairs, runs, problems)
    lines = ["# Step 7: the whole brain against the subcircuit, in closed loop", "",
             f"R = {RATE:g} Hz, R × f, θ_full = {THETA_FULL:g}°, collision course; the 20 held-out cube levels at seeds "
             "0–2. Subcircuit: the Step 2 baseline (D48). Whole brain: the Step 4 intact runs (D51). Plan: "
             "docs/notes/step7_proposal.md. No new runs.", ""] + check_lines
    if ok:
        lines += bars(pairs) + splits_table(pairs) + same_outcome(runs) + described(runs, appr)
    else:
        lines += ["**Checks failed: nothing is compared.**"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    pairs.to_csv(out / "pairs.csv", index=False)
    runs.to_csv(out / "runs.csv", index=False)
    print("\n".join(check_lines))
    print(f"Wrote report.md, pairs.csv and runs.csv to {out} (outcomes not shown: blind, D33)")


if __name__ == "__main__":
    main()
