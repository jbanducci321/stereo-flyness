"""Step 4 runs (D51): build the control networks, the code check, the open-loop check, two nights.

Everything is on the whole brain (D36) at R = 150 Hz (D50), R x f, the calibrated θ_full, collision
course: the Step 2 baseline of record's encoding, unchanged for every network and lesion.

`build`      every D51 control connectome into data/ (make_control_connectivity.py all), ~5 min.
`check`      LC4/LPLC2 silenced on 2 held-out levels at seed 0. Must give exactly 0 Giant Fiber
             spikes and 0 presses, or nothing else runs (D51). Prints PASS or FAIL. ~10 min.
`smoke`      one training level per control network, quietly: does each one build and run? ~15 min.
`open-loop`  the calibration loom (10 trials) for the intact brain, every lesion and random-lesion
             draw, and every control network, before the runs (described only). ~1 h.
`open-loop-recmatched`  the same check for the 6 recruited-matched draws only (D51 amendment). ~20 min.
`night1`     intact, E5b, E5c on the 20 held-out levels at seeds 0-2 (180 runs), blind. ~6 h.
`night2`     the random lesions, the recruited-matched controls (D51 amendment), (a) shuffle,
             (b) looming-kept, (c) relay-only, (d) random network (instance k at seed k; 480 runs),
             then always press, blind. ~8-10 h.

Each step calls the existing scripts, so every run is recorded and labelled exactly as theirs are.
Commit before running, so each run's recorded commit matches the code.

Usage:
    uv run python scripts/step4_runs.py build
    uv run python scripts/step4_runs.py check
    uv run python scripts/step4_runs.py night1 --dry-run     # print the commands only

Then score with scripts/step4_report.py.
"""

import argparse
import json
import subprocess
import sys

import pandas as pd

from run_pathway_tests import ROOT
from step3_grid import levels

SCRIPTS = ROOT / "scripts"
THETA_FULL = 200.0  # D43, configs/recruitment.toml
RATE = 150.0  # D50
SEEDS = (0, 1, 2)
TAG = "_step4"  # its own folders
LESIONS = {  # D51, as the pathway tests' E5 (configs/pathway_tests.toml)
    "E5b": "CB3707,SAD014,CL038,PVLP010,LHAD1g1,CB0010,CB0563",
    "E5c": "DNp70,PVLP122b,PVLP062,PVLP151",
}
CONTROLS = ("shuffle", "loomkept", "random")  # three instances each; relay is one network
CHECK_LEVELS = 2


def play(level_names, suite, seed, *extra, quiet=True, tag=TAG) -> list[str]:
    return [sys.executable, "-u", str(SCRIPTS / "play_cube.py"), *level_names, "--suite", suite,
            "--network", "whole_brain", "--theta-full", f"{THETA_FULL:g}", "--rate", f"{RATE:g}", "--rate-scaling",
            "--seed", str(seed), "--tag", tag, "--jobs", "4", *extra, *(["--quiet"] if quiet else [])]


def conditions(night: int) -> list[tuple[int, list[str]]]:
    """(seed, extra play_cube options) for every run set of a night (D51)."""
    if night == 1:
        out = [(s, []) for s in SEEDS]
        out += [(s, ["--silence", types, "--lesion-name", name]) for name, types in LESIONS.items() for s in SEEDS]
        return out
    out = [(k, ["--random-lesion", types, "--draw", str(k), "--lesion-name", name])
           for name, types in LESIONS.items() for k in SEEDS]
    out += [(k, ["--random-lesion", types, "--draw", str(k), "--recruited-matched", "--lesion-name", name])
            for name, types in LESIONS.items() for k in SEEDS]
    out += [(k, ["--control", f"{kind}_s{k}"]) for kind in CONTROLS for k in SEEDS]
    out += [(s, ["--control", "relay"]) for s in SEEDS]
    return out


def recmatched_sets() -> list[list[str]]:
    return [["--random-lesion", types, "--draw", str(k), "--recruited-matched", "--lesion-name", name]
            for name, types in LESIONS.items() for k in SEEDS]


