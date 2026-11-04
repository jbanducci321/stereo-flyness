"""Write the Step 4 control connectomes (D51) into data/.

Reads Connectivity_783.parquet (never changed), writes data/Connectivity_783_<name>.parquet, checks
it (stereo_flyness.brain.controls) and prints its SHA-256 so runs can record which file they used.
The files live in data/, so they're never committed; rebuild them anywhere from the same seeds.

Kinds (D51):
- shuffle   (a) degree-preserving shuffle                         -> shuffle_s<seed>
- loomkept  (b) the same, keeping the LC4/LPLC2 -> Giant Fiber
                connections in place and allowing no new ones        -> loomkept_s<seed>
- relay     (c) only the LC4/LPLC2 -> Giant Fiber connections        -> relay
- random    (d) random network, same neurons and connection count   -> random_s<seed>

Usage:
    uv run python scripts/make_control_connectivity.py shuffle --seed 0
    uv run python scripts/make_control_connectivity.py all          # every D51 network (seeds 0-2)
"""

import argparse
import sys

import pandas as pd

from find_target_neurons import DATA_DIR, fetch_annotations
from reproduce_sugar import PATH_COMP
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.brain.controls import (
    check_shuffle, control_path, degree_preserving_shuffle, file_sha256, pathway_mask, random_network, relay_only)

ORIGINAL = DATA_DIR / "Connectivity_783.parquet"
LOOMING, GIANT_FIBER = ("LC4", "LPLC2"), ("DNp01",)  # D41's driven types; the output (D42)
SEEDS = (0, 1, 2)  # instance k plays at Poisson seed k (D51)


def build(kind, seed, con, cells, flyids) -> tuple[str, pd.DataFrame, list[str], str]:
    """(name, table, check failures, one-line description) for one control network."""
    loom, gf = cells.ids(*LOOMING), cells.ids(*GIANT_FIBER)
    if kind == "shuffle":
        out, r = degree_preserving_shuffle(con, seed)
        return (f"shuffle_s{seed}", out, check_shuffle(con, out),
                f"{r.shuffled:,} shuffled, {r.rounds} swap rounds, {r.unchanged:,} unchanged by chance")
    if kind == "loomkept":
        keep = pathway_mask(con, loom, gf)
        index = {f: i for i, f in enumerate(flyids)}
        forbid = ([index[i] for i in loom], [index[i] for i in gf])
        out, r = degree_preserving_shuffle(con, seed, keep=keep, forbid=forbid)
        fails = check_shuffle(con, out, keep=keep, forbid=forbid)
        if not (pathway_mask(out, loom, gf) == keep).all():
            fails.append("looming -> Giant Fiber connections differ from the original")
        return (f"loomkept_s{seed}", out, fails,
                f"{r.kept:,} kept, {r.shuffled:,} shuffled, {r.rounds} swap rounds, {r.unchanged:,} unchanged by chance")
    if kind == "relay":
        out = relay_only(con, loom, gf)
        fails = [] if len(out) == pathway_mask(con, loom, gf).sum() else ["relay size differs"]
        return "relay", out, fails, f"{len(out):,} connections, {out['Connectivity'].sum():,} synapses"
    if kind == "random":
        out = random_network(con, flyids, seed)
        fails = []
        if len(out) != len(con) or (out["Presynaptic_Index"] == out["Postsynaptic_Index"]).any() \
                or out.duplicated(["Presynaptic_Index", "Postsynaptic_Index"]).any():
            fails.append("size, self-connections or duplicates")
        if sorted(out["Connectivity"]) != sorted(con["Connectivity"]):
            fails.append("synapse counts differ from the real distribution")
        return f"random_s{seed}", out, fails, f"{len(out):,} connections placed at random"
    raise ValueError(kind)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=["shuffle", "loomkept", "relay", "random", "all"])
    parser.add_argument("--seed", type=int, help="required except for relay and all")
    args = parser.parse_args()
    if not ORIGINAL.exists():
        sys.exit("Connectome files missing. Run scripts/download_data.py first.")
    if args.kind not in ("relay", "all") and args.seed is None:
        sys.exit("--seed is required for this kind.")

    con = pd.read_parquet(ORIGINAL)
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)  # IDs checked against v783
    flyids = pd.read_csv(PATH_COMP, index_col=0).index.to_numpy()
    jobs = ([(k, s) for k in ("shuffle", "loomkept", "random") for s in SEEDS] + [("relay", 0)]
            if args.kind == "all" else [(args.kind, args.seed or 0)])
    for kind, seed in jobs:
        name, out, fails, text = build(kind, seed, con, cells, flyids)
        if fails:
            sys.exit(f"{name}: check failed: " + "; ".join(fails))
        path = control_path(DATA_DIR, name)
        out.to_parquet(path, index=False)
        print(f"Wrote {path.name}: {text}. Checks pass. sha256 {file_sha256(path)}", flush=True)


if __name__ == "__main__":
    main()
