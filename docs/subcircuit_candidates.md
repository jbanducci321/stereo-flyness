# Subcircuit candidates (J5, input for S5)

*Jacob, J5 checkpoint 3, 2026-10-28. These are options measured for Shannyn's subcircuit rule (S5). **None of them is the rule.** S5 is Shannyn's decision, agreed together and logged in `docs/decisions.md`.*

## Why a subcircuit, and what this measures

- **The problem:** the whole brain runs ~16–26× slower than real time (FEASIBILITY, Benchmarks), far too slow for tuning on hundreds of level runs.
- **The fix:** a subcircuit keeps only the neurons that matter and every connection between them, with weights unchanged (D5). D18 set the target at up to ~20k neurons / ~3M connections.
- **What a subcircuit gives up:** inputs from the neurons it drops.
- **What we measured:** six candidate rules, each run through the pathway tests (same seeds as the whole brain, 3 trials per condition) and compared with the whole brain on:
  - the go/no-go verdicts (D29–D31);
  - the key neurons' rates (Giant Fibers, VS, DNp20/22, LPi09);
  - **every neuron's activity** (D34): the share of whole-brain-active neurons that stay active, and the per-neuron rate correlation.
- **A fair test:** activity-based rules were built only from **E1 and S1 (original signs)**. Everything else (E2–E5, S2, S3, corrected signs) is **held out**, so it tests how a rule copes with input it wasn't built from, as it will in the game.

Tools: `scripts/extract_subcircuit.py` (specs in `configs/subcircuits/candidates/`), `scripts/run_pathway_tests.py --subcircuit`, `scripts/validate_subcircuit.py`, `scripts/compare_subcircuits.py`. Per-candidate reports are in git-ignored `results/subcircuits/<name>/`.

## The candidates

Every candidate also keeps the pathway-test neurons (inputs and watched groups: 6,563 neurons, mostly the right T4/T5 inputs), so it can be validated. "Outputs" are the Giant Fibers (DNp01), DNp20, DNp22 and VS1–8, both sides.

| Candidate | Rule | Family |
|---|---|---|
| `w1_1hop` | Neurons 1 step upstream of the outputs (connections ≥ 5 synapses) | Wiring only |
| `w2_2hop` | 2 steps upstream (≥ 20 synapses) | Wiring only |
| `w3_3hop` | 3 steps upstream (≥ 30 synapses) | Wiring only |
| `a1_active` | Every neuron active in the training experiments (E1, S1) | Activity |
| `a2_active_inputs` | `a1` plus the strong inputs (≥ 30 synapses) of every active neuron | Activity + wiring |
| `h1_hybrid` | `w2` ∪ `a1` | Wiring + activity |

## Results

| Candidate | Neurons | Connections | Speed-up vs whole brain | Same verdicts | Held-out: active neurons kept (median) | Held-out: worst key-group error |
|---|---|---|---|---|---|---|
| `w1_1hop` | 8,688 | 0.20M | 10.4× | yes | 62–85% | **~100%** (E2, E3) |
| `w2_2hop` | 10,628 | 0.43M | 10.4× | yes | 69–83% | 43% (E3) |
| `w3_3hop` | 14,473 | 1.03M | 7.4× | **no**¹ | 68–85% | 46% (E3) |
| `a1_active` | 10,352 | 0.60M | 8.5× | yes | 96–100%, **but S3: 33–43%** | **163%** (S3) |
| `a2_active_inputs` | 21,243 | 2.23M | 5.6× | yes | 92–100% | 8% (S3) |
| `h1_hybrid` | 13,814 | 0.93M | 7.6× | yes | 84–100% | 6% (S3) |

¹ `w3_3hop` flips one D32 pick: the corrected half-of-maximum rate moves from 25 to 50 Hz, and S3 wasn't run at 50 Hz, so the corrected steering verdict can't be judged. That pick was on a knife edge in the whole brain (50.07% against a 50% bar), so this reflects a fragile threshold more than a broken circuit. It is still a difference.

**Share of whole-brain-active neurons that stay active, by experiment** (median across conditions; stimulated neurons excluded):

| Experiment | w1 | w2 | w3 | a1 | a2 | h1 |
|---|---|---|---|---|---|---|
| E1 (train) | 68% | 74% | 78% | 100% | 100% | 100% |
| S1 original (train) | 84% | 68% | 68% | 100% | 100% | 100% |
| E2 on/off | 62% | 78% | 85% | 100% | 100% | 100% |
| E3 LC4 subsets | 40% | 83% | 83% | 100% | 100% | 100% |
| E4 controls (LC10a, sugar) | 0% | 11% | 35% | 14% | 71% | 13% |
| E5b / E5c lesions | 72 / 67% | 74 / 76% | 83 / 81% | 96 / 96% | 97 / 100% | 97 / 96% |
| S1 corrected | 84% | 69% | 68% | 98% | 98% | 97% |
| S2 original / corrected | 85 / 85% | 78 / 79% | 79 / 81% | 100 / 100% | 100 / 100% | 100 / 100% |
| **S3 horizontal**, original / corrected | 74 / 84% | 70 / 71% | 71 / 78% | **43 / 33%** | 92 / 93% | 84 / 87% |

