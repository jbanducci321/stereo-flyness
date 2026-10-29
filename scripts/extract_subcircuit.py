"""Extract a subcircuit from the whole brain from a spec file (J5).

A spec (configs/subcircuits/<name>.toml) is a union of `[[include]]` blocks, each one of:

    types = ["LC4", "LPLC2"]                     # every neuron of these cell types
    side = "right"                               #   (optional, with `types`)
    hops = { from_types = ["DNp01"], n = 2, direction = "in", min_synapses = 5 }
    hops = { from_active = { experiments = ["E1"] }, n = 1, direction = "in", min_synapses = 20 }
    active = { experiments = ["E1"], sign = "original", min_rate_hz = 1.0 }   # D34 record
    pathway_tests = true                         # every input and watched neuron of the tests

Which neurons belong in the real subcircuit is Shannyn's rule (S5); specs here are tools for
trying rules out. Output goes to git-ignored data/subcircuits/<name>/.

Usage:
    uv run python scripts/extract_subcircuit.py configs/subcircuits/example.toml
"""

import argparse
import sys
import tomllib
from pathlib import Path

import pandas as pd

from find_target_neurons import fetch_annotations
from reproduce_sugar import PATH_COMP, PATH_CON
from run_pathway_tests import CONFIG as PATHWAY_CONFIG, OUT as PATHWAY_OUT, conditions
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.brain.signs import CORRECTED_NAME
from stereo_flyness.brain.subcircuit import active_neurons, hops, retained_input, write_subcircuit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "subcircuits"
# Neurons whose input matters most for the game; reported after every extraction.
KEY_TYPES = ["DNp01", "DNp20", "DNp22", *[f"VS{i}" for i in range(1, 9)]]


_ACTIVE_CACHE = {}


def active(a, pathway_conds):
    """Neurons active in the whole-brain pathway-test trials named by an `active` table:
    `experiments`, `sign` or `signs` (default original), optional `min_rate_hz`, and optional
    `exclude_trials` ([[condition key, trial], ...]). Every side's runs are included."""
    key = repr(sorted(a.items()))
    if key not in _ACTIVE_CACHE:
        signs = a.get("signs", [a.get("sign", "original")])
        skip = {(k, t) for k, t in a.get("exclude_trials", [])}
        paths = [c.path(PATHWAY_OUT, t) for c in pathway_conds
                 if c.experiment in a["experiments"] and c.sign in signs
                 for t in range(c.trials) if c.path(PATHWAY_OUT, t).exists() and (c.key, t) not in skip]
        if not paths:
            sys.exit(f"No saved pathway-test trials for {a}. Run scripts/run_pathway_tests.py first.")
        _ACTIVE_CACHE[key] = active_neurons(paths, a.get("min_rate_hz", 0.0)), len(paths)
    return _ACTIVE_CACHE[key]


def select(spec, cells, con, pathway_conds):
    chosen, parts = set(), []
    for block in spec["include"]:
        if "types" in block:
            ids = set(cells.ids(*block["types"], side=block.get("side")))
            label = f"types {block['types']}" + (f" ({block['side']})" if block.get("side") else "")
        elif "hops" in block:
            h = block["hops"]
            if "from_active" in h:  # grow from the neurons active in some trials
                seeds = active(h["from_active"], pathway_conds)[0]
            else:
                seeds = cells.ids(*h["from_types"], side=h.get("side"))
            ids = hops(con, seeds, h["n"], h.get("direction", "both"), h.get("min_synapses", 1))
            label = f"hops {h}"
        elif "active" in block:
            ids, n_paths = active(block["active"], pathway_conds)
            label = f"active {block['active']} ({n_paths} trials)"
        elif block.get("pathway_tests"):
            ids = {i for c in pathway_conds for g in (c.inputs, c.watch) for v in g.values() for i in v}
            label = "pathway-test inputs and watched neurons"
        else:
            sys.exit(f"Unknown include block: {block}")
        parts.append((label, len(ids), len(ids - chosen)))
        chosen |= ids
    return chosen, parts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", type=Path)
    args = parser.parse_args()

    spec = tomllib.loads(args.spec.read_text())
    name = spec.get("name", args.spec.stem)
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    con = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity", "Excitatory"])
    pathway_conds = conditions(tomllib.loads(PATHWAY_CONFIG.read_text()))

    ids, parts = select(spec, cells, con, pathway_conds)
    corrected = ROOT / "data" / CORRECTED_NAME  # the steering tests also run on it (D27)
    manifest = write_subcircuit(PATH_COMP, PATH_CON, ids, OUT / name, spec,
                                path_con_corrected=corrected if corrected.exists() else None)

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Subcircuit '{name}': {manifest['neurons']:,} neurons, {manifest['connections']:,} connections, "
          f"{manifest['synapses']:,} synapses")
    wb = manifest["whole_brain"]
    print(f"  = {100 * manifest['neurons'] / wb['neurons']:.1f}% of neurons, "
          f"{100 * manifest['connections'] / wb['connections']:.1f}% of connections")
    for label, n, new in parts:
        print(f"  {label}: {n:,} neurons ({new:,} new)")

    keys = [(t, s, i) for t in KEY_TYPES for s in ("right", "left") for i in cells.ids(t, side=s)]
    kept = retained_input(con, ids, [i for _, _, i in keys])
    kept.insert(0, "neuron", [f"{t} {s}" for t, s, _ in keys])
    kept["in subcircuit"] = [i in ids for _, _, i in keys]
    print("\nInput kept for key neurons (share of whole-brain input synapses):")
    print(kept.drop(columns="flywire_id").to_string(index=False, float_format=lambda v: f"{100 * v:.0f}%"))

    missing = {i for c in pathway_conds for g in (c.inputs, c.watch) for v in g.values() for i in v} - ids
    print(f"\nPathway-test neurons missing (needed to validate the subcircuit): {len(missing):,}")
    print(f"Wrote {(OUT / name).relative_to(ROOT)} (git-ignored)")


if __name__ == "__main__":
    main()
