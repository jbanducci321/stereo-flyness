"""Find our target cell types in FlyWire v783 (task S2).

Looks up the escape and steering cell types in the FlyWire cell-type annotations, checks every
ID against the model's neuron list (Completeness_783.csv), and summarises the connections we
care about (e.g. LC4 -> Giant Fiber). Writes configs/target_neurons_783.csv.

The annotation table comes from github.com/flyconnectome/flywire_annotations, pinned to release
v3.1.0. Its `root_id` column is already in the v783 release. It is downloaded into data/ (never
committed) and checked against a SHA-256.

DNOVS1/2 are not in the table under those names, so they are NOT in the output. Instead the
script lists the descending neurons that VS cells connect to most strongly, as candidates to
match against the literature by hand.

Usage:
    uv run python scripts/download_data.py        # connectome files first
    uv run python scripts/find_target_neurons.py
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_CSV = ROOT / "configs" / "target_neurons_783.csv"

ANN_RELEASE = "v3.1.0"
ANN_NAME = "flywire_annotations_v3.1.0_neurons.tsv"
ANN_URL = (
    "https://raw.githubusercontent.com/flyconnectome/flywire_annotations/"
    f"{ANN_RELEASE}/supplemental_files/Supplemental_file1_neuron_annotations.tsv"
)
ANN_SHA256 = "9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be"
SOURCE = f"flywire_annotations {ANN_RELEASE} (cell_type)"

# Cell types to collect, grouped by pathway. Names are exact `cell_type` values.
TARGETS = {
    "escape": ["LC4", "LPLC2", "DNp01"],
    "steering": ["T4c", "T4d", "T5c", "T5d"] + [f"VS{i}" for i in range(1, 9)],
}
# Connections to summarise: (presynaptic types, postsynaptic types).
CONNECTIONS = [
    (["LC4"], ["DNp01"]),
    (["LPLC2"], ["DNp01"]),
    (["T4c", "T4d", "T5c", "T5d"], [f"VS{i}" for i in range(1, 9)]),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_annotations() -> Path:
    dest = DATA_DIR / ANN_NAME
    if dest.exists() and sha256(dest) == ANN_SHA256:
        return dest
    print(f"Downloading cell-type annotations ({ANN_RELEASE}, ~32 MB)...")
    tmp = dest.with_suffix(".part")
    urllib.request.urlretrieve(ANN_URL, tmp)
    if sha256(tmp) != ANN_SHA256:
        tmp.unlink()
        raise SystemExit("Annotation file checksum mismatch. Stopping.")
    tmp.replace(dest)
    return dest


def select_targets(ann: pd.DataFrame, model_ids: set[int]) -> pd.DataFrame:
    """Rows for every target cell type, with an `in_model` check against v783."""
    wanted = [t for types in TARGETS.values() for t in types]
    sel = ann[ann["cell_type"].isin(wanted)].copy()
    sel["flywire_id"] = sel["root_id"].astype("int64")
    sel["in_model"] = sel["flywire_id"].isin(model_ids)
    order = {t: i for i, t in enumerate(wanted)}
    return sel.sort_values(["cell_type", "side", "flywire_id"], key=lambda c: c.map(order) if c.name == "cell_type" else c)


def to_config(sel: pd.DataFrame) -> pd.DataFrame:
    """The configs/target_neurons_783.csv table (columns agreed in PROJECT_BRIEF S2)."""
    out = pd.DataFrame(
        {
            "cell_type": sel["cell_type"].values,
            "side": sel["side"].fillna("").values,
            "flywire_id": sel["flywire_id"].values,
            "source": SOURCE,
            "notes": "",
        }
    )
    return out


def connection_summary(con: pd.DataFrame, id2type: dict[int, str], id2side: dict[int, str], pre, post):
    """Synapse counts from `pre` types onto `post` types, split by pre side -> post side."""
    pre_ids = {i for i, t in id2type.items() if t in pre}
    post_ids = {i for i, t in id2type.items() if t in post}
    e = con[con["Presynaptic_ID"].isin(pre_ids) & con["Postsynaptic_ID"].isin(post_ids)].copy()
    e["pre_side"] = e["Presynaptic_ID"].map(id2side)
    e["post_side"] = e["Postsynaptic_ID"].map(id2side)
    e["post_type"] = e["Postsynaptic_ID"].map(id2type)
    return (
        e.groupby(["post_type", "pre_side", "post_side"])
        .agg(
            pre_neurons=("Presynaptic_ID", "nunique"),
            synapses=("Connectivity", "sum"),
            sign=("Excitatory", lambda s: "+" if (s > 0).all() else ("-" if (s < 0).all() else "mixed")),
        )
        .reset_index()
    )


def vs_descending_partners(con, ann, vs_types, top=15):
    """Descending neurons that VS cells synapse onto, strongest first (DNOVS candidates)."""
    vs_ids = set(ann.loc[ann["cell_type"].isin(vs_types), "root_id"].astype("int64"))
    dn = ann[ann["super_class"] == "descending"].copy()
    dn["root_id"] = dn["root_id"].astype("int64")
    dn = dn.set_index("root_id")
    e = con[con["Presynaptic_ID"].isin(vs_ids) & con["Postsynaptic_ID"].isin(dn.index)].copy()
    e["dn_type"] = e["Postsynaptic_ID"].map(dn["cell_type"])
    e["dn_side"] = e["Postsynaptic_ID"].map(dn["side"])
    e["hemibrain_type"] = e["Postsynaptic_ID"].map(dn["hemibrain_type"])
    return (
        e.groupby(["dn_type", "hemibrain_type", "dn_side"], dropna=False)
        .agg(synapses=("Connectivity", "sum"), from_vs_cells=("Presynaptic_ID", "nunique"))
        .sort_values("synapses", ascending=False)
        .head(top)
        .reset_index()
    )


def main() -> int:
    comp = DATA_DIR / "Completeness_783.csv"
    conn = DATA_DIR / "Connectivity_783.parquet"
    if not (comp.exists() and conn.exists()):
        print("Connectome files missing. Run: uv run python scripts/download_data.py")
        return 1

    ann = pd.read_csv(fetch_annotations(), sep="\t", dtype=str)
    model_ids = set(pd.read_csv(comp, index_col=0).index.astype("int64"))

    sel = select_targets(ann, model_ids)
    missing = sel[~sel["in_model"]]
    print("\n== Counts by cell type and side ==")
    counts = sel.groupby(["cell_type", "side"]).size().unstack(fill_value=0)
    print(counts.reindex([t for ts in TARGETS.values() for t in ts]).fillna(0).astype(int).to_string())
    print(f"\nIDs checked against Completeness_783.csv: {sel['in_model'].sum()} / {len(sel)} found")
    if len(missing):
        print("NOT in the model (do not use):")
        print(missing[["cell_type", "side", "flywire_id"]].to_string(index=False))

    found = set(sel["cell_type"])
    for types in TARGETS.values():
        for t in types:
            if t not in found:
                print(f"WARNING: no neurons labelled {t}")

    con = pd.read_parquet(
        conn, columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity", "Excitatory"]
    )
    good = sel[sel["in_model"]]
    id2type = dict(zip(good["flywire_id"], good["cell_type"]))
    id2side = dict(zip(good["flywire_id"], good["side"]))
    for pre, post in CONNECTIONS:
        print(f"\n== {'/'.join(pre)} -> {post[0] if len(post) == 1 else 'VS cells'} ==")
        print(connection_summary(con, id2type, id2side, pre, post).to_string(index=False))

    print("\n== DNOVS candidates: descending neurons VS cells synapse onto (strongest first) ==")
    print("Match these to DNOVS1/2 from the literature before adding them to the config.")
    print(vs_descending_partners(con, ann, TARGETS["steering"][4:]).to_string(index=False))

    OUT_CSV.parent.mkdir(exist_ok=True)
    to_config(good).to_csv(OUT_CSV, index=False)
    print(f"\nWrote {len(good)} neurons to {OUT_CSV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
