"""Look at the runaway cascades in the whole-brain pathway tests (J5; follow-up to D37).

A cascade trial has far more active neurons than the other trials of its condition (D37's test:
more than `--ratio` times their median). For each one this reports:
- when it starts: the first frame from which its active-neuron count stays above every other
  trial of the condition, by `--margin` times;
- which neurons start it: neurons active in it but in no other trial of the condition, in order
  of first spike, with their cell types;
- whether it stops: with `--extend`, the trial is rerun exactly (same condition name and trial,
  so the same seed and Poisson input) for twice as long, once with the input kept on and once
  with it switched off after the original 1 s. The first second is checked against the saved trial;
- whether it's chance that every cascade had upward-motion input.

Reruns go to git-ignored results/cascades/; the report to results/cascades/report.md.

Usage:
    uv run python scripts/analyse_cascades.py
    uv run python scripts/analyse_cascades.py --extend --jobs 3
"""

import argparse
import sys
import tomllib
from dataclasses import replace
from math import comb

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from find_target_neurons import fetch_annotations
from run_pathway_tests import CON_PATHS, CONFIG, OUT, PATH_COMP, conditions, git_commit
from stereo_flyness.experiments.pathway_tests import load_trial, run_trial

RESULTS = OUT.parent / "cascades"
EXTENSIONS = {"input_kept_on": True, "input_off_after_1s": False}


def active_counts(conds):
    """{condition key: {trial: number of neurons that fired}} for every saved trial."""
    out = {}
    for c in conds:
        counts = {}
        for t in range(c.trials):
            p = c.path(OUT, t)
            if p.exists():
                with np.load(p) as z:
                    counts[t] = len(z["all_ids"])
        if counts:
            out[c.key] = counts
    return out


def find_cascades(counts, ratio):
    found = []
    for key, by_trial in counts.items():
        for t, n in by_trial.items():
            others = [v for k, v in by_trial.items() if k != t]
            if others and n > ratio * np.median(others):
                found.append((key, t, n, float(np.median(others))))
    return found


def per_frame_active(tr):
    return (tr["all_spikes"] > 0).sum(axis=1)


def onset(curve, others, margin):
    """First frame from which `curve` stays above `margin` times the others' per-frame maximum."""
    above = curve > margin * np.maximum(others.max(axis=0), 1)
    stays = np.flip(np.cumprod(np.flip(above)))  # True where every later frame is above too
    hits = np.flatnonzero(stays)
    return int(hits[0]) if len(hits) else None


def extended(cond, keep_on):
    """The same condition, run for twice as long: input kept on, or switched off after 1 s."""
    (n, rates), = cond.schedule  # pathway tests with a cascade have one constant segment
    return replace(cond, schedule=[(n, rates), (n, rates if keep_on else {})])