**Worst key-group error by experiment** (|subcircuit − whole| / whole, for groups firing > 5 Hz in the whole brain):

| Experiment | w1 | w2 | w3 | a1 | a2 | h1 |
|---|---|---|---|---|---|---|
| E1 (train) | 157% | 48% | 41% | 0% | 0% | 0% |
| E2 | 97% | 27% | 5% | 1% | 1% | 1% |
| E3 | 105% | 43% | 46% | 0% | 0% | 0% |
| E5b / E5c | 9 / 1% | 2 / 0% | 7 / 0% | 3 / 0% | 1 / 0% | 2 / 0% |
| S1 corrected | 11% | 11% | 11% | 3% | 2% | 4% |
| S2 original / corrected | 21 / 43% | 24 / 14% | 24 / 41% | 4 / 0% | 4 / 0% | 4 / 0% |
| S3 original / corrected | 20 / 14% | 17 / 14% | 11 / 9% | **100 / 163%** | 3 / 8% | 4 / 6% |

**Speed:**
- Measured with 4 trials running at once, the candidates run ~4.5–8× slower than real time.
- One 30 s practice level would take ~2.5–4 min, and a 90 s level ~7–12 min.
- Re-benchmark the chosen subcircuit on game-like input in J5 checkpoint 4.

## What the numbers say

1. **Wiring-only rules (w1–w3) are the smallest and fastest, but lose real activity.**
   - Even 3 steps upstream keeps only ~70–85% of the active neurons.
   - Key rates can be far off. For example, in `w1` the left Giant Fiber at 25 Hz input drops from 42 to 2 Hz, because its input route (DNp70, PVLP151; see `docs/pathway_results.md`) is partly cut.
   - Going from 2 to 3 steps adds ~4k neurons and 0.6M connections without clearly fixing this.
2. **Activity-only (a1) is exact for inputs like the ones it was built from, and fails on new kinds of input.**
   - It reproduces E1-like input perfectly (E2, E3, E5, S2: ~100%).
   - It misses most of what horizontal motion (S3) activates, so VS rates there are off by 100–163%.
   - In the game, the brain will only see the input types our encoding uses. An activity rule must therefore be built from activity that covers **every input the interface (T4) will use**.
3. **Adding wiring to activity fixes the gaps.**
   - `h1` (activity + 2-step wiring) and `a2` (activity + the active neurons' strong inputs) keep 84–100% of active neurons on everything held out, with key errors ≤ 8%.
   - `a2` is the most faithful, including on S3 and the controls, but it's the largest: 21k neurons, slightly above D18's ~20k, though within ~3M connections. It is also the slowest at 5.6×.
   - `h1` is ~35% smaller and faster, and only a bit worse on S3.
4. **No candidate covers the E4 controls well.**
   - LC10a and sugar input activate other parts of the brain.
   - That only matters if those controls are re-run on the subcircuit. They aren't game inputs. The Step 4 controls (shuffled connectome, silencing LC4/LPLC2 or the Giant Fiber) are separate and should be run on the whole brain or checked separately.
5. **One whole-brain event can't be reproduced by any candidate.**
   - In 2 of 640 whole-brain trials (corrected signs: S1 "up" 100 Hz trial 5, S2 trial 2), activity spread late (~640–785 ms) into ~8,000 extra central-brain neurons.
   - The second of these trials is inside the 3 compared here, so it lowers every candidate's numbers for that one condition.
   - Small subcircuits can't show such cascades. That's worth knowing when interpreting game runs.

## Questions for S5

- **Wiring, activity, or both?**
  - A wiring rule is easier to justify biologically and doesn't depend on our experiments, but it's clearly less faithful.
  - An activity rule is faithful but only for input types it has seen.
  - A combination has worked best here.
- **Which activity to build from?** These candidates were built from E1 + S1 only, to test generalisation. A final activity-based rule could use all the pathway tests, plus whatever input the interface will actually use (T4). If the ship encoding uses horizontal-motion neurons, their activity has to be in it.
- **How faithful is faithful enough?** For example: "same verdicts, key-group rates within 10%, ≥ 90% of active neurons kept on held-out tests". This needs a tolerance decided before the final validation, like D29–D31.
- **Size vs speed:** is ~14k neurons at ~7.6× (like `h1`) good enough, or is ~21k at ~5.6× (like `a2`) worth the extra fidelity?
