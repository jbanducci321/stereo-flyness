"""Step 4's network and lesion options (D51), shared by play_cube.py and calibrate_theta_full.py.

`--control NAME` swaps in data/Connectivity_783_<NAME>.parquet (scripts/make_control_connectivity.py;
whole brain only, D36). `--silence` lesions every neuron of the listed cell types, both sides, with
Shiu's silence() (D5). `--random-lesion` silences that many random neurons instead, each matched to
one of them by sign and total output (within 10%), never a Giant Fiber, LC4/LPLC2 or lesion-set
neuron, chosen by `--draw` (a fixed seed). `--lesion-name` is a short name for the folder.

Every run records its connectivity file and SHA-256, and exactly which neurons were silenced.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from find_target_neurons import DATA_DIR
from reproduce_sugar import PATH_CON
from stereo_flyness.brain.controls import control_path, file_sha256, matched_random_lesion


@dataclass
class Step4:
    path_con: Path
    silence: list[int] = field(default_factory=list)
    meta: dict = field(default_factory=dict)  # merged into each run's run.json
    suffix: str = ""  # added to the settings folder name


def add_args(parser) -> None:
    parser.add_argument("--control", help="Step 4: play on data/Connectivity_783_<CONTROL>.parquet (whole brain only)")
    parser.add_argument("--silence", help="Step 4: comma-separated cell types to silence, both sides (D5)")
    parser.add_argument("--random-lesion", help="Step 4: silence random neurons matched to these cell types (D51)")
    parser.add_argument("--draw", type=int, help="which random-lesion draw (its seed), with --random-lesion")
    parser.add_argument("--lesion-name", help="short name for the lesion in the folder (e.g. E5b); default: the types")


def resolve(args, cells, default_con) -> Step4:
    """The connectivity file, silenced IDs, run.json fields and folder suffix for these options."""
    path_con, notes = Path(default_con), []
    if args.control:
        if args.network != "whole_brain":
            sys.exit("Controls run on the whole brain (D36): add --network whole_brain.")
        path_con = control_path(DATA_DIR, args.control)
        if not path_con.exists():
            sys.exit(f"No control connectome at {path_con}. Build it with scripts/make_control_connectivity.py.")
        notes.append(f"control {args.control}")
    if args.silence and args.random_lesion:
        sys.exit("Use --silence or --random-lesion, not both.")
    if (args.random_lesion is None) != (args.draw is None):
        sys.exit("--random-lesion and --draw go together.")
    types = [t.strip() for t in (args.silence or args.random_lesion or "").split(",") if t.strip()]
    silence = [i for t in types for i in cells.ids(t)]  # every ID checked against v783
    if args.random_lesion:
        full = pd.read_parquet(PATH_CON, columns=["Presynaptic_ID", "Connectivity", "Excitatory"])
        exclude = cells.ids("DNp01") + cells.ids("LC4", "LPLC2")
        silence = matched_random_lesion(full, silence, exclude, seed=args.draw)
        notes.append(f"random lesion matched to {'+'.join(types)}, draw {args.draw} ({len(silence)} neurons)")
    elif types:
        notes.append(f"silenced {'+'.join(types)} ({len(silence)} neurons)")
    meta = {"connectome": {"file": path_con.name, "sha256": file_sha256(path_con)},
            "silenced": {"name": args.lesion_name, "types": types, "random_draw": args.draw, "ids": silence}}
    if notes:
        meta["status"] = f"Step 4 (D51): {'; '.join(notes)}"
    name = args.lesion_name or "+".join(types)
    suffix = (f"_{args.control}" if args.control else "") + (
        f"_randlesion-{name}_d{args.draw}" if args.random_lesion else f"_silence-{name}" if types else "")
    return Step4(path_con, silence, meta, suffix)