def open_loop(only_recmatched: bool = False) -> list[list[str]]:
    base = [sys.executable, "-u", str(SCRIPTS / "calibrate_theta_full.py"), "--network", "whole_brain",
            "--rate-scaling", "--rate", f"{RATE:g}", "--grid", f"{THETA_FULL:g}", "--trials", "10",
            "--start-gap", "245", "--tag", TAG, "--jobs", "4"]
    sets = [[]]
    sets += [["--silence", types, "--lesion-name", name] for name, types in LESIONS.items()]
    sets += [["--random-lesion", types, "--draw", str(k), "--lesion-name", name]
             for name, types in LESIONS.items() for k in SEEDS]
    sets += [["--control", f"{kind}_s{k}"] for kind in CONTROLS for k in SEEDS] + [["--control", "relay"]]
    sets += recmatched_sets()
    return [base + s for s in (recmatched_sets() if only_recmatched else sets)]


def code_check(dry_run: bool) -> None:
    """D51: LC4/LPLC2 silenced must give exactly 0 Giant Fiber spikes and 0 presses."""
    names = levels("held_out")[:CHECK_LEVELS]
    cmd = play(names, "held_out", 0, "--silence", "LC4,LPLC2", "--lesion-name", "LC4LPLC2",
               quiet=True, tag=TAG + "check")
    print(" ".join(cmd[2:]), flush=True)
    if dry_run:
        return
    subprocess.run(cmd, cwd=SCRIPTS, check=True)
    folder = (ROOT / "results" / "closed_loop" / "whole_brain" / "held_out"
              / f"{THETA_FULL:g}deg_collision_R{RATE:g}_silence-LC4LPLC2{TAG}check" / "fly")
    spikes = presses = 0
    for name in names:
        run = json.loads((folder / name / "run.json").read_text(encoding="utf-8"))
        brain = pd.read_parquet(folder / name / "brain.parquet")
        spikes += int(brain[["spikes_GF_R", "spikes_GF_L"]].to_numpy().sum())
        presses += int(run["presses"])
    ok = spikes == 0 and presses == 0
    print(f"LC4/LPLC2 code check on {len(names)} levels: {spikes} Giant Fiber spikes, {presses} presses: "
          f"{'PASS' if ok else 'FAIL: nothing else runs until this is fixed (D51)'}")
    if not ok:
        sys.exit(1)


def commands(what: str) -> list[list[str]]:
    if what == "build":
        return [[sys.executable, "-u", str(SCRIPTS / "make_control_connectivity.py"), "all"]]
    if what == "smoke":
        first = levels("training")[:1]
        return [play(first, "training", 0, "--control", c, tag=TAG + "smoke")
                for c in [f"{k}_s0" for k in CONTROLS] + ["relay"]]
    if what == "open-loop":
        return open_loop()
    if what == "open-loop-recmatched":
        return open_loop(only_recmatched=True)
    if what in ("night1", "night2"):
        names = levels("held_out")
        cmds = [play(names, "held_out", seed, *extra) for seed, extra in conditions(int(what[-1]))]
        if what == "night2":
            cmds.append([sys.executable, "-u", str(SCRIPTS / "reference_flies.py"), "--network", "whole_brain",
                         "--reference", "always"])
        return cmds
    raise ValueError(what)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["build", "check", "smoke", "open-loop", "open-loop-recmatched", "night1", "night2"])
    parser.add_argument("--dry-run", action="store_true", help="print the commands without running them")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.what == "check":
        code_check(args.dry_run)
        return
    cmds = commands(args.what)
    for i, cmd in enumerate(cmds, 1):
        print(f"[{i}/{len(cmds)}] " + " ".join(c if " " not in c else f'"{c}"' for c in cmd[2:])
              if args.dry_run or args.what not in ("night1", "night2") else f"[{i}/{len(cmds)}] run set {i}", flush=True)
        if not args.dry_run:
            subprocess.run(cmd, cwd=SCRIPTS, check=True)


if __name__ == "__main__":
    main()
