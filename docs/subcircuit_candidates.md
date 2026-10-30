# Subcircuit candidates (J5, input for S5)

*Jacob, J5 checkpoint 3, 2026-10-28. These are options measured for Shannyn's subcircuit rule (S5). None of them is the rule itself.*

> **Outcome:** S5 is decided in **D36**: an a2-style rule (recruited neurons plus their ≥ 30-synapse inputs), built from game inputs on both sides and both sign versions, with a tolerance agreed in advance. An interim version is built in J5 for T3; the final version follows T4.

## Why a subcircuit, and what this measures

- **The problem:** the whole brain runs ~16–26× slower than real time (FEASIBILITY, Benchmarks), far too slow for tuning on hundreds of level runs.
- **The fix:** a subcircuit keeps only the neurons that matter and every connection between them, with weights unchanged (D5). D18 set the target at up to ~20k neurons / ~3M connections.
- **What a subcircuit gives up:** inputs from the neurons it drops.
- **What we measured:** six candidate rules, each run through the pathway tests (same seeds as the whole brain, 3 trials per condition) and compared with the whole brain on:
  - the go/no-go verdicts (D29–D31);
  - the key neurons' rates (Giant Fibers, VS, DNp20/22, LPi09);
  - **every neuron's activity** (D34): the share of whole-brain-active neurons that stay active, and the per-neuron rate correlation.
