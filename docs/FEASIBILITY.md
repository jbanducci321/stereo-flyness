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

## Target cell types (FlyWire v783)

| Cell type | Role | # neurons | Notes |
|---|---|---|---|
| LC4 | looming detector | | |
| LPLC2 | looming detector | | |
| DNp01 (Giant Fiber) | escape command | | |
| T4/T5 (vertical subtypes) | motion detectors | | |
| VS cells | vertical-motion integrators | | |
| DNOVS1/2 (candidates) | steering output | | |

## Subcircuit

- Extraction rule:
- Neurons / synapses:

## Benchmarks

- ms of compute per simulated game step (subcircuit):
- Whole-brain estimate:

## Risks and open questions

## Recommended stack
