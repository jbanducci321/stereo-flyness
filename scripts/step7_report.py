"""Step 7 report (D52): the whole brain against the subcircuit in fly-driven closed loop.

Two pairings, 60 pairs each (the 20 held-out cube levels at seeds 0-2, same Poisson seed within a pair):
- **150 Hz:** the Step 2 baseline on the subcircuit (D48),
  results/closed_loop/final/held_out/200deg_collision_R150[_seedN], against the Step 4 intact whole
  brain (D51), results/closed_loop/whole_brain/held_out/200deg_collision_R150[_seedN]_step4.
- **50 Hz:** Step 3's held-out runs on the subcircuit (D49), .../final/held_out/200deg_collision_R50[_seedN]_step3,
  against the D52 whole-brain runs, .../whole_brain/held_out/200deg_collision_R50[_seedN]_step7.

**The bar (D52): identical games in >= 57 of 60 pairs,** per rate. Identical means the cube's
state (x, y, vy) is exactly the same after every tick, for the same number of ticks; an extra
mid-air press on one network isn't a split. Every pair that splits is described. Described only:
per-approach agreement up to each pair's first split, the per-level sign test, and the usual measures.

Blind (D33): it writes results/step7/report.md, pairs.csv and runs.csv and prints only what it
checked, never an outcome. Opened together after the Step 4 opening.

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
from step4_runs import SEEDS, THETA_FULL
from stereo_flyness.experiments.step2_analysis import CLASSES, approach_spans, compare, replay
from stereo_flyness.experiments.step4_analysis import paired
from stereo_flyness.experiments.step7_analysis import first_split, shared_approaches, state_split
from stereo_flyness.game.physics import TICKS_PER_SECOND
from stereo_flyness.game.suites import load_level

HELD_OUT = ROOT / "results" / "closed_loop"
OUT = ROOT / "results" / "step7"
MODE = "collision"
NETWORKS = ("subcircuit", "whole brain")
GAME_BAR = 57  # identical games, of 60 (D52)
# Settings both runs of a pair must share (run.json); the network and stuck-state lists differ by design (D38).
SAME = ("driver", "mode", "rate_hz", "rate_scaling", "theta_full_deg", "seed", "suite", "level")
# Rate -> (subcircuit folder tag, whole-brain folder tag), as play_cube.py names them (D52).
PAIRINGS = {150: ("", "_step4"), 50: ("_step3", "_step7")}


def folder(network, rate, seed, tag) -> Path:
    net = "final" if network == "subcircuit" else "whole_brain"
    return (HELD_OUT / net / "held_out" /
            f"{THETA_FULL:g}deg_collision_R{rate:g}{'' if seed == 0 else f'_seed{seed}'}{tag}" / "fly")


def load(d: Path, level):
    meta = json.loads((d / "run.json").read_text(encoding="utf-8"))
    row, appr = read_run(d, level, MODE)  # replays the run and stops if it doesn't rebuild exactly
    brain = pd.read_parquet(d / "brain.parquet")
    ticks = pd.read_parquet(d / "ticks.parquet")
    return meta, row, appr, brain, ticks


def where(rep, brain, k) -> dict:
    """What the fly saw at brain row k, the last row both networks saw alike."""
    if k >= len(brain):
        return {"split_theta": None, "split_gap": None, "split_object": "after the shorter run ended"}
    o = rep.obstacle[k]
    return {"split_theta": float(brain["theta_deg"].iloc[k]), "split_gap": float(brain["gap"].iloc[k]),
            "split_object": "nothing looming" if o is None else f"x {o.x0:.0f}, y {o.bottom:.0f}-{o.top:.0f}"}


def outcome(row) -> str:
    return "completed" if row["completed"] else f"died ({row['class']}) on {row['killer_text']}"


def collect(rate):
    sub_tag, whole_tag = PAIRINGS[rate]
    pairs, runs, appr, problems = [], [], [], []
    for seed in SEEDS:
        for name in levels("held_out"):
            ds = {"subcircuit": folder("subcircuit", rate, seed, sub_tag) / name,
                  "whole brain": folder("whole brain", rate, seed, whole_tag) / name}
            missing = [n for n, d in ds.items() if not (d / "run.json").exists()]
            if missing:
                problems.append(f"{name} seed {seed}: no {' or '.join(missing)} run")
                continue
            level, _ = load_level(LEVELS, job(name, "held_out"))
            got = {n: load(d, level) for n, d in ds.items()}
            (ms, rs, _, bs, ts), (mw, rw, _, bw, tw) = got["subcircuit"], got["whole brain"]
            differ = [k for k in SAME if ms.get(k) != mw.get(k)]
            if ms.get("seed") != seed:
                differ.append("seed (not the folder's)")
            if ms.get("rate_hz") != rate:
                differ.append("rate (not the pairing's)")
            if differ:
                problems.append(f"{name} seed {seed}: settings differ ({', '.join(differ)})")
                continue
            for n, (_, row, a, _, _) in got.items():
                key = {"network": n, "seed": seed, "level": name}
                runs.append({**key, **row, "difficulty": name.split("-")[1]})
                appr.append(a.assign(**key, carry_over=(a["since_gf_ms"] < CARRY_OVER_MS).to_numpy()))
            hs, hw = ts["held"].to_numpy(bool), tw["held"].to_numpy(bool)
            split = state_split(tw, ts)
            press = first_split(hw, hs)
            rep = replay(level, hs, MODE)
            agree = shared_approaches(bw, bs, approach_spans(rep), split)
            p = {"rate": rate, "level": name, "seed": seed, "identical": split is None,
                 "presses_differ": press is not None, "first_press_difference_tick": press,
                 "approaches_compared": agree["compared"], "approaches_matched": agree["matched"],
                 "approaches_shared": agree["approaches"], "approaches_neither": agree["neither"],
                 "commits": f"{ms['commit'][:7]} / {mw['commit'][:7]}"}
            if split is not None:
                p.update({"split_tick": split + 1, "split_s": (split + 1) / TICKS_PER_SECOND,
                          "pressed_whole": bool(hw[split]) if split < len(hw) else None,
                          "pressed_sub": bool(hs[split]) if split < len(hs) else None,
                          **where(rep, bs, split), "outcome_whole": outcome(rw), "outcome_sub": outcome(rs),
                          "outcome_changed": compare(rw, rs) != 0})
            pairs.append(p)
    return pd.DataFrame(pairs), pd.DataFrame(runs), (pd.concat(appr, ignore_index=True) if appr else pd.DataFrame()), problems


def checks(rate, pairs, runs, problems) -> tuple[list[str], bool]:
    n = len(levels("held_out")) * len(SEEDS)
    lines = [f"### Checks at {rate} Hz (before any comparison)", "",
             f"- Pairs (need {n}): {len(pairs)}" + (" — **all complete**" if len(pairs) == n else " — **INCOMPLETE: nothing is compared**"),
             f"- Every run replayed exactly from its logged presses ({len(runs)} runs).",
             f"- Settings shared within every pair ({', '.join(SAME)}): "
             + ("yes" if not any("settings" in p for p in problems) else "**NO**")]
    commits = sorted(runs["commit"].unique()) if len(runs) else []
    dirty = [c for c in commits if c.endswith("-dirty")]
    lines.append(f"- Commits: {', '.join(c[:7] for c in commits) or '–'}" + (" — **some runs are -dirty**" if dirty else " (all clean)"))
    lines += [f"- **Problem:** {p}" for p in problems[:10]] + (["- ..."] if len(problems) > 10 else [])
    return lines + [""], len(pairs) == n and not problems and not dirty


def bar(rate, pairs) -> list[str]:
    same = int(pairs["identical"].sum())
    press_only = int((pairs["identical"] & pairs["presses_differ"]).sum())
    compared, matched = int(pairs["approaches_compared"].sum()), int(pairs["approaches_matched"].sum())
    share = f"{matched / compared:.1%}" if compared else "–"
    return [f"### The bar at {rate} Hz (D52)", "",
            f"- **Identical games** (the cube's x, y, vy equal on every tick): **{same} of {len(pairs)}** "
            f"(bar ≥ {GAME_BAR}): **{'PASS' if same >= GAME_BAR else 'FAIL'}**.",
            f"- Of the identical games, {press_only} differ only in presses that did nothing (in mid-air), described.",
            f"- Described, not a bar: per approach, up to each pair's first split, {matched} of {compared} compared "
            f"approaches with the first press within ±1 frame ({share}); "
            f"{int(pairs['approaches_neither'].sum())} shared approaches had no press from either.", ""]


def splits_table(rate, pairs) -> list[str]:
    s = pairs[~pairs["identical"]]
    lines = [f"### Every game that split at {rate} Hz", ""]
    if s.empty:
        return lines + ["None: every pair played the same game.", ""]
    lines += ["| Level | Seed | State first differs after | Pressed there (whole / sub) | θ, gap | Object in view | Whole brain | Subcircuit | Outcome changed |",
              "|---|---|---|---|---|---|---|---|---|"]
    yn = {True: "yes", False: "no", None: "–"}
    for r in s.sort_values(["level", "seed"]).to_dict("records"):
        th = "–" if r["split_theta"] is None or pd.isna(r["split_theta"]) else f"{r['split_theta']:.1f}°, {r['split_gap']:.1f}"
        lines.append(f"| {r['level']} | {r['seed']} | tick {r['split_tick']} ({r['split_s']:.2f} s) | "
                     f"{yn[r['pressed_whole']]} / {yn[r['pressed_sub']]} | {th} | {r['split_object']} | "
                     f"{r['outcome_whole']} | {r['outcome_sub']} | {yn[r['outcome_changed']]} |")
    return lines + [""]


def same_outcome(rate, runs) -> list[str]:
    rec = {n: runs[runs["network"] == n].to_dict("records") for n in NETWORKS}
    r = paired(rec["subcircuit"], rec["whole brain"])
    return [f"### Same outcome per level at {rate} Hz (described)", "",
            "Per level, each network's median run across seeds 0–2; D48's \"equal\"; two-sided sign test, equal levels left out.", "",
            f"- Subcircuit against whole brain: better {r.better}, worse {r.worse}, equal {r.equal}; p = {r.p:.3f} ({r.reading}).", ""]


def described(rate, runs, appr) -> list[str]:
    lines = [f"### Described at {rate} Hz", "",
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
    return lines + [""]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    out = ap.parse_args().out
    lines = ["# Step 7: the whole brain against the subcircuit, in closed loop (D52)", "",
             f"θ_full = {THETA_FULL:g}°, R × f, collision course; the 20 held-out cube levels at seeds 0–2, "
             "the same Poisson seed within a pair. Rules fixed in D52 before the Step 4 report was opened.", ""]
    printed, all_pairs, all_runs = [], [], []
    for rate in PAIRINGS:
        pairs, runs, appr, problems = collect(rate)
        check_lines, ok = checks(rate, pairs, runs, problems)
        printed += check_lines
        lines += [f"## {rate} Hz" + (" (the fly of record)" if rate == 150 else " (the labelled variant, D50)"), ""] + check_lines
        if ok:
            lines += bar(rate, pairs) + splits_table(rate, pairs) + same_outcome(rate, runs) + described(rate, runs, appr)
        else:
            lines += ["**Checks failed at this rate: nothing is compared.**", ""]
        all_pairs.append(pairs)
        all_runs.append(runs.assign(rate=rate) if len(runs) else runs)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    pd.concat(all_pairs, ignore_index=True).to_csv(out / "pairs.csv", index=False)
    pd.concat(all_runs, ignore_index=True).to_csv(out / "runs.csv", index=False)
    print("\n".join(printed))
    print(f"Wrote report.md, pairs.csv and runs.csv to {out} (outcomes not shown: blind, D33)")


if __name__ == "__main__":
    main()
