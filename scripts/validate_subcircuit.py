"""Compare a subcircuit's pathway tests with the whole brain's (J5).

Run the tests on the subcircuit first (same seeds as the whole brain):
    uv run python scripts/run_pathway_tests.py --subcircuit example --jobs 4
    uv run python scripts/validate_subcircuit.py example

    # J5 candidates: 3 trials per condition, metrics split into training and held-out tests
    uv run python scripts/run_pathway_tests.py --subcircuit w2_2hop --trials 3 --jobs 4
    uv run python scripts/validate_subcircuit.py w2_2hop --trials 3 --train E1,S1

Writes results/subcircuits/<name>/validation.md and summary.json (git-ignored): key-group rates
side by side, whole-activity fidelity per condition, the go/no-go verdicts on both networks, and
speed. Only conditions run on both networks are compared. With --train, the conditions a rule
was built from (those experiments, original signs) are reported separately from the held-out
ones, which are the fair test.

The D36 tolerance (as clarified with D37) is judged on the held-out probes:
1. same go/no-go verdicts (all trials);
2. key-group rates within 10%, or 1 Hz under 10 Hz;
3. Giant Fiber first spikes within one frame in >= 95% of events;
4. in **each** probe type, the median share of all whole-brain-active neurons (stimulated ones
   excluded) still active in the subcircuit is >= 90%; the lowest is reported.
Rules 2-4 leave out trial pairs where either network's trial is a runaway cascade (D37's test);
those are reported separately. Every subcircuit trial also gets a stuck-state share (D37's
diagnostic), over the stuck-state neurons the subcircuit contains.
"""

import argparse
import dataclasses
import json
import sys
import tomllib

import numpy as np
import pandas as pd

from analyse_pathway_tests import analyse, load_all, md_table
from run_pathway_tests import CONFIG, OUT, ROOT, conditions, network, runnable
from stereo_flyness.experiments.cascades import load_stuck_state, stuck_share
from stereo_flyness.experiments.pathway_tests import judged
from stereo_flyness.experiments.subcircuit_validation import (
    activity_fidelity, compare_groups, first_spike_agreement, kept_by_type, neuron_rates, paired_cascades,
    within_tolerance,
)

KEY_GROUPS = ["GF_R", "GF_L", "VS_R", "VS_L", "DNp20_R", "DNp20_L", "DNp22_R", "DNp22_L", "LPi09_R", "LPi09_L"]


