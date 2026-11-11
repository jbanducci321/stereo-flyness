# Step 4 report: controls and lesions on the cube

*Jacob and Shannyn, 2026-11-05. Analysis as fixed in D51 (with its amendment), all before any Step 4 result was read. The skeleton was written before the results were opened. **Opened 2026-11-10:** at Jacob and Shannyn's request, Jacob's Claude Code session read the report and judged every fixed question against D51's rules; Jacob and Shannyn review the verdicts (this replaces the two independent reads planned in `opening_verdicts.md`). Full tables: `results/step4/report.md` (git-ignored), made by `scripts/step4_report.py`.*

## Headline

- **The play depends on the real wiring.** Both the degree-preserving shuffle (a) and the random network (d) are worse than intact (0 better, 18 worse, 2 equal; p < 0.001, both survive Holm): their Giant Fiber never fires, so they play exactly like never press (6.3%).
- **But a relay alone plays the cube *further* than the intact fly, by firing later.** The looming-kept shuffle (b) and the relay-only network (c) give identical results: 59.4% progress against 29.4%, 24 of 24 easy runs completed against 6. That's better at p = 0.013 on its own, but **not after Holm** (p = 0.129). By D51's bars they are **not** a relay of the intact fly: all three bars fail, since they fire ~10° later (46.5° against 36.6°) and almost never die early. As fixed in D51, playing better is read as the late-threshold effect (Step 3), not as "a relay plays better".
- **What the rest of the wiring does, then, is mostly make the Giant Fiber fire earlier,** close to the real fly's 39°, which at 150 Hz happens to cost progress.
- **Neither lesion is specific:** E5b and E5c show no clear difference against intact or against their recruited-matched controls, although E5c moves the first spike hugely later (100° against 37°).

## Setup
- **The question:** does the fly's play depend on the real wiring? Caveat 1: 293 direct LC4/LPLC2 → Giant Fiber connections carry 19.9% of the Giant Fibers' input, so the fly could be little more than a relay plus a threshold.
- **Network and settings:** whole brain (D36), R = 150 Hz (D50), R × f, θ_full = 200°, collision course: the Step 2 baseline's encoding, unchanged for every network and lesion. Original signs only. No recalibration for any control.
- **Levels and seeds:** the 20 held-out cube levels at seeds 0, 1 and 2, so 60 runs per condition. Instance or draw *k* plays at Poisson seed *k*.
- **Reference:** the intact whole brain on the same levels and seeds.
- **Control networks** (each built from a fixed seed, all checks passing; `scripts/make_control_connectivity.py`):
  - **(a)** degree-preserving shuffle ×3;
  - **(b)** shuffle keeping the 293 looming → Giant Fiber connections ×3, with no new ones allowed;
  - **(c)** relay-only: those 293 connections and nothing else;
  - **(d)** random network ×3.
- **Lesions** (whole cell types, both sides, D5):
  - **E5b**, the Giant Fiber's inhibitory partners: 22 neurons;
  - **E5c**, its excitatory partners: 12 neurons;
  - **two controls for each, 3 draws:** a random lesion (same sign, output within ±10%), and a recruited-matched control (the same, plus the same recruitment status, so it silences as many involved neurons as the lesion: 13 of 22 and 10 of 12).
- **Not run, and why:**
  - **Giant Fiber silenced.** Shiu's `silence()` leaves it spiking and our output reads its spikes, so it would only test our output rule. In real flies, Giant Fiber–silenced flies still escape through the long-mode pathway (von Reyn et al. 2014), which our output can't see.
  - **LC4 only / LPLC2 only.** With both types calibrated together, it would act like lowering R (Step 3), and it wouldn't test the von Reyn 2017 split.

## Checks (all passed before any result was read)
- **The LC4/LPLC2 code check:** 0 Giant Fiber spikes and 0 presses on 2 held-out levels, as required.
- **Runs:**
  - all 11 conditions complete, 660 runs;
  - every run replayed exactly from its logged presses;
  - clean commits: `91989c6` for night 1 and `b8228a6` for night 2. The only change between them is the amendment's new control, which night 1 doesn't use.
- **Control files:** every connectivity file still matches the SHA-256 its runs recorded.
- **0 stuck runs, 0 unclassified deaths.**
- **The laptop slept twice during night 2.** That froze the runs; it didn't change them, since each run depends only on its seed and game ticks.

## Open-loop check (calibration loom, 10 trials; recorded before the runs, described only)

| Condition | First Giant Fiber spike θ | Fired |
|---|---|---|
| Intact whole brain | 38.0 ± 6.3° | 10/10 |
| E5b (inhibitory partners silenced) | 35.0 ± 3.6° | 10/10 |
| E5c (excitatory partners silenced) | 106.7 ± 20.3° | 10/10 |
| Random lesions, all 6 draws | 38.0 ± 6.3° (identical to intact) | 10/10 |
| E5b recruited-matched, all 3 draws | 38.0 ± 6.3° (identical to intact) | 10/10 |
| E5c recruited-matched | draw 0: 48.5 ± 5.6°; draws 1–2: 38.0 ± 6.3° (identical to intact) | 10/10 |
| (b) looming-kept ×3 and (c) relay-only | 46.6 ± 4.0° (all four identical) | 10/10 |
| (a) shuffle ×3 and (d) random network ×3 | never fired | 0/10 |

