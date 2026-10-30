# Feasibility report (Step 0)

**Status:** in progress.

## Go / no-go

Pathway-test verdicts (J4), judged by rules agreed before the full runs (D28–D35). Details: `docs/pathway_results.md`. The interim subcircuit (J5) reproduces them within the tolerance agreed in advance (D36/D37; see "Subcircuit" below). Step 0's overall go/no-go is decided together in T3.

| Pathway | Pathway tests | Why |
|---|---|---|
| Escape (LC4/LPLC2 → Giant Fiber) → cube jump | **GO** | Right Giant Fiber fires in 10/10 trials at every input rate (77–205 Hz), clearly above the left; first spike within ~8–13 ms; stops within ~3–13 ms of input off; LC10a and sugar controls give 0 |
| Motion (T4/T5 → VS → descending neurons) → ship | **GO** (original signs; corrected also GO) | "Down" drives VS cells and DNp20 in 10/10 trials; "up" gives 0 and suppresses "down" via LPi09; horizontal motion drives VS less than "down" |

Sign version carried forward (D28): **original**.

| Check | Result | Why |
|---|---|---|
| Interim subcircuit reproduces the whole brain (J5, D36 tolerance) | **PASS** | On all 7 held-out probes: identical verdicts, key rates within 7.1%, Giant Fiber first spikes 360/360 within one frame, 97–100% of active neurons kept. 11× faster than the whole brain; a 30 s tuning grid fits overnight (~7.2 h) |

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
| T4c | motion detector (ON, upward) | 1,706 (864 / 842) | No direct input to VS cells. Reaches them only through inhibitory LPi neurons (34,629 synapses onto LPi09), so upward motion inhibits VS. 1.7% of neurons predicted inhibitory |
| T4d | motion detector (ON, downward) | 1,573 (796 / 777) | Main direct input to VS cells: 19,174 synapses (28% of VS input). **13.7% of neurons predicted inhibitory** although T4/T5 are cholinergic, giving 14% of its VS synapses the wrong sign (D27) |
| T5c | motion detector (OFF, upward) | 1,541 (775 / 766) | As T4c: no direct VS input, 42,124 synapses onto LPi09. 1.9% predicted inhibitory |
| T5d | motion detector (OFF, downward) | 1,467 (740 / 727) | As T4d: 18,601 synapses onto VS cells (27% of VS input). **12.1% predicted inhibitory**, 13% of its VS synapses (D27) |
| VS cells (VS1–VS8) | vertical-motion integrators | 16 (8 / 8) | One of each type per side. Main input to DNp20 |
| DNp20 (DNOVS1) | steering output candidate | 2 (1 / 1) | Similar to DNOVS1 (Namiki et al. 2018, Supp. file 2). Strongest VS-driven descending neuron: 82 / 182 synapses from 6 / 8 VS cells |
| DNp22 (DNOVS2 or 3) | steering output candidate | 2 (1 / 1) | Namiki lists it as DNOVS2 *or* DNOVS3, so uncertain. Weaker VS input: 42 / 35 synapses from 2 VS cells per side |

## Pathway tests

**Result: both pathways GO.** 640 whole-brain trials, run 2026-10-28 (`scripts/run_pathway_tests.py`, `scripts/analyse_pathway_tests.py`). Full tables: `docs/pathway_results.md`. The headlines:

- **Escape:**
  - LC4 + LPLC2 drive the right Giant Fiber from 77 Hz (25 Hz input) to 205 Hz (200 Hz input).
  - The left Giant Fiber also fires (44–102 Hz), entirely through excitatory partners (DNp70, PVLP151). Silencing them removes it.
  - Recruitment threshold: ~5–12 of the 50 right LC4 neurons.
- **Steering:**
  - Downward motion drives the right VS cells (113–241 Hz) and DNp20 (73–140 Hz).
  - Upward motion gives 0, and added to downward motion suppresses it by 88–100%.
  - The corrected signs give ~10–15% stronger responses with the same pattern.
- **Caveats:**
  - latencies have 4.2 ms resolution;
  - firing rates are far above biological ones under direct drive;
  - the input encoding (looming, direction) is ours.

## Subcircuit

**Result: the interim subcircuit passes the D36 tolerance on every held-out probe.**
- Built and validated 2026-10-30 (J5). The rule and the tolerance were both agreed before validation (D36, D37).
- Details: `docs/subcircuit_candidates.md` (the candidate comparison, "Interim size" and "J5 4c") and `docs/cascades.md`.

**Extraction rule (D36 + D37):**
- Every neuron that fires in whole-brain runs of the game's inputs: LC4/LPLC2 and T4/T5, right, left and both sides, both sign versions. Runaway-cascade trials are left out.
- Plus every neuron with a ≥ 30-synapse connection onto one of them.
- Plus every pathway-test neuron.
- Connectome weights are unchanged (D5).
- Spec: `configs/subcircuits/interim.toml`.

**Size:**
- **33,480 neurons** (24.1% of the brain) and **3,391,290 connections** (22.5%; 17.6M synapses).
- The Giant Fibers keep 87–88% of their input synapses (82% of their inhibitory input). The VS cells keep ~99–100%, and DNp20/22 91–97%.

