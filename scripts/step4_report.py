"""Step 4 report (D51): every control and lesion against the intact whole brain, judged by the rules
fixed before any run (stereo_flyness.experiments.step4_analysis).

Blind (D33): it writes results/step4/report.md, runs.csv and approaches.csv and prints only what it
checked, never an outcome. Opened together, after both nights.

Checks before anything is compared: every condition has all 60 runs, every run replays exactly from
its logged presses, every run's recorded connectivity file still has the SHA-256 it recorded, the
recorded commits, stuck runs and unclassified deaths.

Usage:
    uv run python scripts/step4_report.py
"""

import json
import sys
from collections import Counter

import pandas as pd

from inspect_encoding import LEVELS, job
from run_pathway_tests import ROOT
from step2_report import CARRY_OVER_MS, read_run
from step3_grid import levels
from step4_runs import RATE, SEEDS, TAG, THETA_FULL
from find_target_neurons import DATA_DIR
from stereo_flyness.brain.controls import control_path, file_sha256
from stereo_flyness.experiments.step2_analysis import CLASSES
from stereo_flyness.experiments.step4_analysis import holm, paired, relay_reading, specific
from stereo_flyness.game.suites import load_level
from reproduce_sugar import PATH_CON

RUNS = ROOT / "results" / "closed_loop" / "whole_brain" / "held_out"
CALIBRATION = ROOT / "results" / "calibration" / "whole_brain"
OUT = ROOT / "results" / "step4"
INTACT = "intact whole brain"

# Condition -> [(folder suffix, Poisson seed)]: instance or draw k plays at seed k (D51).
CONDITIONS = {
    INTACT: [("", s) for s in SEEDS],
    "E5b (inhibitory partners silenced)": [("_silence-E5b", s) for s in SEEDS],
    "E5c (excitatory partners silenced)": [("_silence-E5c", s) for s in SEEDS],
    "E5b random lesion": [(f"_randlesion-E5b_d{k}", k) for k in SEEDS],
    "E5c random lesion": [(f"_randlesion-E5c_d{k}", k) for k in SEEDS],
    "(a) shuffle": [(f"_shuffle_s{k}", k) for k in SEEDS],
    "(b) looming-kept shuffle": [(f"_loomkept_s{k}", k) for k in SEEDS],
    "(c) relay-only": [("_relay", s) for s in SEEDS],
    "(d) random network": [(f"_random_s{k}", k) for k in SEEDS],
}
E5B, E5C = "E5b (inhibitory partners silenced)", "E5c (excitatory partners silenced)"
RANDOM_OF = {E5B: "E5b random lesion", E5C: "E5c random lesion"}
# The Holm family, named in D51: 8 against intact, 2 against their own random-lesion controls.
FAMILY = [(c, INTACT) for c in CONDITIONS if c != INTACT] + [(E5B, RANDOM_OF[E5B]), (E5C, RANDOM_OF[E5C])]
WIRING = ("(a) shuffle", "(d) random network")
RELAY = ("(b) looming-kept shuffle", "(c) relay-only")


def run_folder(suffix, seed):
    return RUNS / f"{THETA_FULL:g}deg_collision_R{RATE:g}{suffix}{'' if seed == 0 else f'_seed{seed}'}{TAG}" / "fly"


def open_loop_folder(suffix):
    return CALIBRATION / f"gap245_R{RATE:g}_scaled{suffix}{TAG}" / "results.csv"


def collect() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, appr = [], []
    for cond, sets in CONDITIONS.items():
        for suffix, seed in sets:
            for name in levels("held_out"):
                d = run_folder(suffix, seed) / name
                if not (d / "run.json").exists():
                    continue
                meta = json.loads((d / "run.json").read_text(encoding="utf-8"))
                if meta.get("seed") != seed:
                    raise ValueError(f"{d} isn't a seed-{seed} run")
                level, _ = load_level(LEVELS, job(name, "held_out"))
                row, t = read_run(d, level, "collision")
                key = {"condition": cond, "seed": seed, "level": name}
                rows.append({**key, **row, "difficulty": name.split("-")[1],
                             "connectome": meta.get("connectome", {}).get("file"),
                             "connectome_sha256": meta.get("connectome", {}).get("sha256"),
                             "silenced": len(meta.get("silenced", {}).get("ids", []))})
                carry = t["since_gf_ms"] < CARRY_OVER_MS
                appr.append(t.assign(**key, carry_over=carry.to_numpy()))
    if not rows:
        sys.exit(f"No Step 4 runs under {RUNS}. Run scripts/step4_runs.py night1 and night2 first.")
    return pd.DataFrame(rows), pd.concat(appr, ignore_index=True)