- **Identical results** mean the silenced or shuffled neurons take no part in the Giant Fiber's response to a loom, so with fixed trial seeds the spikes come out the same.
- **On balance, open loop, the rest of the wiring makes the Giant Fiber fire *earlier*:**
  - with only the direct connections it fires at 46.6°, about 9° later than intact;
  - without its excitatory partners (E5c) it fires very late.

## Predictions (written before any run; D51)
- **(a) and (d):** worse than intact, playing like never press (or like always press if they run away).
- **(b)** (Shannyn): earlier jumps, more (d1), progress the same or lower.
  - **Dated note, before night 2:** the open-loop check points the other way (46.6° against 38.0°). The prediction stays as recorded.
- **(c):** no confident prediction.
- **E5b** (Shannyn): earlier first spike (below ~37°), more (d1), lower progress.
- **E5c** (Shannyn): later first spike, fewer (d1), more (d2), progress the same or higher.
- **Random and recruited-matched controls:** no clear difference from intact.

## Results

### Every condition

| Condition | Mean progress | Completed easy / medium / hard | Deaths (a) / (c) / (b) / (d1) / (d2) / (d3) | Presses per s | First-spike θ, median (all / no carry-over) | Approaches with no GF spike |
|---|---|---|---|---|---|---|
| Intact whole brain | 29.4% | 6/24 / 0/24 / 0/12 | 5 / 0 / 14 / 33 / 2 / 0 | 2.59 | 36.3° / 36.6° | 305 of 761 |
| E5b (inhibitory partners) | 26.3% | 4/24 / 0/24 / 0/12 | 6 / 0 / 11 / 39 / 0 / 0 | 4.55 | 35.4° / 35.8° | 301 of 729 |
| E5c (excitatory partners) | 47.4% | 21/24 / 0/24 / 0/12 | 1 / 2 / 18 / 3 / 15 / 0 | 2.78 | 99.1° / 100.2° | 564 of 1,221 |
| E5b random lesion | 29.4% | 6/24 / 0/24 / 0/12 | 5 / 0 / 15 / 33 / 1 / 0 | 2.52 | 36.3° / 36.6° | 309 of 767 |
| E5c random lesion | 29.4% | 6/24 / 0/24 / 0/12 | 5 / 0 / 13 / 33 / 3 / 0 | 2.61 | 36.3° / 36.6° | 308 of 767 |
| E5b recruited-matched | 29.5% | 6/24 / 0/24 / 0/12 | 5 / 1 / 14 / 33 / 1 / 0 | 2.64 | 36.4° / 36.6° | 314 of 776 |
| E5c recruited-matched | 36.4% | 10/24 / 0/24 / 0/12 | 6 / 0 / 13 / 24 / 7 / 0 | 2.71 | 39.5° / 40.5° | 358 of 929 |
| (a) shuffle | 6.3% | 0/24 / 0/24 / 0/12 | 0 / 0 / 30 / 0 / 0 / 30 | 0.00 | never fired | 84 of 84 |
| (b) looming-kept shuffle | 59.4% | 24/24 / 0/24 / 0/12 | 12 / 2 / 21 / 0 / 1 / 0 | 2.83 | 46.5° / 46.5° | 799 of 1,684 |
| (c) relay-only | 59.4% | 24/24 / 0/24 / 0/12 | 12 / 2 / 21 / 0 / 1 / 0 | 2.83 | 46.5° / 46.5° | 799 of 1,684 |
| (d) random network | 6.3% | 0/24 / 0/24 / 0/12 | 0 / 0 / 30 / 0 / 0 / 30 | 0.00 | never fired | 84 of 84 |

0 stuck (s) and 0 unclassified (u) deaths in every condition.

- **(b) and (c) are identical,** although their connectivity files differ (checked: `Connectivity_783_loomkept_s*` against `Connectivity_783_relay`, different SHA-256). In (b), the shuffled rest of the brain stays silent (about 1 neuron firing per tick besides the inputs, as in (c)), so only the 293 direct connections act; the Giant Fiber spikes match tick for tick in 18 of the 20 pairs checked.

### The 12 comparisons (the Holm family)

