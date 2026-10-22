"""Benchmark BrainStepper: compute cost per game frame vs network size.

Two ways of driving the brain are timed:
- step_loop: one `step()` (one Brian2 `Network.run`) per frame;
- run_frames: one `Network.run` for many frames, with a callback at each frame boundary.

Each network runs alone (one worker, no other brains competing for the CPU) under two
conditions:
- quiet: no input, so no spikes;
- active: sugar GRNs at 100 Hz, so spikes spread downstream.

Each condition is timed at two frame sizes:
- 16.7 ms: one frame at 60 fps;
- 4.2 ms: one physics tick at 240 Hz, rounded to whole 0.1 ms time steps.

Smaller networks are neighbourhoods grown outward from the sugar GRNs. Starting from the GRNs,
we add whole layers of connected neurons (inputs and outputs) until the target size is
reached, keeping all connections among the chosen neurons. They're **timing stand-ins**
shaped like a real subcircuit extraction, not circuits with any biological meaning.

Usage:
    uv run python scripts/benchmark_stepping.py
"""

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
from brian2 import Hz, defaultclock, ms

from reproduce_sugar import PATH_COMP, PATH_CON, SUGAR_GRNS_783
from stereo_flyness.brain.stepper import BrainStepper

ROOT = Path(__file__).resolve().parents[1]
PATH_RES = ROOT / "results" / "benchmark"

FRAMES = {"60fps_16.7ms": 1000 / 60 * ms, "240Hz_4.2ms": 1000 / 240 * ms}
LEVEL_S = 90  # approximate length of Stereo Madness, used to put costs in real terms
WARMUP = 3


def neighbourhood(con, seeds, n_target):
    """Grow outward from `seeds` one layer at a time (in- and out-partners) until >= n_target
    neurons. The last layer is trimmed to the neurons most strongly connected to the set."""
    selected, frontier = list(seeds), set(seeds)
    chosen = set(seeds)
    while len(selected) < n_target and frontier:
        out = con[con.Presynaptic_ID.isin(frontier)][["Postsynaptic_ID", "Connectivity"]]
        inn = con[con.Postsynaptic_ID.isin(frontier)][["Presynaptic_ID", "Connectivity"]]
        layer = pd.concat([out.set_axis(["id", "w"], axis=1), inn.set_axis(["id", "w"], axis=1)])
        layer = layer[~layer.id.isin(chosen)].groupby("id").w.sum().sort_values(ascending=False)
        new = list(layer.index[: n_target - len(selected)])
        selected += new
        chosen.update(new)
        frontier = set(new)
    return selected


def write_subset(con, ids, folder):
    """Write a sub-connectome in Shiu's file format (comp CSV + connectivity parquet)."""
    folder.mkdir(parents=True, exist_ok=True)
    index = {f: i for i, f in enumerate(ids)}
    sub = con[con.Presynaptic_ID.isin(index) & con.Postsynaptic_ID.isin(index)].copy()
    sub["Presynaptic_Index"] = sub.Presynaptic_ID.map(index)
    sub["Postsynaptic_Index"] = sub.Postsynaptic_ID.map(index)
    pd.DataFrame({"Completed": True}, index=pd.Index(ids)).to_csv(folder / "comp.csv")
    sub.to_parquet(folder / "con.parquet")
    return folder / "comp.csv", folder / "con.parquet", len(sub), int(sub.Connectivity.sum())


def time_step_loop(stepper, frame, n_frames):
    """ms per frame when calling step() once per frame (one Network.run each)."""
    for _ in range(WARMUP):
        stepper.step(frame)
    times = []
    for _ in range(n_frames):
        t0 = time.perf_counter()
        stepper.step(frame)
        times.append(time.perf_counter() - t0)
    return 1000 * np.median(times)


