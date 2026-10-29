"""Compare candidate subcircuit rules by size and by how much input they keep (task S5).

For each candidate rule, reports the subcircuit's size (neurons, connections, synapses) against
the D18 target (up to ~20k neurons / ~3M connections), and the share of input synapses kept for
the neurons we read out: the Giant Fiber (DNp01), DNp20 and the VS cells. A neuron's input is
"kept" if its presynaptic partner is inside the subcircuit. Input from outside is lost, which
changes the dynamics (PROJECT_BRIEF section 3.3), so a higher share means a more faithful cut.

Rules (all start from the core: inputs, VS1-VS8, LPi09 and the output neurons):
- paths<=k: every neuron on some input -> output path of at most k synapse hops.
- core+partners: every direct input and output partner of the output neurons.
Only connections with at least `min_syn` synapses count when growing the rule.

Nothing is decided here. This only gives numbers for the S5 proposal.

Usage:
    uv run python scripts/find_target_neurons.py     # downloads the cell-type labels
    uv run python scripts/subcircuit_sizes.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ANN = DATA / "flywire_annotations_v3.1.0_neurons.tsv"

VS_TYPES = [f"VS{i}" for i in range(1, 9)]
INPUTS = ["LC4", "LPLC2", "T4c", "T4d", "T5c", "T5d"]
OUTPUTS = ["DNp01", "DNp20", "DNp22"]
ALWAYS_IN = VS_TYPES + ["LPi09"]
# The Giant Fiber's top predicted-inhibitory partners (docs/pathway_tests.md, E5b).
GF_INHIBITORY = ["CB3707", "SAD014", "CL038", "PVLP010", "LHAD1g1", "CB0010", "CB0563"]

MIN_SYN = [1, 5, 10]
HOPS = [2, 3]
TARGET_NEURONS, TARGET_CONNECTIONS = 20_000, 3_000_000


def neighbours(nodes, con, direction):
    if direction == "down":
        return set(con.loc[con["Presynaptic_ID"].isin(nodes), "Postsynaptic_ID"])
    return set(con.loc[con["Postsynaptic_ID"].isin(nodes), "Presynaptic_ID"])


def hop_distances(start, con, direction, k):
    """Shortest hop count (<= k) from `start` to every reachable neuron."""
    dist = {n: 0 for n in start}
    front = set(start)
    for hop in range(1, k + 1):
        front = neighbours(front, con, direction) - dist.keys()
        dist.update({n: hop for n in front})
    return dist


def paths_rule(inputs, outputs, con, k):
    down = hop_distances(inputs, con, "down", k)
    up = hop_distances(outputs, con, "up", k)
    return {n for n, d in down.items() if n in up and d + up[n] <= k}


def main() -> int:
    if not ANN.exists():
        print("Cell-type labels missing. Run: uv run python scripts/find_target_neurons.py")
        return 1
    ann = pd.read_csv(ANN, sep="\t", dtype=str)
    ann["root_id"] = ann["root_id"].astype("int64")
    con = pd.read_parquet(
        DATA / "Connectivity_783.parquet", columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"]
    )

    def ids(types):
        return set(ann.loc[ann["cell_type"].isin(types), "root_id"])

    inputs, outputs = ids(INPUTS), ids(OUTPUTS)
    core = inputs | outputs | ids(ALWAYS_IN)
    gf, dnp20, vs, gf_inh = ids(["DNp01"]), ids(["DNp20"]), ids(VS_TYPES), ids(GF_INHIBITORY)

    def kept(nodes, targets):
        e = con[con["Postsynaptic_ID"].isin(targets)]
        return round(100 * e.loc[e["Presynaptic_ID"].isin(nodes), "Connectivity"].sum() / e["Connectivity"].sum(), 1)

    rows = []
    for m in MIN_SYN:
        strong = con[con["Connectivity"] >= m]
        rules = {f"paths<={k}": paths_rule(inputs, outputs, strong, k) | core for k in HOPS}
        rules["core+partners"] = core | neighbours(outputs, strong, "up") | neighbours(outputs, strong, "down")
        for name, nodes in rules.items():
            inside = con["Presynaptic_ID"].isin(nodes) & con["Postsynaptic_ID"].isin(nodes)
            n, conns = len(nodes), int(inside.sum())
            rows.append(
                {
                    "rule": name,
                    "min_syn": m,
                    "neurons": n,
                    "connections": conns,
                    "synapses": int(con.loc[inside, "Connectivity"].sum()),
                    "fits_D18": n <= TARGET_NEURONS and conns <= TARGET_CONNECTIONS,
                    "GF_input_%": kept(nodes, gf),
                    "DNp20_input_%": kept(nodes, dnp20),
                    "VS_input_%": kept(nodes, vs),
                    "GF_inhib_kept": f"{len(gf_inh & nodes)}/{len(gf_inh)}",
                }
            )
    pd.set_option("display.width", 200)
    print(pd.DataFrame(rows).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