def label(ann, ids):
    rows = ann.reindex(ids)
    return [f"{r.cell_type if isinstance(r.cell_type, str) else '(untyped ' + str(r.super_class) + ')'} "
            f"{r.side if isinstance(r.side, str) else ''}".strip() for r in rows.itertuples()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ratio", type=float, default=2.0, help="cascade test: times the median (D37)")
    parser.add_argument("--margin", type=float, default=1.5, help="onset: times the others' per-frame max")
    parser.add_argument("--extend", action="store_true", help="rerun each cascade for twice as long")
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = tomllib.loads(CONFIG.read_text())
    conds = [c for c in conditions(cfg) if not c.experiment.startswith("P")]  # game-input tests
    by_key = {c.key: c for c in conds}
    counts = active_counts(conds)
    cascades = find_cascades(counts, args.ratio)
    ann = pd.read_csv(fetch_annotations(), sep="\t", usecols=["root_id", "cell_type", "super_class", "side"],
                      low_memory=False).drop_duplicates("root_id").set_index("root_id")
    frame_ms = None
    lines = [f"# Runaway cascades (whole-brain pathway tests)\n",
             f"{sum(len(v) for v in counts.values())} trials in {len(counts)} conditions; cascade = more than "
             f"{args.ratio:g}x the median active count of the condition's other trials.\n"]
    starters = {}

    for key, t, n, med in cascades:
        cond = by_key[key]
        tr = load_trial(cond.path(OUT, t))
        frame_ms = tr["meta"]["frame_ms"]
        others = [load_trial(cond.path(OUT, k)) for k in counts[key] if k != t]
        curves = np.array([per_frame_active(o) for o in others])
        start = onset(per_frame_active(tr), curves, args.margin)
        normal = set().union(*(set(o["all_ids"].tolist()) for o in others))
        new = [i for i, nid in enumerate(tr["all_ids"]) if int(nid) not in normal]
        first = {i: int(np.flatnonzero(tr["all_spikes"][:, i])[0]) for i in new}
        order = sorted(new, key=lambda i: (first[i], i))
        ids = [int(tr["all_ids"][i]) for i in order]
        starters[key] = ids
        end = per_frame_active(tr)[-20:].mean(), curves[:, -20:].mean()

        lines += [f"## {key}, trial {t}\n",
                  f"- {n:,} active neurons vs a median of {med:,.0f} ({n / med:.1f}x); "
                  f"{len(new):,} fired in no other trial of this condition.",
                  f"- Takes off at frame {start} (~{start * frame_ms:.0f} ms of {len(curves[0]) * frame_ms:.0f} ms): "
                  "from then on, more than "
                  f"{args.margin:g}x as many neurons fire per frame as in any other trial." if start is not None
                  else "- No sustained take-off frame found.",
                  f"- Last 20 frames: {end[0]:,.0f} neurons active per frame vs {end[1]:,.0f} in the other trials.",
                  "- First 15 neurons that fired in no other trial (frame, cell type):"]
        lines += [f"  - frame {first[i]}: {lab} ({nid})"
                  for i, nid, lab in zip(order[:15], ids[:15], label(ann, ids[:15]))]
        before = [nid for i, nid in zip(order, ids) if start is not None and first[i] < start]
        types = pd.Series(label(ann, before)).str.replace(r" (left|right|center)$", "", regex=True)
        lines += [f"- {len(before)} such neurons fired before the take-off. Most common types: "
                  + ", ".join(f"{k} ({v})" for k, v in types.value_counts().head(8).items()), ""]

    # Do the cascades share neurons?
    keys = list(starters)
    lines.append("## Overlap between cascades\n")
    for a in range(len(keys)):
        for b in range(a + 1, len(keys)):
            sa, sb = set(starters[keys[a]]), set(starters[keys[b]])
            lines.append(f"- {keys[a]} vs {keys[b]}: {len(sa & sb):,} shared of {len(sa):,} / {len(sb):,}; "
                         f"first 50 to fire share {len(set(starters[keys[a]][:50]) & set(starters[keys[b]][:50]))}")
    all_new = pd.Series(label(ann, sorted(set().union(*map(set, starters.values())))))
    supers = ann.reindex(sorted(set().union(*map(set, starters.values()))))["super_class"].value_counts()
    lines += ["- Neurons recruited only in cascades, by super class: "
              + ", ".join(f"{k} ({v:,})" for k, v in supers.head(8).items()),
              f"- ... by cell type: " + ", ".join(
                  f"{k} ({v})" for k, v in all_new.str.replace(r" (left|right|center)$", "", regex=True)
                  .value_counts().head(10).items()), ""]

    # Is "every cascade had upward-motion input" chance?
    up = lambda c: any(g.startswith("up_") for g in c.inputs)  # noqa: E731
    steer = lambda c: c.experiment.startswith("S")  # noqa: E731
    lines.append("## Upward-motion input: chance?\n")
    for name, pool in (("all game-input trials", conds), ("steering trials only (T4/T5 input)",
                                                          [c for c in conds if steer(c)])):
        n_all = sum(len(counts.get(c.key, {})) for c in pool)
        n_up = sum(len(counts.get(c.key, {})) for c in pool if up(c))
        k = sum(up(by_key[key]) for key, *_ in cascades)
        m = len(cascades)
        p_tail = sum(comb(n_up, j) * comb(n_all - n_up, m - j) for j in range(k, m + 1)) / comb(n_all, m)
        lines.append(f"- Among {name}: {n_up} of {n_all} trials had upward-motion input "
                     f"({100 * n_up / n_all:.0f}%). {k} of {m} cascades did; the chance of {k} or more by luck "
                     f"is {p_tail:.2f}.")
    lines.append("")

    if args.extend:
        meta = {"commit": git_commit(), "purpose": "cascade extension (analyse_cascades.py)"}
        jobs = [(key, t, name, extended(by_key[key], keep)) for key, t, *_ in cascades
                for name, keep in EXTENSIONS.items()]
        Parallel(n_jobs=args.jobs)(
            delayed(run_trial)(c, t, RESULTS / name, PATH_COMP, CON_PATHS[c.sign], cfg["base_seed"],
                               cfg["frame_ms"], meta) for key, t, name, c in jobs)
        lines.append("## Rerun for 2 s (same seed and input)\n")
        for key, t, name, c in jobs:
            orig, ext = load_trial(by_key[key].path(OUT, t)), load_trial(c.path(RESULTS / name, t))
            n = len(per_frame_active(orig))
            same = (set(orig["all_ids"].tolist()) == set(ext["all_ids"][ext["all_spikes"][:n].any(axis=0)].tolist())
                    and np.array_equal(per_frame_active(orig), per_frame_active(ext)[:n]))
            curve = per_frame_active(ext)
            idx = lambda a, b: slice(int(a / frame_ms), int(b / frame_ms))  # noqa: E731
            parts = ", ".join(f"{a}-{b} ms: {curve[idx(a, b)].mean():,.0f}" for a, b in
                              ((0, 500), (500, 1000), (1000, 1100), (1100, 1500), (1500, 2000)))
            last = np.flatnonzero(curve)
            lines.append(f"- {key} t{t}, {name.replace('_', ' ')}: first second identical to the saved trial: "
                         f"{'yes' if same else 'NO'}. Neurons active per frame: {parts}. "
                         f"Last activity at {(last[-1] + 1) * frame_ms:.0f} ms." if len(last) else " No activity.")
        lines.append("")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {RESULTS / 'report.md'}")


if __name__ == "__main__":
    main()