def time_run_frames(stepper, frame, n_frames, rate):
    """Marginal ms per frame with run_frames(): one Network.run, plus a callback that sets the
    input rate every frame (as the game would). Timing runs of n and 3n frames and taking
    the difference separates the per-frame cost from the one-off per-run setup cost."""
    align_to_frame(stepper, frame)
    callback = lambda i, counts: stepper.set_rate("sugar", rate)
    stepper.run_frames(WARMUP, frame, callback)
    elapsed = {}
    for n in (n_frames, 3 * n_frames):
        t0 = time.perf_counter()
        stepper.run_frames(n, frame, callback)
        elapsed[n] = time.perf_counter() - t0
    return 1000 * (elapsed[3 * n_frames] - elapsed[n_frames]) / (2 * n_frames)


def align_to_frame(stepper, frame):
    """Step forward to the next multiple of `frame`, which run_frames requires."""
    n_dt = int(round(float(frame / defaultclock.dt)))
    rem = int(round(float(stepper.t / defaultclock.dt))) % n_dt
    if rem:
        stepper.step((n_dt - rem) * defaultclock.dt)


def benchmark(label, path_comp, path_con, n_neurons, n_conn, n_syn, n_frames):
    rows = []
    t0 = time.perf_counter()
    stepper = BrainStepper(path_comp, path_con, inputs={"sugar": SUGAR_GRNS_783},
                           watch={"sugar": SUGAR_GRNS_783}, seed=0)
    build_s = time.perf_counter() - t0

    for condition, rate in [("quiet", 0 * Hz), ("active", 100 * Hz)]:
        stepper.set_rate("sugar", rate)
        for frame_name, frame in FRAMES.items():
            frame_ms = round(float(frame / ms), 1)  # actual step length after rounding to dt
            frames_per_level = LEVEL_S * 1000 / frame_ms
            timings = {
                "step_loop": time_step_loop(stepper, frame, n_frames),
                "run_frames": time_run_frames(stepper, frame, n_frames, rate),
            }
            for mode, ms_per_frame in timings.items():
                rows.append({
                    "network": label, "neurons": n_neurons, "connections": n_conn, "synapses": n_syn,
                    "build_s": round(build_s, 1), "condition": condition, "frame": frame_name,
                    "mode": mode, "ms_per_frame": round(ms_per_frame, 2),
                    "realtime_factor": round(ms_per_frame / frame_ms, 2),
                    "minutes_per_level": round(ms_per_frame * frames_per_level / 60000, 1),
                })
                print(f"  {label:>12} {condition:6} {frame_name:13} {mode:10} {ms_per_frame:9.1f} ms/frame", flush=True)
    del stepper
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sizes", default="1000,5000,20000,50000", help="neighbourhood sizes (neurons)")
    parser.add_argument("--frames", type=int, default=20, help="timed frames per condition")
    parser.add_argument("--skip-whole", action="store_true", help="skip the whole-brain benchmark")
    args = parser.parse_args()
    PATH_RES.mkdir(parents=True, exist_ok=True)

    con = pd.read_parquet(PATH_CON)
    rows = []
    for n in [int(s) for s in args.sizes.split(",")]:
        ids = neighbourhood(con, SUGAR_GRNS_783, n)
        comp, con_path, n_conn, n_syn = write_subset(con, ids, PATH_RES / f"subset_{n}")
        rows += benchmark(f"subset_{n}", comp, con_path, len(ids), n_conn, n_syn, args.frames)
        pd.DataFrame(rows).to_csv(PATH_RES / "stepping_benchmark.csv", index=False)

    if not args.skip_whole:
        rows += benchmark("whole_brain", PATH_COMP, PATH_CON, 138639, len(con), int(con.Connectivity.sum()), args.frames)

    df = pd.DataFrame(rows)
    df.to_csv(PATH_RES / "stepping_benchmark.csv", index=False)
    print()
    print(df[["network", "neurons", "connections", "build_s", "condition", "frame", "mode",
              "ms_per_frame", "realtime_factor", "minutes_per_level"]].to_string(index=False))


if __name__ == "__main__":
    main()