def checks(df) -> tuple[list[str], bool]:
    lines = ["## Checks (before any comparison)", ""]
    n = len(levels("held_out")) * len(SEEDS)
    counts = df.groupby("condition").size()
    complete = all(counts.get(c, 0) == n for c in CONDITIONS)
    lines.append(f"- Runs per condition (need {n}): " + ", ".join(f"{c} {counts.get(c, 0)}" for c in CONDITIONS)
                 + (" — **all complete**" if complete else " — **INCOMPLETE: nothing is compared**"))
    lines.append(f"- Every run replayed exactly from its logged presses ({len(df)} runs).")
    commits = sorted(df["commit"].unique())
    dirty = [c for c in commits if c.endswith("-dirty")]
    lines.append(f"- Commits: {', '.join(c[:7] + ('-dirty' if c.endswith('-dirty') else '') for c in commits)}"
                 + (" — **some runs are -dirty**" if dirty else " (all clean)"))
    bad_sha = []
    for (file, sha), _ in df.groupby(["connectome", "connectome_sha256"]):
        path = PATH_CON if file == PATH_CON.name else DATA_DIR / file
        if not path.exists() or file_sha256(path) != sha:
            bad_sha.append(file)
    lines.append("- Connectivity files unchanged since the runs (SHA-256): "
                 + ("all match" if not bad_sha else f"**MISMATCH: {', '.join(bad_sha)}**"))
    lines.append(f"- Stuck runs: {int(df['stuck'].sum())}; unclassified deaths (u): {int((df['class'] == 'u').sum())}")
    return lines + [""], complete and not bad_sha


def fresh_thetas(appr, cond, seed=None) -> list[float]:
    a = appr[(appr["condition"] == cond) & appr["first_spike_theta"].notna() & ~appr["carry_over"]]
    if seed is not None:
        a = a[a["seed"] == seed]
    return a["first_spike_theta"].tolist()


def describe(df, appr) -> list[str]:
    lines = ["## Every condition (described)", "",
             "| Condition | Mean progress | Completed easy / medium / hard | Deaths " + " / ".join(f"({c})" for c in CLASSES)
             + " | Stuck | Presses per s | First-spike θ, median (all / without carry-over) | Approaches with no Giant Fiber spike |",
             "|---|---|---|---|---|---|---|---|"]
    for cond in CONDITIONS:
        g, a = df[df["condition"] == cond], appr[appr["condition"] == cond]
        if g.empty:
            continue
        done = " / ".join(f"{int(g.loc[g['difficulty'] == d, 'completed'].sum())}/{int((g['difficulty'] == d).sum())}"
                          for d in ("easy", "medium", "hard"))
        deaths = Counter(g.loc[~g["completed"], "class"])
        spiked = a["first_spike_theta"].dropna()
        fresh = fresh_thetas(appr, cond)
        theta = "never fired" if spiked.empty else f"{spiked.median():.1f}° / " + (
            f"{pd.Series(fresh).median():.1f}°" if fresh else "–")
        lines.append(f"| {cond} | {100 * g['progress'].mean():.1f}% | {done} | "
                     + " / ".join(str(deaths.get(c, 0)) for c in CLASSES)
                     + f" | {int(g['stuck'].sum())} | {g['presses'].sum() / g['seconds'].sum():.2f} | {theta} | "
                     f"{int(a['first_spike_theta'].isna().sum())} of {len(a)} |")
    return lines + [""]


def open_loop_table() -> list[str]:
    lines = ["## Open-loop check (calibration loom, 10 trials; recorded before the runs, described only)", "",
             "| Condition | First-spike θ, mean ± s.d. | Trials fired |", "|---|---|---|"]
    sets = {INTACT: [""], E5B: ["_silence-E5b"], E5C: ["_silence-E5c"],
            "E5b random lesion": [f"_randlesion-E5b_d{k}" for k in SEEDS],
            "E5c random lesion": [f"_randlesion-E5c_d{k}" for k in SEEDS],
            "(a) shuffle": [f"_shuffle_s{k}" for k in SEEDS], "(b) looming-kept shuffle": [f"_loomkept_s{k}" for k in SEEDS],
            "(c) relay-only": ["_relay"], "(d) random network": [f"_random_s{k}" for k in SEEDS]}
    for cond, suffixes in sets.items():
        files = [open_loop_folder(s) for s in suffixes]
        if not all(f.exists() for f in files):
            lines.append(f"| {cond} | not run | – |")
            continue
        d = pd.concat([pd.read_csv(f) for f in files])
        fired = d["first_spike_theta"].dropna()
        m = "never fired" if fired.empty else f"{fired.mean():.1f} ± {fired.std():.1f}°"
        lines.append(f"| {cond} | {m} | {len(fired)}/{len(d)} |")
    return lines + [""]


