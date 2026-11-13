"""Write configs/ship_neurons_783.csv: the neurons the replay viewer's ship column needs (D53).

- T4c, T4d, T5c, T5d: our input ("up" and "down"), per side, for the bar labels' neuron counts.
- VS1-VS8: the pathway between our input and DNp22, shown as one square each per side.
- DNp20 and DNp22: DNp22 is the ship's readout; DNp20 is recorded only.

From the FlyWire v783 annotations (cell_type, side), as the runs pick them (`CellTypes.ids`), and
every ID checked to be in the model (data/Completeness_783.csv, hard rule 4). Like
configs/target_neurons_783.csv, it's committed so the viewer doesn't need the annotation table.

Usage:
    uv run python scripts/make_ship_neurons_config.py
"""

import sys
from pathlib import Path

import pandas as pd

from find_target_neurons import fetch_annotations
from reproduce_sugar import PATH_COMP
from stereo_flyness.brain.celltypes import CellTypes

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "configs" / "ship_neurons_783.csv"
TYPES = ("T4c", "T4d", "T5c", "T5d", *(f"VS{i}" for i in range(1, 9)), "DNp20", "DNp22")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    model = set(pd.read_csv(ROOT / "data" / "Completeness_783.csv").iloc[:, 0].astype("int64"))
    rows = [{"cell_type": t, "side": s, "flywire_id": i}
            for t in TYPES for s in ("left", "right") for i in cells.ids(t, side=s)]
    df = pd.DataFrame(rows)
    missing = set(df["flywire_id"]) - model
    if missing:
        sys.exit(f"{len(missing)} IDs aren't in the v783 model: {sorted(missing)[:5]}")
    if df["flywire_id"].duplicated().any():
        sys.exit("An ID appears under two types or sides.")
    df.to_csv(OUT, index=False)
    print(df.groupby(["cell_type", "side"]).size().unstack().to_string())
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(df)} neurons, all in v783.")


if __name__ == "__main__":
    main()