**Speed** (Jacob's laptop, i7-10750H, 6 cores / 12 threads):
- On game-like input (`scripts/benchmark_subcircuit.py`): 8.9× slower than real time alone, 17.2× each with 4 at once.
- So a 200-run tuning grid on 30 s practice levels takes **~7.2 h**, inside D37's 10 h limit.
- On the pathway tests it runs a median 11.2× faster than the whole brain. On busier, game-like input that drops to ~2.4–3.5×.

**Validation:** the same 1,410 trials as the whole brain, with the same seeds. The tolerance is judged on the held-out probes P1–P7, which were never used to build it:

| D36 rule | Result |
|---|---|
| 1. Same go/no-go verdicts and D32 picks | Pass: all 10 identical |
| 2. Key-group rates within 10% (1 Hz under 10 Hz), both sides | Pass: worst 7.1% (P6 DNp20_L, 2.8 → 3.0 Hz) |
| 3. Giant Fiber first spikes within one frame in ≥ 95% of events | Pass: 360/360 |
| 4. Median share of all whole-brain-active neurons kept, ≥ 90% per probe type | Pass: 97–100% (lowest single condition 93%) |
| 5. Same closed-loop actions | Judged from Step 2 on |

**Caveats:**
- **The training runs match exactly by construction.** Only spikes pass between neurons in this model, so a subcircuit that contains every neuron that fired in a run reproduces it exactly. The probes are the evidence.
- **The probes are our own game-like stand-ins.** The final subcircuit is rebuilt and validated again once T4 fixes the input encoding (D36).
- **The stuck state** (below and `docs/cascades.md`):
  - The subcircuit partly reproduces the whole brain's 3 runaway cascades, and entered the stuck state once on its own (a control trial).
  - D37's cascade test can't flag a stuck subcircuit, because it holds only 1,904 of the 8,189 stuck-state neurons. The stuck-state share can, so closed-loop runs on the subcircuit should flag with it (D38).

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
  - **Superseded by D37 (2026-10-30):**
    - Practice levels for tuning are **30 s**.
    - The limit is now a tuning time: a 200-run grid in ≤ 10 h with 4 at once on this laptop.
    - The interim subcircuit (33,480 neurons / 3.39M connections) measured 8.9× slower than real time alone and 17.2× each with 4 at once on game-like input, so a grid takes **~7.2 h**.
    - Game-like input is much busier than the sugar input used here: the subcircuit is only ~2.4–3.5× faster than the whole brain (`docs/subcircuit_candidates.md`).
  - With 4 parallel workers (each slower from contention), a tuning grid of ~25 dial settings × 8 training levels (200 level runs) takes roughly **2–7 hours**. That's overnight-feasible on the laptop.
  - Smaller subcircuits (~5k) are proportionally faster.
- **The whole brain is usable for occasional runs:** ~25–40 min per level on CPU. A whole-brain Stereo Madness comparison (Step 7) is possible on the laptop overnight; a GPU would make it routine.
- **Caveat:** the real looming input may drive more or less activity than the sugar input used here. Re-benchmark on the real subcircuit once it's extracted (J5).
  - **Done (J5):** game-like input is much busier. See "Subcircuit" above and D37.

## Risks and open questions

- **Horizontal motion drives the ship pathway too** (pathway tests, S3): at 50 Hz, horizontal T4/T5 input gives DNp20 64 Hz vs 104 Hz for downward motion. A ship input encoding that drives horizontal-motion neurons (e.g. for the level scrolling) would push the controller. Decide in T4.
- **Sustained Giant Fiber firing:** the Giant Fiber fires continuously while driven and for up to ~30 ms after (E2), unlike a real escape (a few spikes). The output rule (T4) must turn this into single jumps.
- **Whole-brain results must survive the subcircuit:** the left Giant Fiber route and the feed-forward inhibition (E5) depend on non-looming partners, so S5's rule should keep them.
  - **Kept in the interim subcircuit (J5):**
    - The E5 conditions match exactly, but they were used to build it, so that's by construction.
    - The real evidence is the held-out probes: both Giant Fibers are within tolerance in all of them, on every side.
    - To be re-checked on the final rebuild after T4.
- **Runaway "stuck" state** (`docs/cascades.md`; D37, D38):
  - About 0.2% per simulated second, the whole brain falls into a self-sustaining state of ~8,300 neurons, centred on the mushroom body. Nothing stops it, even with all input off.
  - It leaves the Giant Fibers and VS silent when there's no input.
  - **Tested in a larger stuck state we could switch on** (~12,500 neurons): a loom still drives the right Giant Fiber, but at 112 vs 186 Hz, first spike 25–29 ms vs 4.2 ms, and the left Giant Fiber goes silent. The natural state's effect is untested (`docs/cascades.md`, follow-up (a)).
  - Treated as a property of the model. Stuck runs are kept, flagged and counted (D38). Step 2 compares jump timing in stuck vs normal runs.

## Recommended stack