def comparisons(df, appr) -> list[str]:
    runs = {c: df[df["condition"] == c].to_dict("records") for c in CONDITIONS}
    results = {(a, b): paired(runs[a], runs[b]) for a, b in FAMILY}
    adj = holm({f"{a} vs {b}": r.p for (a, b), r in results.items()})
    lines = ["## The D51 comparisons (the Holm family: these 10 sign tests)", "",
             "Per level, each setting's median run across its 3 seeds or instances; D48's \"equal\"; two-sided sign test, "
             "equal levels left out; \"better\"/\"worse\" only at p < 0.05. Holm-adjusted p over the 10.", "",
             "| Comparison | Better | Worse | Equal | p | Reading | Holm-adjusted p | Survives Holm |",
             "|---|---|---|---|---|---|---|---|"]
    for (a, b), r in results.items():
        p_adj, keep = adj[f"{a} vs {b}"]
        lines.append(f"| {a} vs {b} | {r.better} | {r.worse} | {r.equal} | {r.p:.3f} | {r.reading} | "
                     f"{p_adj:.3f} | {'yes' if keep else 'no'} |")

    lines += ["", "## Readings fixed in D51", ""]
    for c in WIRING:
        r = results[(c, INTACT)]
        lines.append(f"- **{c}: depends on the wiring** (worse than intact at p < 0.05)? "
                     f"**{'yes' if r.reading == 'worse' else 'no'}** ({r.reading}, p = {r.p:.3f}).")
    def classes(g):  # completed runs aren't deaths (None)
        return [None if done else k for done, k in zip(g["completed"], g["class"])]

    intact = df[df["condition"] == INTACT]
    intact_theta = [fresh_thetas(appr, INTACT, s) for s in SEEDS]
    intact_classes = [classes(intact[intact["seed"] == s]) for s in SEEDS]
    for c in RELAY:
        rr = relay_reading(results[(c, INTACT)], fresh_thetas(appr, c), intact_theta,
                           classes(df[df["condition"] == c]), intact_classes)
        theta = "never fired: fails" if rr.theta_diff is None else f"{rr.theta_diff:.1f}° against a seed range of {rr.theta_range:.1f}°"
        lines.append(f"- **{c}: {rr.verdict}.** Progress: {'pass' if rr.progress_ok else 'fail'} "
                     f"({results[(c, INTACT)].reading}); first-spike θ: {'pass' if rr.theta_ok else 'fail'} ({theta}); "
                     f"(d1) share: {'pass' if rr.d1_ok else 'fail'} ({rr.d1_diff:.0%} against a seed range of {rr.d1_range:.0%}).")
    for c in (E5B, E5C):
        s = specific(results[(c, INTACT)], results[(c, RANDOM_OF[c])])
        lines.append(f"- **{c}: specific to those neurons?** **{'yes' if s else 'no'}** "
                     f"(against intact: {results[(c, INTACT)].reading}; against its random lesion: "
                     f"{results[(c, RANDOM_OF[c])].reading}).")
    lines.append("- **E5c, fixed reading:** if it does better than intact, that's Step 3's late-threshold effect (D49), "
                 "not the lesion improving the fly.")
    lines.append("- The relay bars use a 3-seed range, which is small and noisy, so they're strict: they make \"relay\" "
                 "harder to claim, not easier (D51).")
    return lines + [""]


def references() -> list[str]:
    lines = ["## References (no brain)", ""]
    for name, f in (("never press / random presses (Step 2)", ROOT / "results" / "references" / "final_held_out.csv"),
                    ("always press", ROOT / "results" / "references" / "whole_brain_held_out_always_press.csv")):
        if not f.exists():
            lines.append(f"- {name}: not run")
            continue
        d = pd.read_csv(f)
        for ref, g in d.groupby("reference"):
            lines.append(f"- {ref}: mean progress {100 * g['progress'].mean():.1f}%, "
                         f"{int(g['completed'].sum())}/{len(g)} completed")
    return lines + [""]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    df, appr = collect()
    check_lines, ok = checks(df)
    lines = ["# Step 4: controls and lesions on the cube (D51)", "",
             f"Whole brain, R = {RATE:g} Hz, R × f, θ_full = {THETA_FULL:g}°, collision course; the 20 held-out cube "
             "levels at seeds 0–2 (instance or draw k at seed k). Rules fixed in D51 before any run.", ""] + check_lines
    if ok:
        lines += describe(df, appr) + open_loop_table() + comparisons(df, appr) + references()
    else:
        lines += ["**Checks failed: nothing is compared.**"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    df.to_csv(OUT / "runs.csv", index=False)
    appr.to_csv(OUT / "approaches.csv", index=False)
    print("\n".join(check_lines))
    print(f"Wrote {(OUT / 'report.md').relative_to(ROOT)}, runs.csv and approaches.csv (outcomes not shown: blind, D33)")


if __name__ == "__main__":
    main()
