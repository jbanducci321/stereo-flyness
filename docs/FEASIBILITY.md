# Feasibility report (Step 0)

**Status:** in progress.

## Go / no-go

| Pathway | Verdict | Why |
|---|---|---|
| Escape (LC4/LPLC2 → Giant Fiber) → cube jump | TBD | |
| Motion (T4/T5 → VS → descending neurons) → ship | TBD | |

## Environment

- **Machine:** Jacob's laptop. Windows 11, 12 logical cores, 34 GB RAM.
- **Software:** Python 3.12.14 (via uv), Brian2 2.10.1, numpy 2.5.4, pandas 3.0.6. Shiu's code runs unmodified on these versions.
- **Compiler:** Visual Studio 2026 Build Tools (MSVC 14.50). Both Brian2 Cython runtime mode and C++ standalone mode compile and run.
  - **Fixed issue on Jacob's machine:** the Build Tools setup had paused partway, so the install was marked incomplete and Python couldn't find the compiler. Clicking **Resume** in the Visual Studio Installer fixed it, and Brian2 now finds MSVC automatically.

## Reproducing Shiu et al.

**Result: reproduced.** We stimulated the 21 right-hemisphere sugar GRNs (Poisson input) across the whole brain (138,639 neurons, 15.1M connections, 54.5M synapses, FlyWire v783), with 10 trials of 1 s each (`scripts/reproduce_sugar.py`).

| Sugar GRN rate | MN9 rate (mean ± SD) | Shiu reference (v630, 30 trials) | Active neurons |
|---|---|---|---|
| 100 Hz | 67.7 ± 5.2 Hz | 67.0 Hz | 398 |
| 150 Hz (model default) | 84.4 ± 5.0 Hz | 93.3 Hz* | 396 |

\* The reference file `sugarR.parquet` was run "at the default rate". Shiu's notebook text says that's 200 Hz, but `model.py` sets 150 Hz, so this comparison is less certain than the 100 Hz one.

- About 400 active neurons matches the notebook's "only about 400 neurons show activity".
- **Neuron IDs:** 20 of Shiu's 21 sugar GRN IDs are unchanged in v783. `720575940620900446` was re-segmented and replaced by `720575940639259967`, which shares 95% of the other GRNs' downstream partners. eonsystemspbc/fly-brain makes the same substitution. MN9 (`720575940660219265`) is unchanged.
- **Speed:** each 1 s whole-brain trial takes about 2.5 min on one core. Most of that is rebuilding the network (15M synapses) every trial, not simulating. With 4 parallel workers, 10 trials took about 6 min.

## Frame-by-frame stepping (closed loop)

**Result: works, and matches Shiu's model.** `BrainStepper` (`src/stereo_flyness/brain/stepper.py`) builds the whole brain once and advances it in game frames, with input that can change between frames. Validated with `scripts/validate_stepping.py` (results in `results/stepping/`).

**1. Stepped sugar test.** Sugar GRNs at 100 Hz for 1 s, delivered as 60 frames × 16.7 ms, 10 trials:

