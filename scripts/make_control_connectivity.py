"""Write a degree-preserving shuffled connectome (Step 4 control, draft) into data/.

Reads Connectivity_783.parquet (never changed) and writes
data/Connectivity_783_shuffle_s<seed>.parquet, then checks it (stereo_flyness.brain.controls)
and prints its SHA-256 so runs can record which file they used. The file lives in data/, so it
is never committed; rebuild it anywhere from the same seed.

Not run for any Step 4 result yet: the Step 4 plan (docs/notes/step4_proposal.md) isn't agreed.

Usage:
    uv run python scripts/make_control_connectivity.py --seed 0
"""

import argparse
import sys

import pandas as pd

from find_target_neurons import DATA_DIR
from stereo_flyness.brain.controls import check_shuffle, control_path, degree_preserving_shuffle, file_sha256

ORIGINAL = DATA_DIR / "Connectivity_783.parquet"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    if not ORIGINAL.exists():
        sys.exit("Connectome files missing. Run scripts/download_data.py first.")

    con = pd.read_parquet(ORIGINAL)
    shuffled, report = degree_preserving_shuffle(con, args.seed)
    fails = check_shuffle(con, shuffled)
    if fails:
        sys.exit("Shuffle check failed: " + "; ".join(fails))

    out = control_path(DATA_DIR, f"shuffle_s{args.seed}")
    shuffled.to_parquet(out, index=False)
    print(f"Wrote {out.name}: {report.connections:,} connections, {report.shuffled:,} shuffled, "
          f"{report.rounds} swap rounds, {report.unchanged:,} unchanged by chance. Checks pass.")
    print(f"sha256 {file_sha256(out)}")


if __name__ == "__main__":
    main()
