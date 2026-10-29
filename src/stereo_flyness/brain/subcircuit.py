"""Cut a subcircuit out of the whole brain, in Shiu's file format (J5).

The rule for *which* neurons to keep is Shannyn's (S5) and isn't decided here. This module only
provides rule-agnostic building blocks:
- `hops`: every neuron within N synaptic steps of some seeds, with a synapse-count threshold;
- `active_neurons`: every neuron that fired in saved pathway-test trials (D34);
- `write_subcircuit`: writes the chosen neurons as a Completeness CSV + connectivity parquet that
  `BrainStepper` (and Shiu's `create_model`) load unchanged;
- `retained_input`: how much of each key neuron's input survives the cut.

Weights are never changed (D5). A subcircuit keeps exactly the connections whose two neurons are
both kept. Inputs from removed neurons are simply gone, which is the approximation J5 measures.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

DIRECTIONS = ("in", "out", "both")


def hops(con: pd.DataFrame, seeds, n: int, direction: str = "both", min_synapses: int = 1) -> set[int]:
    """Seeds plus every neuron reachable in at most `n` steps.

    A step follows one connection with at least `min_synapses` synapses: "in" goes to presynaptic
    partners (what drives the seeds), "out" to postsynaptic ones (what the seeds drive), "both"
    to either.
    """
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}")
    strong = con[con["Connectivity"] >= min_synapses]
    chosen, frontier = set(int(s) for s in seeds), set(int(s) for s in seeds)
    for _ in range(n):
        new = set()
        if direction in ("in", "both"):
            new |= set(strong.loc[strong["Postsynaptic_ID"].isin(frontier), "Presynaptic_ID"])
        if direction in ("out", "both"):
            new |= set(strong.loc[strong["Presynaptic_ID"].isin(frontier), "Postsynaptic_ID"])
        frontier = {int(i) for i in new} - chosen
        if not frontier:
            break
        chosen |= frontier
    return chosen


def active_neurons(trial_paths, min_rate_hz: float = 0.0) -> set[int]:
    """Neurons whose mean rate across the given saved trials is above `min_rate_hz` (D34 record).

    Includes stimulated neurons: whoever uses this for a rule decides whether that's wanted.
    """
    from stereo_flyness.experiments.pathway_tests import load_trial

    totals, secs = {}, 0.0
    for p in trial_paths:
        tr = load_trial(p)
        secs += tr["meta"]["n_frames"] * tr["meta"]["frame_ms"] / 1000
        for i, n in zip(tr["all_ids"], tr["all_spikes"].sum(axis=0)):
            totals[int(i)] = totals.get(int(i), 0) + int(n)
    if not secs:
        return set()
    return {i for i, n in totals.items() if n / secs > min_rate_hz}


def retained_input(con: pd.DataFrame, ids, targets) -> pd.DataFrame:
    """For each target neuron: its input synapses in the whole brain and the share kept."""
    ids = set(int(i) for i in ids)
    rows = []
    for t in targets:
        inp = con[con["Postsynaptic_ID"] == t]
        kept = inp[inp["Presynaptic_ID"].isin(ids)]
        total = int(inp["Connectivity"].sum())
        exc = inp[inp["Excitatory"] > 0]
        rows.append({
            "flywire_id": int(t), "input_synapses": total,
            "kept": int(kept["Connectivity"].sum()) / total if total else np.nan,
            "kept_excitatory": int(kept.loc[kept["Excitatory"] > 0, "Connectivity"].sum()) / int(exc["Connectivity"].sum())
            if len(exc) else np.nan,
            "kept_inhibitory": int(kept.loc[kept["Excitatory"] < 0, "Connectivity"].sum())
            / int(inp.loc[inp["Excitatory"] < 0, "Connectivity"].sum())
            if (inp["Excitatory"] < 0).any() else np.nan,
        })
    return pd.DataFrame(rows)


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _cut(con, ids, index):
    sub = con[con["Presynaptic_ID"].isin(ids) & con["Postsynaptic_ID"].isin(ids)].copy()
    sub["Presynaptic_Index"] = index.loc[sub["Presynaptic_ID"]].to_numpy()
    sub["Postsynaptic_Index"] = index.loc[sub["Postsynaptic_ID"]].to_numpy()
    return sub.reset_index(drop=True)


def write_subcircuit(path_comp, path_con, ids, folder, spec: dict | None = None,
                     path_con_corrected=None) -> dict:
    """Write the neurons `ids` (and every connection between them) in Shiu's file format.

    Neurons keep the whole brain's order, so indices are reproducible. Writes `comp.csv`,
    `con.parquet` and `manifest.json` (spec, sizes, source checksums) into `folder`, plus
    `con_corrected.parquet` cut the same way from the T4/T5-corrected copy (D27) if given.
    Returns the manifest.
    """
    comp = pd.read_csv(path_comp, index_col=0)
    con = pd.read_parquet(path_con)
    ids = set(int(i) for i in ids)
    if missing := sorted(ids - set(comp.index)):
        raise KeyError(f"IDs not in the connectome: {missing[:5]}")

    sub_comp = comp[comp.index.isin(ids)]
    index = pd.Series(np.arange(len(sub_comp)), index=sub_comp.index)
    sub = _cut(con, ids, index)

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    sub_comp.to_csv(folder / "comp.csv")
    sub.to_parquet(folder / "con.parquet")
    sources = [path_comp, path_con]
    if path_con_corrected is not None:
        _cut(pd.read_parquet(path_con_corrected), ids, index).to_parquet(folder / "con_corrected.parquet")
        sources.append(path_con_corrected)
    manifest = {
        "neurons": len(sub_comp), "connections": len(sub), "synapses": int(sub["Connectivity"].sum()),
        "whole_brain": {"neurons": len(comp), "connections": len(con), "synapses": int(con["Connectivity"].sum())},
        "source": {Path(p).name: _sha256(p) for p in sources},
        "spec": spec or {},
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