| Comparison | Better | Worse | Equal | p | Reading | Holm p | Survives |
|---|---|---|---|---|---|---|---|
| E5b vs intact | 1 | 5 | 14 | 0.219 | no clear difference | 1.000 | no |
| E5c vs intact | 10 | 6 | 4 | 0.454 | no clear difference | 1.000 | no |
| E5b random lesion vs intact | 0 | 0 | 20 | 1.000 | no clear difference | 1.000 | no |
| E5c random lesion vs intact | 0 | 0 | 20 | 1.000 | no clear difference | 1.000 | no |
| E5b recruited-matched vs intact | 1 | 0 | 19 | 1.000 | no clear difference | 1.000 | no |
| E5c recruited-matched vs intact | 5 | 2 | 13 | 0.453 | no clear difference | 1.000 | no |
| **(a) shuffle vs intact** | 0 | 18 | 2 | < 0.001 | **worse** | < 0.001 | **yes** |
| (b) looming-kept vs intact | 12 | 2 | 6 | 0.013 | better | 0.129 | no |
| (c) relay-only vs intact | 12 | 2 | 6 | 0.013 | better | 0.129 | no |
| **(d) random network vs intact** | 0 | 18 | 2 | < 0.001 | **worse** | < 0.001 | **yes** |
| E5b vs its recruited-matched control | 1 | 5 | 14 | 0.219 | no clear difference | 1.000 | no |
| E5c vs its recruited-matched control | 8 | 6 | 6 | 0.791 | no clear difference | 1.000 | no |

### Readings fixed in D51
- **(a), (d): depends on the wiring?** **Yes, both** (worse than intact, p < 0.001, surviving Holm).
- **(b), (c): the three relay bars** (progress, first-spike θ, (d1) share):
  - **all three fail for both:** progress differs (better); first-spike θ differs by 9.8° against a seed range of 2.5°; the (d1) share differs by 61 points against a seed range of 9. **So neither is "a relay" of the intact fly by D51's rule: they play further, and not the same way.**
  - The bars use a 3-seed range, so they're strict: they make "relay" harder to claim, not easier.
  - If (b) or (c) does better than intact, that's the late-threshold effect (Step 3), not "a relay plays better".
- **E5b, E5c: specific to those neurons** (differs from intact and from its recruited-matched control, same direction)?
  - **No for both:** no clear difference against intact, nor against the recruited-matched control.
  - If E5c does better than intact, that's Step 3's late-threshold effect, not the lesion improving the fly.

### Against the predictions

- **(a), (d) (Jacob): hit.** Worse than intact, playing exactly like never press (the Giant Fiber never fires).
- **(b) (Shannyn): miss on all three.** It jumped later, not earlier (46.5° against 36.6°), had no (d1) deaths against 33, and went further, not the same or lower. The dated open-loop note before night 2 pointed this way.
- **(c): no prediction.** Identical to (b).
- **E5b (Shannyn): the direction holds, but not significantly.** Slightly earlier first spike (35.8° against 36.6°), more (d1) (39 against 33), lower progress (26.3% against 29.4%); the sign test shows no clear difference (1 better, 5 worse, p = 0.22).
- **E5c (Shannyn): hit on all four.** Much later first spike (100.2°), fewer (d1) (3 against 33), more (d2) (15 against 2), higher progress (47.4%; not a clear difference by the sign test, p = 0.45). As fixed, the higher progress is the late-threshold effect.
- **Random and recruited-matched controls: hit.** No clear difference; the random lesions equal intact on all 20 levels.

### References (no brain)
- never press 6.3%;
- random presses 8.0%;
- always press 13.0%.

## What it means (interpretation, labelled as such)

- **Caveat 1, the relay.** The direct looming → Giant Fiber connections alone are enough to make the cube jump at all, and to fly the easy levels. What the rest of the real wiring adds is *when*: it brings the first spike ~10° earlier, to 36.6°, close to the real fly's 39 ± 14°. At R = 150 Hz, firing late plays better on these levels (Step 3's late-threshold effect), so the relay "wins" on progress while being further from the real fly's timing. The honest summary: **the fly's play depends on the wiring, and the wiring's main measurable effect in this game is earlier escape timing, which the game happens not to reward.**
- **The rest of the brain is nearly silent in these games.** In the relay networks only ~1 neuron per tick fires besides the inputs; in the intact brain, the same 154 neurons fire in a Step 7 pair checked tick by tick, all inside the subcircuit. So the intact brain's extra contribution comes through a small set of neurons, which fits single cell-type lesions moving the timing (E5c a lot, E5b a little) without a clear effect on progress.
- **Whole brain against subcircuit:** the intact whole brain's numbers here are identical to the Step 2 subcircuit baseline; Step 7 confirms the games are identical tick for tick (D52, 60 of 60 pairs).
- **"Involved" is an approximation:** neurons that fired in D46's 70 recruitment runs, not in the held-out games.

## Replays for the write-up (picked by rule: instance or draw 0, seed 0, the first held-out level alphabetically)

Rendered before the opening and unwatched until now: `results/step4/replays/` (git-ignored), one per condition (`intact`, `E5b`, `E5c`, their random-lesion and recruited-matched controls, `a_shuffle`, `b_looming_kept`, `c_relay_only`, `d_random_network`, as `.mp4`). Which go in the write-up is chosen after watching, by both.