def headline(cmp: pd.DataFrame, fid: pd.DataFrame) -> dict:
    """Summary numbers for one set of conditions."""
    act = cmp[cmp["whole"] > 1]
    fa = fid[fid["whole_active"] > 0]
    return {
        "conditions": int(len(fid)),
        "key_median_abs_rel_error": float(act["rel_error"].abs().median()) if len(act) else None,
        "key_worst_abs_rel_error": float(act["rel_error"].abs().max()) if len(act) else None,
        "key_worst": (lambda r: f"{r['condition']} {r['group']}: {r['whole']:.1f} → {r['subcircuit']:.1f} Hz")(
            act.loc[act["rel_error"].abs().idxmax()]) if len(act) else None,
        "r_median": float(fa["r"].median()) if len(fa) else None,
        "r_min": float(fa["r"].min()) if len(fa) else None,
        "kept_active_median": float(fa["kept_active"].median()) if len(fa) else None,
        "kept_active_min": float(fa["kept_active"].min()) if len(fa) else None,
        "cut_active_median": float(fa["cut_active"].median()) if len(fa) else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="subcircuit name (data/subcircuits/NAME)")
    parser.add_argument("--trials", type=int, help="compare only the first N trials of each condition")
    parser.add_argument("--train", default="", help="experiments the rule was built from, e.g. E1,S1 (original signs)")
    parser.add_argument("--heldout", default="P", help="experiment prefix the D36 tolerance is judged on (default: probes)")
    args = parser.parse_args()

    cfg = tomllib.loads(CONFIG.read_text())
    path_comp, con_paths, sub_out = network(args.name)
    conds, skipped = runnable(conditions(cfg), path_comp, con_paths)
    if args.trials:
        conds = [dataclasses.replace(c, trials=min(c.trials, args.trials)) for c in conds]
    # Compare only conditions with every (capped) trial saved on both networks
    conds = [c for c in conds if all(c.path(OUT, t).exists() and c.path(sub_out, t).exists() for t in range(c.trials))]
    if not conds:
        sys.exit("No conditions run on both networks yet. Run scripts/run_pathway_tests.py --subcircuit first.")
    train_exps = {e for e in args.train.split(",") if e}
    in_train = {c.key: c.experiment in train_exps and c.sign == "original" for c in conds}
    manifest = json.loads((path_comp.parent / "manifest.json").read_text())
    sub_ids = set(pd.read_csv(path_comp, index_col=0).index)

    # Verdicts (D29-D31) come from the main side's tests; everything else is compared below
    verdict_conds = [c for c in conds if judged(c, cfg)]
    whole = analyse(OUT, cfg, verdict_conds, title="# Whole brain")
    sub = analyse(sub_out, cfg, verdict_conds, title=f"# Subcircuit {args.name}")
    extra = [c for c in conds if not judged(c, cfg)]
    for res, out_dir in ((whole, OUT), (sub, sub_out)):
        if extra:
            df_x, trials_x = load_all(extra, out_dir)
            res["df"] = pd.concat([res["df"], df_x], ignore_index=True)
            res["trials"].update(trials_x)

    # D37: trial pairs where either network's trial is a runaway cascade leave rules 2-4
    cc = cfg["cascade"]
    skip, cascade_rows = set(), []
    for c in conds:
        counts = [{t: len(res["trials"][(c.key, t)]["all_ids"]) for t in range(c.trials)} for res in (whole, sub)]
        for t in sorted(paired_cascades(*counts, cc["ratio"], cc["min_extra"])):
            skip.add((c.key, t))
            cascade_rows.append({"condition": c.key, "trial": t, "active (whole)": counts[0][t],
                                 "active (subcircuit)": counts[1][t]})
    used = lambda key, n: [t for t in range(n) if (key, t) not in skip]  # noqa: E731
    keep = lambda df: df[[(k, t) not in skip for k, t in zip(df["key"], df["trial"])]]  # noqa: E731

    # Does the subcircuit enter the stuck state? (D37 diagnostic)
    stuck_all = load_stuck_state(ROOT / cc["stuck_state"])
    stuck_ids = np.array([i for i in stuck_all if i in sub_ids], dtype=np.int64)
    shares = pd.DataFrame([{"condition": c.key, "trial": t,
                            "whole": stuck_share(whole["trials"][(c.key, t)]["all_ids"], stuck_all),
                            "subcircuit": stuck_share(sub["trials"][(c.key, t)]["all_ids"], stuck_ids)}
                           for c in conds for t in range(c.trials)])
    stuck_sub = shares[shares["subcircuit"] >= cc["stuck_share"]]
    stuck_whole = shares[shares["whole"] >= cc["stuck_share"]]

    n_trials = sorted({c.trials for c in conds})
    out = [f"# Subcircuit validation: {args.name}", "",
           f"- **Size:** {manifest['neurons']:,} neurons ({100 * manifest['neurons'] / manifest['whole_brain']['neurons']:.1f}% of the brain), "
           f"{manifest['connections']:,} connections ({100 * manifest['connections'] / manifest['whole_brain']['connections']:.1f}%)",
           f"- **Spec:** `{json.dumps(manifest['spec'])}`",
           f"- **Compared:** {len(conds)} conditions run on both networks with the same seeds ({'/'.join(map(str, n_trials))} trials each); "
           f"{len(skipped)} conditions can't run on this subcircuit (neurons or sign version missing).",
           f"- **Training conditions** (the rule may have been built from them): {', '.join(sorted(train_exps)) or 'none'}, original signs. "
           "Everything else is held out.",
           "- **Tolerance:** D36 rules 1-4 (with D37's cascade rule) are judged on the held-out probes below.", ""]

    # Verdicts
    keys = sorted(set(whole["verdicts"]) | set(sub["verdicts"]))
    rows = [{"verdict": k, "whole brain": str(whole["verdicts"].get(k)), "subcircuit": str(sub["verdicts"].get(k)),
             "same": whole["verdicts"].get(k) == sub["verdicts"].get(k)} for k in keys]
    verdicts_same = all(r["same"] for r in rows)
    out += ["## Go/no-go verdicts and D32 picks", "", md_table(pd.DataFrame(rows)), ""]

    # Key groups
    cmp = compare_groups(keep(whole["df"]), keep(sub["df"]), KEY_GROUPS)
    cmp["set"] = ["train" if in_train[k] else "held-out" for k in cmp["condition"]]
    worst = cmp.assign(abs_rel=cmp["rel_error"].abs()).sort_values("abs_rel", ascending=False)
    out += ["## Key groups (mean Hz per neuron)", "", "Largest relative differences:", "",
            md_table(worst.drop(columns="abs_rel").head(15).assign(rel_error=lambda d: 100 * d["rel_error"])
                     .rename(columns={"rel_error": "rel. error %"})), ""]

    # Whole activity and speed
    rows = []
    for c in conds:
        tw = [whole["trials"][(c.key, t)] for t in used(c.key, c.trials)]
        ts = [sub["trials"][(c.key, t)] for t in used(c.key, c.trials)]
        if not tw:
            continue
        stim = {i for ids in c.inputs.values() for i in ids}
        f = activity_fidelity(neuron_rates(tw), neuron_rates(ts), sub_ids, exclude=stim)
        secs = np.mean([t["meta"]["n_frames"] * t["meta"]["frame_ms"] / 1000 for t in ts])
        rows.append({"condition": c.key, "set": "train" if in_train[c.key] else "held-out", **f,
                     "speed-up": np.mean([t["meta"]["run_s"] for t in tw]) / np.mean([t["meta"]["run_s"] for t in ts]),
                     "x real time": np.mean([t["meta"]["run_s"] for t in ts]) / secs})
    fid = pd.DataFrame(rows)

    summary = {"name": args.name, "neurons": manifest["neurons"], "connections": manifest["connections"],
               "spec": manifest["spec"], "verdicts_same": verdicts_same,
               "verdict_mismatches": [k for k in keys if whole["verdicts"].get(k) != sub["verdicts"].get(k)],
               "speed_up_median": float(fid["speed-up"].median()),
               "x_real_time_median": float(fid["x real time"].median()),
               "trials_per_condition": n_trials,
               "cascades_left_out": cascade_rows,
               "stuck_state": {"neurons_in_subcircuit": int(len(stuck_ids)), "of": int(len(stuck_all)),
                               "subcircuit_trials_stuck": [[k, int(t)] for k, t in zip(stuck_sub["condition"], stuck_sub["trial"])],
                               "whole_brain_trials_stuck": [[k, int(t)] for k, t in zip(stuck_whole["condition"], stuck_whole["trial"])],
                               "subcircuit_share_max": float(shares["subcircuit"].max())}}
    for s in ("train", "held-out"):
        summary[s] = headline(cmp[cmp["set"] == s], fid[fid["set"] == s])

    # D36 tolerance on the held-out, game-like conditions
    held = [c for c in conds if c.experiment.startswith(args.heldout)]
    tol = {}
    if held:
        hk = cmp[cmp["condition"].isin({c.key for c in held})]
        ok = [within_tolerance(w, x) for w, x in zip(hk["whole"], hk["subcircuit"])]
        bad = hk[[not o for o in ok]]
        m = t = 0
        for c in held:
            if "GF_R" not in c.watch:
                continue
            tw = [whole["trials"][(c.key, i)] for i in used(c.key, c.trials)]
            ts = [sub["trials"][(c.key, i)] for i in used(c.key, c.trials)]
            for g in ("GF_R", "GF_L"):
                a, b = first_spike_agreement(tw, ts, g)
                m, t = m + a, t + b
        by_type = kept_by_type(fid[fid["condition"].isin({c.key for c in held})], {c.key: c.experiment for c in conds})
        tol = {
            "same_verdicts": verdicts_same,
            "key_rates": bool(all(ok)),
            "key_rate_failures": [f"{r.condition} {r.group}: {r.whole:.1f} → {r.subcircuit:.1f} Hz" for r in bad.itertuples()],
            "first_spikes": (m / t >= 0.95) if t else None, "first_spikes_matched": f"{m}/{t}",
            "active_kept": bool(by_type) and all(ok for _, _, ok in by_type.values()),
            "active_kept_by_type": {e: {"median": m, "lowest": lo, "pass": ok} for e, (m, lo, ok) in by_type.items()},
            "cascade_pairs_left_out": len(skip),
            "subcircuit_stuck_trials": len(stuck_sub),
        }
        tol["pass"] = bool(tol["same_verdicts"] and tol["key_rates"] and tol["first_spikes"] and tol["active_kept"])
        summary["tolerance"] = tol

    def line(s):
        h = summary[s]
        if not h["conditions"]:
            return f"- **{s}:** no conditions"
        return (f"- **{s}** ({h['conditions']} conditions): key groups median |error| {100 * h['key_median_abs_rel_error']:.1f}%, "
                f"worst {100 * h['key_worst_abs_rel_error']:.1f}% ({h['key_worst']}); per-neuron r median {h['r_median']:.3f}, "
                f"lowest {h['r_min']:.3f}; active neurons kept median {100 * h['kept_active_median']:.0f}%, "
                f"lowest {100 * h['kept_active_min']:.0f}%")

    out += ["## Whole activity (every neuron, D34; stimulated neurons excluded)", "",
            line("train"), line("held-out"),
            f"- **Speed:** median {summary['speed_up_median']:.1f}× faster than the whole brain; "
            f"{summary['x_real_time_median']:.1f}× slower than real time (4 workers running at once).", "",
            *([f"## D36 tolerance on held-out probes ({args.heldout}*): **{'PASS' if tol['pass'] else 'FAIL'}**", "",
               f"1. Same go/no-go verdicts: {tol['same_verdicts']}",
               f"2. Key rates within 10% (1 Hz under 10 Hz): {tol['key_rates']}"
               + (f" (failures: {'; '.join(tol['key_rate_failures'][:8])})" if tol["key_rate_failures"] else ""),
               f"3. Giant Fiber first spikes within one frame in ≥ 95% of events: {tol['first_spikes']} ({tol['first_spikes_matched']})",
               f"4. In each probe type, median share of all whole-brain-active neurons kept ≥ 90%: {tol['active_kept']} ("
               + ", ".join(f"{e} {100 * v['median']:.0f}% (lowest {100 * v['lowest']:.0f}%)"
                           for e, v in tol["active_kept_by_type"].items()) + ")",
               "5. Closed-loop actions: judged from Step 2 on", ""] if tol else []),
            "## Runaway cascades and the stuck state (D37)", "",
            f"- **Trial pairs left out of rules 2-4** (either network's trial is a cascade: more than {cc['ratio']:g}x "
            f"and more than {cc['min_extra']:,} above its condition's median): {len(cascade_rows)}",
            *([md_table(pd.DataFrame(cascade_rows)), ""] if cascade_rows else []),
            f"- **Stuck state:** the subcircuit contains {len(stuck_ids):,} of the {len(stuck_all):,} stuck-state neurons. "
            f"Subcircuit trials with >= {cc['stuck_share']:.0%} of them firing: {len(stuck_sub)}"
            + (" (" + "; ".join(f"{r.condition} t{r.trial}" for r in stuck_sub.itertuples()) + ")" if len(stuck_sub) else "")
            + f"; highest share {100 * shares['subcircuit'].max():.1f}%. Whole-brain trials in the stuck state: {len(stuck_whole)}.",
            "",
            "## Per condition", "",
            md_table(fid.rename(columns={"kept_active": "kept active", "kept_inside": "kept (inside only)",
                                         "cut_active": "active but cut",
                                         "new_active": "newly active", "whole_active": "active (whole)"}), 3), ""]

    report = sub_out.parent / "validation.md"
    report.write_text("\n".join(out), encoding="utf-8")
    (sub_out.parent / "summary.json").write_text(json.dumps(summary, indent=2))
    fid.to_csv(sub_out.parent / "fidelity.csv", index=False)
    cmp.to_csv(sub_out.parent / "key_groups.csv", index=False)
    (sub_out.parent / "report.md").write_text("\n".join(sub["lines"]), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(out[:8]))
    print(line("train"), line("held-out"), sep="\n")
    print(f"Verdicts identical: {verdicts_same}; speed-up {summary['speed_up_median']:.1f}×")
    if tol:
        print(f"D36 tolerance on {args.heldout}*: {'PASS' if tol['pass'] else 'FAIL'} (rates {tol['key_rates']}, "
              f"first spikes {tol['first_spikes_matched']}, kept per type "
              + ", ".join(f"{e} {100 * v['median']:.0f}%" for e, v in tol["active_kept_by_type"].items())
              + f"; cascade pairs left out {len(skip)}, subcircuit stuck trials {len(stuck_sub)})")
    print(f"\nWrote {report.relative_to(ROOT)}, summary.json and the subcircuit's full pathway report (report.md)")


if __name__ == "__main__":
    main()
