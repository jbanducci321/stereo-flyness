"""Compare a subcircuit's pathway tests with the whole brain's (J5).

Run the tests on the subcircuit first (same seeds as the whole brain):
    uv run python scripts/run_pathway_tests.py --subcircuit example --jobs 4
    uv run python scripts/validate_subcircuit.py example

Writes results/subcircuits/<name>/validation.md (git-ignored): key-group rates side by side,
whole-activity fidelity per condition, the go/no-go verdicts on both networks, and speed. Only
conditions run on both networks are compared. Tolerances are not decided here (S5/J5).
"""

import argparse
import json
import math
import sys
import tomllib

import numpy as np
import pandas as pd

from analyse_pathway_tests import analyse, md_table
from run_pathway_tests import CONFIG, OUT, ROOT, conditions, network, runnable
from stereo_flyness.experiments.subcircuit_validation import activity_fidelity, compare_groups, neuron_rates

KEY_GROUPS = ["GF_R", "GF_L", "VS_R", "VS_L", "DNp20_R", "DNp22_R", "LPi09_R"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="subcircuit name (data/subcircuits/NAME)")
    args = parser.parse_args()

    cfg = tomllib.loads(CONFIG.read_text())
    path_comp, con_paths, sub_out = network(args.name)
    conds, skipped = runnable(conditions(cfg), path_comp, con_paths)
    # Compare only conditions with every trial saved on both networks
    conds = [c for c in conds if all(c.path(OUT, t).exists() and c.path(sub_out, t).exists() for t in range(c.trials))]
    if not conds:
        sys.exit("No conditions run on both networks yet. Run scripts/run_pathway_tests.py --subcircuit first.")
    manifest = json.loads((path_comp.parent / "manifest.json").read_text())
    sub_ids = set(pd.read_csv(path_comp, index_col=0).index)

    whole = analyse(OUT, cfg, conds, title="# Whole brain")
    sub = analyse(sub_out, cfg, conds, title=f"# Subcircuit {args.name}")

    out = [f"# Subcircuit validation: {args.name}", "",
           f"- **Size:** {manifest['neurons']:,} neurons ({100 * manifest['neurons'] / manifest['whole_brain']['neurons']:.1f}% of the brain), "
           f"{manifest['connections']:,} connections ({100 * manifest['connections'] / manifest['whole_brain']['connections']:.1f}%)",
           f"- **Spec:** `{json.dumps(manifest['spec'])}`",
           f"- **Compared:** {len(conds)} conditions run on both networks with the same seeds; "
           f"{len(skipped)} conditions can't run on this subcircuit (neurons or sign version missing).",
           "- How close is close enough isn't decided here (S5/J5); this report only measures.", ""]

    # Verdicts
    keys = sorted(set(whole["verdicts"]) | set(sub["verdicts"]))
    rows = [{"verdict": k, "whole brain": str(whole["verdicts"].get(k)), "subcircuit": str(sub["verdicts"].get(k)),
             "same": whole["verdicts"].get(k) == sub["verdicts"].get(k)} for k in keys]
    out += ["## Go/no-go verdicts and D32 picks", "", md_table(pd.DataFrame(rows)), ""]

    # Key groups
    cmp = compare_groups(whole["df"], sub["df"], KEY_GROUPS)
    worst = cmp.assign(abs_rel=cmp["rel_error"].abs()).sort_values("abs_rel", ascending=False)
    active = cmp[cmp["whole"] > 1]
    out += ["## Key groups (mean Hz per neuron)", "",
            f"- Over {len(active)} condition × group pairs where the whole brain fires (> 1 Hz): median |relative error| "
            f"{100 * active['rel_error'].abs().median():.1f}%, worst {100 * active['rel_error'].abs().max():.1f}%.", "",
            "Largest relative differences:", "",
            md_table(worst.drop(columns="abs_rel").head(15).assign(rel_error=lambda d: 100 * d["rel_error"])
                     .rename(columns={"rel_error": "rel. error %"})), ""]

    # Whole activity
    rows = []
    for c in conds:
        tw = [whole["trials"][(c.key, t)] for t in range(c.trials)]
        ts = [sub["trials"][(c.key, t)] for t in range(c.trials)]
        stim = {i for ids in c.inputs.values() for i in ids}
        f = activity_fidelity(neuron_rates(tw), neuron_rates(ts), sub_ids, exclude=stim)
        speed = np.mean([t["meta"]["run_s"] for t in tw]) / np.mean([t["meta"]["run_s"] for t in ts])
        rows.append({"condition": c.key, **f, "speed-up": speed})
    fid = pd.DataFrame(rows)
    fid_active = fid[fid["whole_active"] > 0]
    out += ["## Whole activity (every neuron, D34; stimulated neurons excluded)", "",
            f"- Correlation of per-neuron rates: median r = {fid_active['r'].median():.3f}, lowest {fid_active['r'].min():.3f} "
            f"(over {len(fid_active)} conditions with activity).",
            f"- Whole-brain-active neurons inside the subcircuit that still fire: median {100 * fid_active['kept_active'].median():.0f}%.",
            f"- Whole-brain-active neurons cut out of the subcircuit: median {fid_active['cut_active'].median():.0f} per condition.",
            f"- Simulation speed-up vs the whole brain (run time per trial): median {fid['speed-up'].median():.1f}×.", "",
            md_table(fid.rename(columns={"kept_active": "kept active", "cut_active": "active but cut",
                                         "new_active": "newly active", "whole_active": "active (whole)"}), 3), ""]

    report = sub_out.parent / "validation.md"
    report.write_text("\n".join(out), encoding="utf-8")
    (sub_out.parent / "report.md").write_text("\n".join(sub["lines"]), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(out))
    print(f"\nWrote {report.relative_to(ROOT)} and the subcircuit's full pathway report (report.md)")


if __name__ == "__main__":
    main()
