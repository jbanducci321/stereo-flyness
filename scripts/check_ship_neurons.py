"""Check the ship's neurons against FlyWire v783 (Step 5, hard rule 4).

For the input (T4c/T5c "up", T4d/T5d "down", both eyes) and the readout (DNp22, with DNp20 for
comparison), from Shannyn's draft (docs/notes/ship_proposals.md):
1. every ID in configs/target_neurons_783.csv is the same set as the annotation table's, per type
   and side, and every one is in the model (data/Completeness_783.csv);
2. the wiring from each eye: T4/T5 onto VS cells, and VS cells onto DNp22, per side.
The judged pathway tests drove the right eye; the left eye's responses are in scripts/ship_pathway_check.py.

Reads only; writes nothing. Results are in docs/notes/ship_neuron_check.md.

Usage:
    uv run python scripts/check_ship_neurons.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "configs" / "target_neurons_783.csv"

INPUT = {"down": ["T4d", "T5d"], "up": ["T4c", "T5c"]}
READOUT = ["DNp22", "DNp20"]
VS = [f"VS{i}" for i in range(1, 9)] + ["VSm", "VST1", "VST2"]
SIDES = ("left", "right")


def id_check(cfg: pd.DataFrame, ann: pd.DataFrame, model: set[int]) -> tuple[pd.DataFrame, bool]:
    rows = []
    for t in [t for g in INPUT.values() for t in g] + READOUT:
        for s in SIDES:
            c = set(cfg.loc[(cfg.cell_type == t) & (cfg.side == s), "flywire_id"])
            a = set(ann.loc[(ann.cell_type == t) & (ann.side == s), "root_id"])
            rows.append({"type": t, "side": s, "config": len(c), "annotations": len(a),
                         "same set": c == a, "in v783": len(c & model)})
    out = pd.DataFrame(rows)
    ok = bool(out["same set"].all() and (out["in v783"] == out["config"]).all() and (out["config"] > 0).all())
    return out, ok


def wiring(con: pd.DataFrame, ann: pd.DataFrame) -> pd.DataFrame:
    """Synapses per VS type and side: from each eye's "down" and "up" input, and from everything."""
    ty, sd = ann.set_index("root_id")["cell_type"], ann.set_index("root_id")["side"]
    e = con.assign(pre=con.Presynaptic_ID.map(ty), post=con.Postsynaptic_ID.map(ty),
                   pre_side=con.Presynaptic_ID.map(sd), post_side=con.Postsynaptic_ID.map(sd))
    onto_vs = e[e.post.isin(VS)]
    cols = {}
    for s in SIDES:
        here = onto_vs[onto_vs.post_side == s]
        for name, types in INPUT.items():
            cols[f"{name} {s[0].upper()}"] = here[here.pre.isin(types) & (here.pre_side == s)].groupby("post").Connectivity.sum()
        cols[f"all in {s[0].upper()}"] = here.groupby("post").Connectivity.sum()
    for s in SIDES:
        vd = e[e.pre.isin(VS) & (e.post == "DNp22") & (e.pre_side == s) & (e.post_side == s)]
        cols[f"to DNp22 {s[0].upper()}"] = vd.groupby("pre").Connectivity.sum()
    out = pd.DataFrame(cols).reindex(VS).fillna(0).astype(int)
    out.loc["total"] = out.sum()
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    model = set(pd.read_csv(DATA / "Completeness_783.csv").iloc[:, 0].astype("int64"))
    cfg = pd.read_csv(CONFIG)
    ann = pd.read_csv(DATA / "flywire_annotations_v3.1.0_neurons.tsv", sep="\t", low_memory=False,
                      usecols=["root_id", "cell_type", "side"]).astype({"root_id": "int64"})
    con = pd.read_parquet(DATA / "Connectivity_783.parquet", columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"])
    ids, ok = id_check(cfg, ann, model)
    print("IDs (config against annotations, and in v783):\n" + ids.to_string(index=False))
    print(f"\nAll IDs check out: {'yes' if ok else 'NO'}\n")
    print("Synapses onto each VS type, by side (input from the same side's eye), and VS onto DNp22:")
    print(wiring(con, ann).to_string())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
