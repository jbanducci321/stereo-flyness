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
ones, which are the fair test. Tolerances are not decided here (S5/J5).
"""

import argparse
import dataclasses
import json
import sys
import tomllib

import numpy as np
import pandas as pd

from analyse_pathway_tests import analyse, md_table
from run_pathway_tests import CONFIG, OUT, ROOT, conditions, network, runnable
from stereo_flyness.experiments.subcircuit_validation import activity_fidelity, compare_groups, neuron_rates

KEY_GROUPS = ["GF_R", "GF_L", "VS_R", "VS_L", "DNp20_R", "DNp22_R", "LPi09_R"]


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

    whole = analyse(OUT, cfg, conds, title="# Whole brain")
    sub = analyse(sub_out, cfg, conds, title=f"# Subcircuit {args.name}")

    n_trials = sorted({c.trials for c in conds})
    out = [f"# Subcircuit validation: {args.name}", "",
           f"- **Size:** {manifest['neurons']:,} neurons ({100 * manifest['neurons'] / manifest['whole_brain']['neurons']:.1f}% of the brain), "
           f"{manifest['connections']:,} connections ({100 * manifest['connections'] / manifest['whole_brain']['connections']:.1f}%)",
           f"- **Spec:** `{json.dumps(manifest['spec'])}`",
           f"- **Compared:** {len(conds)} conditions run on both networks with the same seeds ({'/'.join(map(str, n_trials))} trials each); "
           f"{len(skipped)} conditions can't run on this subcircuit (neurons or sign version missing).",
           f"- **Training conditions** (the rule may have been built from them): {', '.join(sorted(train_exps)) or 'none'}, original signs. "
           "Everything else is held out.",
           "- How close is close enough isn't decided here (S5/J5); this report only measures.", ""]

    # Verdicts
    keys = sorted(set(whole["verdicts"]) | set(sub["verdicts"]))
    rows = [{"verdict": k, "whole brain": str(whole["verdicts"].get(k)), "subcircuit": str(sub["verdicts"].get(k)),
             "same": whole["verdicts"].get(k) == sub["verdicts"].get(k)} for k in keys]
    verdicts_same = all(r["same"] for r in rows)
    out += ["## Go/no-go verdicts and D32 picks", "", md_table(pd.DataFrame(rows)), ""]

    # Key groups
    cmp = compare_groups(whole["df"], sub["df"], KEY_GROUPS)
    cmp["set"] = ["train" if in_train[k] else "held-out" for k in cmp["condition"]]
    worst = cmp.assign(abs_rel=cmp["rel_error"].abs()).sort_values("abs_rel", ascending=False)
    out += ["## Key groups (mean Hz per neuron)", "", "Largest relative differences:", "",
            md_table(worst.drop(columns="abs_rel").head(15).assign(rel_error=lambda d: 100 * d["rel_error"])
                     .rename(columns={"rel_error": "rel. error %"})), ""]

    # Whole activity and speed
    rows = []
    for c in conds:
        tw = [whole["trials"][(c.key, t)] for t in range(c.trials)]
        ts = [sub["trials"][(c.key, t)] for t in range(c.trials)]
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
               "trials_per_condition": n_trials}
    for s in ("train", "held-out"):
        summary[s] = headline(cmp[cmp["set"] == s], fid[fid["set"] == s])

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
            md_table(fid.rename(columns={"kept_active": "kept active", "cut_active": "active but cut",
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
    print(f"\nWrote {report.relative_to(ROOT)}, summary.json and the subcircuit's full pathway report (report.md)")


if __name__ == "__main__":
    main()
