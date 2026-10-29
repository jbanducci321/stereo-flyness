"""How fast a subcircuit (or the whole brain) runs on game-length, game-like input (J5).

The input is a stand-in for a level, not an encoding decision (that's T4): first half "cube",
an expanding looming burst on both sides every 1.25 s (like the P1 probe); second half "ship",
constant horizontal motion with downward and upward motion alternating (like P3/P4). Driven
frame by frame at 240 Hz with `run_frames`, as the closed loop will be.

Usage:
    uv run python scripts/benchmark_subcircuit.py d36_nocascade_75 --seconds 30
    uv run python scripts/benchmark_subcircuit.py whole_brain --seconds 10
    uv run python scripts/benchmark_subcircuit.py d36_nocascade_75 --seconds 30 --parallel 4

Prints compute time relative to real time and what one 30 s / 90 s level would cost.
"""

import argparse
import sys
import time

import numpy as np
from joblib import Parallel, delayed

from find_target_neurons import fetch_annotations
from run_pathway_tests import CONFIG, PATH_COMP, network
from stereo_flyness.brain.celltypes import CellTypes
from stereo_flyness.experiments.pathway_tests import DT_MS, frame_steps

FRAME_MS = 1000 / 240


def schedule(cells, seconds: float):
    """Input groups and a (frames, groups) rate array for the stand-in level."""
    both = lambda *t: cells.ids(*t, side="right") + cells.ids(*t, side="left")  # noqa: E731
    rng = np.random.default_rng(0)
    chunks = np.array_split(rng.permutation(both("LC4", "LPLC2")), 4)
    inputs = {f"loom_{k}": sorted(int(i) for i in c) for k, c in enumerate(chunks)}
    inputs |= {"horizontal": both("T4a", "T4b", "T5a", "T5b"), "down": both("T4d", "T5d"),
               "up": both("T4c", "T5c")}
    names = list(inputs)
    frame = frame_steps(FRAME_MS) * DT_MS
    n = int(round(seconds * 1000 / frame))
    rates = np.zeros((n, len(names)))
    for i in range(n):
        t = i * frame / 1000
        if t < seconds / 2:  # cube: a looming burst every 1.25 s, chunks on 75 ms apart, 300 ms long
            phase = (t % 1.25) * 1000
            if phase < 300:
                for k in range(int(phase // 75) + 1):
                    rates[i, names.index(f"loom_{k}")] = 150
        else:  # ship: scrolling plus up/down steering, switching every 150 ms
            rates[i, names.index("horizontal")] = 50
            rates[i, names.index("down" if int((t * 1000) // 150) % 2 == 0 else "up")] = 100
    return inputs, rates, frame


def run(path_comp, path_con, inputs, rates, frame_ms, seed):
    from brian2 import Hz, ms

    from stereo_flyness.brain.stepper import BrainStepper

    t0 = time.perf_counter()
    st = BrainStepper(path_comp, path_con, inputs=inputs, watch={}, seed=seed)
    build = time.perf_counter() - t0
    names = list(inputs)

    def set_rates(i):
        for j, g in enumerate(names):
            st.set_rate(g, rates[i, j] * Hz)

    def on_frame(i, _):
        if i + 1 < len(rates):
            set_rates(i + 1)

    set_rates(0)
    t0 = time.perf_counter()
    st.run_frames(len(rates), frame_ms * ms, on_frame)
    return build, time.perf_counter() - t0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="subcircuit name, or whole_brain")
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--parallel", type=int, default=1, help="runs at once (as in a tuning grid)")
    args = parser.parse_args()

    path_comp, con_paths, _ = network(None if args.name == "whole_brain" else args.name)
    cells = CellTypes.from_files(fetch_annotations(), PATH_COMP)
    inputs, rates, frame = schedule(cells, args.seconds)
    res = Parallel(n_jobs=args.parallel)(
        delayed(run)(path_comp, con_paths["original"], inputs, rates, frame, seed) for seed in range(args.parallel))
    builds, runs = zip(*res)
    x = float(np.mean(runs)) / args.seconds
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{args.name}: {args.seconds:g} s simulated, {args.parallel} at once: build {np.mean(builds):.1f} s, "
          f"run {np.mean(runs):.0f} s = {x:.1f}× real time → one 30 s level ≈ {30 * x / 60:.1f} min, "
          f"90 s level ≈ {90 * x / 60:.1f} min (per run)")


if __name__ == "__main__":
    main()