- **A fair(er) test:** activity-based rules were built only from **E1 and S1 (original signs)**. Everything else (E2–E5, S2, S3, corrected signs) is **held out**.
  - **Limit (Shannyn's review):** most held-out conditions (E2, E3, E5, S2) stimulate the same neurons as the training ones, in different combinations or timings. **Horizontal motion (S3) is the only genuinely new input**, and everything here stimulated the right side only. So this compares candidates fairly, but the final validation needs game-like input (D36).

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

1. **Wiring-only rules (w1–w3) are the smallest and fastest, but lose real activity.** (Caveat: w1–w3 change both the number of steps and the synapse cut-off, so the step comparison is confounded.)
   - Even 3 steps upstream keeps only ~70–85% of the active neurons.
   - Key rates can be far off. For example, in `w1` the left Giant Fiber at 25 Hz input drops from 42 to 2 Hz, because its input route (DNp70, PVLP151; see `docs/pathway_results.md`) is partly cut.
   - Going from 2 to 3 steps adds ~4k neurons and 0.6M connections without clearly fixing this.
2. **Activity-only (a1) is exact for inputs like the ones it was built from, and fails on new kinds of input.**
   - It reproduces E1-like input perfectly (E2, E3, E5, S2: ~100%).
   - It misses most of what horizontal motion (S3) activates, and the VS cells **over-fire** (e.g. 15 → 39 Hz at 25 Hz, corrected; 65 → 83 Hz at 50 Hz, original). It is missing recruited inhibition, and not via LPi09, which is silent during horizontal motion.
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

## Interim size (J5 checkpoint 4, 2026-10-29): D36 as written doesn't fit the limit

D36's recipe was applied to all 1,210 whole-brain game-input trials: E1–E3, E5b/c and S1–S3, on the right side, left side and both sides, with both sign versions. Probes were excluded.

**Recruited neurons alone exceed the ~25k limit**, so raising the synapse cut-off (D36's size fallback) can't make the recipe fit:

| Recruited from | Recruited | + inputs ≥ 30 syn | ≥ 50 | ≥ 75 | ≥ 100 |
|---|---|---|---|---|---|
| All trials (D36 as written) | 27,960 | 42.4k / 4.50M | 33.8k / 3.29M | 30.9k / 2.78M | 29.7k / 2.57M |
| Without the 3 runaway-cascade trials | 20,609 | 33.5k / 3.39M | 26.3k / 2.37M | 23.6k / 1.92M | 22.5k / 1.73M |

- **Where the extra neurons come from:** about 7,400 of the recruited neurons fire only in the 3 cascade trials (out of 1,350), where activity spreads late into ~8,000–11,000 neurons.
- **The two cascade-free columns aren't D36:** excluding trials is a rule change that needs agreement.
- **D36 says what to do when nothing fits:** "raise the limit (and log it) or rethink the rule".

**Speed on game-length input** (`scripts/benchmark_subcircuit.py`):
- The stand-in level is 15 s "cube" (an expanding looming burst on both sides every 1.25 s) plus 15 s "ship" (horizontal motion with up/down switching every 150 ms).
- These are **measurement builds**, not validated subcircuits: `configs/subcircuits/d36/`.

| Network | Size | 1 run alone | 4 runs at once (each) | One 30 s level (4 at once) | 200-run tuning grid (4 at once) |
|---|---|---|---|---|---|
| Whole brain | 139k / 15.1M | 24.3× real time | (not measured) | ~12 min alone | ~20 h+ |
| D36 as written, ≥ 30 syn (`d36_literal_30`) | 42.4k / 4.50M | 10.0× | 20.5× | ~10 min | **~8.5 h** |
| Cascades excluded, ≥ 75 syn (`d36_nocascade_75`) | 23.6k / 1.92M | 6.9× | 13.8× | ~7 min | **~5.8 h** |
| Cascades excluded, ≥ 30 syn (`d36_nocascade_30`, D37 proposed; measured 2026-10-30) | 33.5k / 3.39M | 8.9× | 17.2× | ~8.6 min | **~7.2 h** |

- **Game-like input is much busier than the pathway tests.** With both sides driven and thousands of T4/T5 neurons stimulated, the speed-up over the whole brain is ~2.4–3.5×, not the ~8× of the right-side tests in checkpoint 3.
- **Both builds allow an overnight tuning grid.** The difference between them is ~1.5× in speed.
- **Fidelity cost of `d36_nocascade_75`:** its 75-synapse cut-off keeps only ~74% of the Giant Fibers' input synapses (62–67% of their inhibitory input), against 87–89% for `d36_literal_30`. It may fail the D36 tolerance; that isn't checked yet.

**Decision needed before the interim build:** see the options in the summary for Shannyn. Neither build has been validated, and the probes haven't been run on any subcircuit.

**Update (2026-10-29):** Shannyn proposed a third option, logged as **D37 (proposed)** in `docs/decisions.md`:
- Leave out cascade trials using a fixed test: more than 3× the median active count of the condition's other trials.
- Keep D36's ≥ 30-synapse cut-off: 33.5k / 3.39M, the cascade-free ≥ 30 column above.
- Replace the neuron limit with a tuning-time limit: a 200-run grid on 30 s levels in ≤ 10 h, 4 at once.

It is pending a speed benchmark of that build and confirmation of the practice-level length.

**Checks for D37 (2026-10-30, measurement only; nothing validated):**
- **Build `d36_nocascade_30`:**
  - 33,480 neurons, 3,391,290 connections, with 0 pathway-test neurons missing.
  - The Giant Fibers keep 87–88% of their input (82% of their inhibitory input), the same as `d36_literal_30`.
- **Speed (on Jacob's laptop):**
  - 8.9× real time alone, 17.2× each with 4 at once.
  - A 200-run grid on 30 s levels takes **~7.2 h**, under the proposed 10 h.
  - On 90 s levels it would take ~21.5 h.
- **The 3× cascade test, applied to all 1,350 whole-brain trials, flags only 2 of the 3 known cascades:**

  | Trial | Active neurons | Median of the condition's other trials | Ratio | Flagged by 3×? |
  |---|---|---|---|---|
  | corrected S1 up_R 100 Hz, trial 5 | 11,143 | 3,008 | 3.7× | Yes |
  | original S1 up_L 200 Hz, trial 3 | 11,401 | 3,416 | 3.3× | Yes |
  | corrected S2 down 25 + up 150 Hz, trial 2 | 12,808 | 4,845 | **2.6×** | **No** |

  - It misses the third because that condition is already busy without a cascade.
  - The highest ratio among the other 1,347 trials is 1.6× (a small E3 subset, 42 vs 26 neurons).
  - So a threshold anywhere between ~1.7× and ~2.6× would separate the cascades cleanly. Choosing the threshold is Shannyn's call.
  - This build excludes all 3 trials by hand.

## Held-out probes P5–P7 (2026-10-30, whole brain only)

These were added after Shannyn's probe review, alongside P1–P4. They are defined in `configs/pathway_tests.toml` under `[probes]`, and **never used to build a subcircuit** (D36). Each runs 5 trials on the right side, the left side and both sides. P6 also runs on both sign versions. That makes 60 trials, and no trial produced activity with no input.

**The probes:**
- **P5, spatial looming:** an LC4 + LPLC2 patch that grows from 19 neurons per side to all of them, in 8 steps of 40 ms at 150 Hz.
  - There are no visual-field positions, so "nearby" means sharing input partners (cosine similarity of input synapse counts).
  - LC4 and LPLC2 share almost no inputs: their median similarity to each other is 0.03, against 0.2–0.4 within each type. So each type grows its own patch. LPLC2's patch starts from the LPLC2 neuron most similar to LC4's starting neuron.
- **P6, looming over scrolling:** P1's looming plus constant front-to-back motion (T4a + T5a at 50 Hz). It watches both the escape and steering groups.
- **P7, close obstacles:** all of a side's LC4 + LPLC2 at 150 Hz, 100 ms on / 50 ms off, 4 times.

**Whole-brain results** (Hz, mean ± SD over 5 trials, original signs; corrected is the same within ~2 Hz except where noted):

| Probe | Right GF | Left GF | Steering groups |
|---|---|---|---|
| P5 right / left / both | 70.9 / 54.1 / 78.7 | 45.8 / 69.0 / 75.5 | (not watched) |
| P7 right / left / both | 131.6 / 82.0 / 138.2 | 71.8 / 122.0 / 124.0 | (not watched) |
| P6 right | 91.7 (P1 alone: 93.7) | 51.2 (P1: 52.0) | VS_R 82, DNp20_R 95, DNp22 and LPi09 silent |
| P6 left | 57.3 (P1: 59.3) | 81.2 (P1: 80.8) | VS_L 42 (corrected 61) |
| P6 both | 97.8 (P1: 98.6) | 85.1 (P1: 88.1) | VS_R 82, VS_L 42 (corrected 61), DNp20_R 96 |

- **Front-to-back motion barely changes the escape response:** the Giant Fiber rates in P6 are within ~3 Hz of P1's.
- **VS cells fire at ~82 Hz in P6.** That's more than S3's 65 Hz at 50 Hz, which drove all four horizontal types (T4a/b, T5a/b). Front-to-back alone drives VS harder than both directions together.
- **No cascades:** the 3× test, applied to all 1,410 whole-brain trials, still flags only the 2 known S1 trials.
