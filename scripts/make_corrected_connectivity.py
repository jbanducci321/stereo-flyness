"""Write the T4/T5 sign-corrected connectivity copy (D27) into data/.

Every connection *from* a T4a-d or T5a-d neuron is set to excitatory. Nothing else changes, and
the original Connectivity_783.parquet is only read. The copy lives in data/, so it is never
committed. Rebuild it on any machine with this script.

T4/T5 IDs come from the flywire_annotations v3.1.0 table (the same pinned, checksum-verified
download as find_target_neurons.py), and every ID is checked against Completeness_783.csv.

Usage:
    uv run python scripts/download_data.py      # connectome files first
    uv run python scripts/make_corrected_connectivity.py
"""

import sys

import pandas as pd

from find_target_neurons import DATA_DIR, fetch_annotations
from stereo_flyness.brain.signs import CORRECTED_NAME, T4T5_TYPES, correct_signs

ORIGINAL = DATA_DIR / "Connectivity_783.parquet"
COMPLETENESS = DATA_DIR / "Completeness_783.csv"


def main() -> None:
    if not ORIGINAL.exists() or not COMPLETENESS.exists():
        sys.exit("Connectome files missing. Run scripts/download_data.py first.")

    ann = pd.read_csv(fetch_annotations(), sep="\t", usecols=["root_id", "cell_type"], low_memory=False)
    t4t5 = ann[ann["cell_type"].isin(T4T5_TYPES)].copy()
    t4t5["root_id"] = t4t5["root_id"].astype("int64")

    model_ids = set(pd.read_csv(COMPLETENESS, index_col=0).index)
    missing = t4t5.loc[~t4t5["root_id"].isin(model_ids), "root_id"]
    if len(missing):
        sys.exit(f"{len(missing)} T4/T5 IDs are not in v783 (e.g. {missing.iloc[0]}). Stopping.")

    con = pd.read_parquet(ORIGINAL)
    corrected, report = correct_signs(con, t4t5["root_id"])

    # Per-type breakdown of what changed, for the record.
    flipped = con["Presynaptic_ID"].isin(t4t5["root_id"]) & (con["Excitatory"] < 0)
    by_type = (
        con[flipped]
        .merge(t4t5, left_on="Presynaptic_ID", right_on="root_id")
        .groupby("cell_type")
        .agg(neurons=("Presynaptic_ID", "nunique"), connections=("Connectivity", "size"),
             synapses=("Connectivity", "sum"))
        .reindex(T4T5_TYPES, fill_value=0)
    )
    by_type.insert(0, "of_neurons", t4t5.groupby("cell_type").size().reindex(T4T5_TYPES, fill_value=0))

    out = DATA_DIR / CORRECTED_NAME
    corrected.to_parquet(out)

    print(f"T4/T5 neurons (v3.1.0 annotations, all in v783): {len(t4t5):,}")
    print(f"  with outgoing connections: {report.neurons:,}")
    print(f"  with inhibitory outgoing signs (now excitatory): {report.neurons_flipped:,}")
    print(f"Connections flipped: {report.connections_flipped:,} of {report.rows_total:,}")
    print(f"Synapses flipped: {report.synapses_flipped:,}")
    print("\nFlipped, by type (neurons / connections / synapses):")
    print(by_type.to_string())
    print(f"\nWrote {out.relative_to(DATA_DIR.parent)} (original unchanged)")


if __name__ == "__main__":
    main()
