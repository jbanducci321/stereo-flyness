"""Checkpoint check: BrainStepper on the whole brain matches Shiu's model.

1. Stepped sugar test. Sugar GRNs at a steady 100 Hz for 1 s, delivered as 60 game frames
   (16.7 ms each) instead of one continuous run. MN9's rate should match the unstepped
   reproduction (scripts/reproduce_sugar.py, which uses Shiu's own PoissonInput).
2. On/off switching. Sugar input on 300 ms, off 300 ms, on 300 ms, frame by frame. MN9
   should follow the input: fire, fall silent, fire again.

Usage:
    uv run python scripts/validate_stepping.py --n-run 10 --n-proc 4
"""

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
from brian2 import Hz, ms
from joblib import Parallel, delayed

from reproduce_sugar import MN9, PATH_COMP, PATH_CON, SUGAR_GRNS_783
from stereo_flyness.brain.stepper import BrainStepper

ROOT = Path(__file__).resolve().parents[1]
PATH_RES = ROOT / "results" / "stepping"
REFERENCE = ROOT / "results" / "sugar" / "sugarR_100.parquet"  # unstepped run at 100 Hz

FRAME = 1000 / 60 * ms  # one game frame at 60 fps; rounds to 16.7 ms (167 time steps)
RATE = 100 * Hz
PHASES = [("on", RATE), ("off", 0 * Hz), ("on_again", RATE)]
FRAMES_PER_PHASE = 18  # 18 x 16.7 ms = 300.6 ms


def make_stepper(seed):
    return BrainStepper(PATH_COMP, PATH_CON, inputs={"sugar": SUGAR_GRNS_783},
                        watch={"mn9": [MN9]}, seed=seed)


def stepped_trial(seed):
    t0 = time.perf_counter()
    stepper = make_stepper(seed)
    build_s = time.perf_counter() - t0

    stepper.set_rate("sugar", RATE)
    step_times, n_spikes = [], 0
    for _ in range(60):
        t0 = time.perf_counter()
        n_spikes += int(stepper.step(FRAME)["mn9"][0])
        step_times.append(time.perf_counter() - t0)
    return {"seed": seed, "mn9_rate_hz": n_spikes / float(stepper.t), "sim_time_s": float(stepper.t),
            "build_s": build_s, "step_ms_median": 1000 * np.median(step_times)}


def switching_trial(seed):
    stepper = make_stepper(seed)
    rows, frame = [], 0
    for phase, rate in PHASES:
        stepper.set_rate("sugar", rate)
        for k in range(FRAMES_PER_PHASE):
            n = int(stepper.step(FRAME)["mn9"][0])
            rows.append({"seed": seed, "frame": frame, "phase": phase, "frame_in_phase": k,
                         "t_end_ms": 1000 * float(stepper.t), "mn9_spikes": n})
            frame += 1
    return rows


def welch_t(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def reference_rates():
    df = pd.read_parquet(REFERENCE)
    n_run = df["trial"].max() + 1
    per_trial = df[df["flywire_id"] == MN9].groupby("trial").size()
    return per_trial.reindex(range(n_run), fill_value=0).to_numpy() / 1.0  # trials are 1 s


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n-run", type=int, default=10, help="stepped sugar trials")
    parser.add_argument("--n-switch", type=int, default=4, help="on/off switching trials")
    parser.add_argument("--n-proc", type=int, default=4, help="parallel workers (each holds the whole brain)")
    args = parser.parse_args()
    PATH_RES.mkdir(parents=True, exist_ok=True)

    # 1. Stepped sugar test
    trials = pd.DataFrame(Parallel(n_jobs=args.n_proc)(delayed(stepped_trial)(s) for s in range(args.n_run)))
    trials.to_csv(PATH_RES / "stepped_sugar.csv", index=False)
    print("\n=== Stepped sugar test (100 Hz, 60 frames x 16.7 ms) ===")
    print(f"MN9 stepped:   {trials.mn9_rate_hz.mean():.1f} +/- {trials.mn9_rate_hz.std(ddof=0):.1f} Hz (n={len(trials)})")
    if REFERENCE.exists():
        ref = reference_rates()
        t = welch_t(trials.mn9_rate_hz, ref)
        verdict = "PASS" if abs(t) < 2 else "CHECK"
        print(f"MN9 unstepped: {ref.mean():.1f} +/- {ref.std():.1f} Hz (n={len(ref)}, Shiu's PoissonInput)")
        print(f"Welch t = {t:.2f} -> {verdict} (|t| < 2 means no meaningful difference)")
    print(f"Build: {trials.build_s.mean():.0f} s per brain; step: {trials.step_ms_median.median():.0f} ms per frame (median)")

    # 2. On/off switching
    rows = Parallel(n_jobs=args.n_proc)(delayed(switching_trial)(1000 + s) for s in range(args.n_switch))
    frames = pd.DataFrame([r for trial in rows for r in trial])
    frames.to_csv(PATH_RES / "switching.csv", index=False)
    print("\n=== On/off switching (300 ms on, 300 ms off, 300 ms on) ===")
    phase_s = FRAMES_PER_PHASE * float(FRAME)
    by_phase = frames.groupby(["seed", "phase"])["mn9_spikes"].sum().unstack() / phase_s
    for phase, _ in PHASES:
        print(f"MN9 during {phase:9s}: {by_phase[phase].mean():5.1f} +/- {by_phase[phase].std(ddof=0):4.1f} Hz")
    for phase in ("on", "on_again"):
        first = frames[(frames.phase == phase) & (frames.mn9_spikes > 0)].groupby("seed")["frame_in_phase"].min()
        print(f"First MN9 spike after '{phase}': frame {first.mean():.1f} of phase on average (frame 0 = first 16.7 ms)")
    off = frames[frames.phase == "off"]
    last = off[off.mn9_spikes > 0].groupby("seed")["frame_in_phase"].max().reindex(frames.seed.unique(), fill_value=-1)
    print(f"Last MN9 spike after 'off': frame {last.mean():.1f} of phase on average (-1 = none)")
    print(f"\nResults written to {PATH_RES}")


if __name__ == "__main__":
    main()