| Run | MN9 rate (mean ± SD) |
|---|---|
| Stepped (our changeable input) | **67.8 ± 3.9 Hz** |
| Unstepped (Shiu's PoissonInput) | 67.7 ± 5.2 Hz |

Welch t = 0.03, so there's no meaningful difference. Stepping and the replacement input mechanism (D16) don't change the model's behaviour.

**2. On/off switching.** Sugar input on 300 ms, off 300 ms, on 300 ms, 4 trials:

| Phase | MN9 rate |
|---|---|
| On | 60.8 ± 8.3 Hz |
| Off | 7.5 ± 2.8 Hz, all within the first ~1 frame after switching off |
| On again | 65.8 ± 7.2 Hz |

- MN9 starts firing about **2 frames (~35–50 ms) after input turns on** and stops within **~1 frame after it turns off**.
- So the brain follows changing input frame by frame, which is exactly what the game loop needs.

**First speed numbers:** ~1.8 s per 16.7 ms frame on the whole brain, with 4 workers running in parallel and one `step()` per frame. These are superseded by the Benchmarks section below.
- 4 brains running at once compete for the CPU and roughly double the per-brain cost.
- Calling `step()` once per frame adds a large fixed overhead, which `run_frames()` removes.

## Target cell types (FlyWire v783)

Source: flywire_annotations v3.1.0, all IDs checked against `Completeness_783.csv`. Full list in `configs/target_neurons_783.csv` (`scripts/find_target_neurons.py`). Synapse counts are given as left / right.

| Cell type | Role | # neurons (L / R) | Notes |
|---|---|---|---|
| LC4 | looming detector | 104 (54 / 50) | All 104 synapse onto the Giant Fiber on their own side: 374 / 431 synapses, excitatory |
| LPLC2 | looming detector | 210 (108 / 102) | 189 of 210 synapse onto the Giant Fiber: 458 / 622 synapses, excitatory |
| DNp01 (Giant Fiber) | escape command | 2 (1 / 1) | Receives both looming inputs. The jump itself (via TTM, partly gap junctions) is outside the brain data |
| T4c | motion detector (ON, upward) | 1,706 (864 / 842) | Strong input to VS cells (hundreds of T4/T5 cells per VS cell). Sign shows "mixed" because ~1–2% of T4/T5 are predicted GABA/glutamate; T4/T5 are known to be cholinergic, so likely prediction errors |
| T4d | motion detector (ON, downward) | 1,573 (796 / 777) | As T4c |
| T5c | motion detector (OFF, upward) | 1,541 (775 / 766) | As T4c |
| T5d | motion detector (OFF, downward) | 1,467 (740 / 727) | As T4c |
| VS cells (VS1–VS8) | vertical-motion integrators | 16 (8 / 8) | One of each type per side. Main input to DNp20 |
| DNp20 (DNOVS1) | steering output candidate | 2 (1 / 1) | Similar to DNOVS1 (Namiki et al. 2018, Supp. file 2). Strongest VS-driven descending neuron: 82 / 182 synapses from 6 / 8 VS cells |
| DNp22 (DNOVS2 or 3) | steering output candidate | 2 (1 / 1) | Namiki lists it as DNOVS2 *or* DNOVS3, so uncertain. Weaker VS input: 42 / 35 synapses from 2 VS cells per side |

## Subcircuit

- Extraction rule:
- Neurons / synapses:

## Benchmarks

`scripts/benchmark_stepping.py` (raw results in `results/benchmark/stepping_benchmark.csv`).
- **Setup:** one worker, no other brains running. Frames of 16.7 ms (60 fps) and 4.2 ms (240 Hz). Two conditions: quiet (no input) and active (sugar GRNs at 100 Hz).
- **Networks:** smaller networks are neighbourhoods grown outward from the sugar GRNs. They're **timing stand-ins**, not real subcircuits.

### Finding 1: one `step()` per frame is dominated by a fixed overhead
- Every `Network.run` call makes Brian2 regenerate its code objects and run garbage collection. That costs **~100–250 ms per call, whatever the network size**: a 1,000-neuron network cost ~120–260 ms per frame.
- **Fix:** `BrainStepper.run_frames()` (D17) runs many frames in one `Network.run`, with a Python callback at each frame boundary. It's tested to give results identical to a `step()` loop.

### Finding 2: with `run_frames()`, cost tracks network size (connections), not frame count

**Compute cost relative to real time** (ranges across quiet/active and both frame sizes):

| Network | Neurons | Connections | `run_frames` | `step()` loop | One 90 s level with `run_frames` |
|---|---|---|---|---|---|
| Neighbourhood | 1,000 | 0.09 M | 0.2–1.9× | 7–62× | ~0.3–3 min |
| Neighbourhood | 5,000 | 0.46 M | 0.9–5× | 8–57× | ~1–8 min |
| Neighbourhood | 20,000 | 2.7 M | 1.2–5× | 13–48× | ~2–8 min |
| Neighbourhood | 50,000 | 6.6 M | 5.5–9× | 23–59× | ~8–13 min |
| **Whole brain** | 138,639 | 15.1 M | **16–26×** | 47–128× | **~25–40 min** |

- **Build time** (after Brian2's one-time compile) is under 1 s for the neighbourhoods and ~2–10 s for the whole brain.
- **Noise:** each value is one timing run, and repeats vary by up to ~2×. Treat them as order-of-magnitude.
- **240 Hz is affordable.** With `run_frames()`, the cost depends on simulated time, not on how often the game talks to the brain, so querying the brain every 4.2 ms physics tick costs about the same per second of gameplay as every 16.7 ms frame.

### What this means for the plan
- **Subcircuit target: up to ~20k neurons / ~3M connections.** That keeps one 90 s level at a few minutes on one core.
  - With 4 parallel workers (each slower from contention), a tuning grid of ~25 dial settings × 8 training levels (200 level runs) takes roughly **2–7 hours**. That's overnight-feasible on the laptop.
  - Smaller subcircuits (~5k) are proportionally faster.
- **The whole brain is usable for occasional runs:** ~25–40 min per level on CPU. A whole-brain Stereo Madness comparison (Step 7) is possible on the laptop overnight; a GPU would make it routine.
- **Caveat:** the real looming input may drive more or less activity than the sugar input used here. Re-benchmark on the real subcircuit once it's extracted (J5).

## Risks and open questions

## Recommended stack
