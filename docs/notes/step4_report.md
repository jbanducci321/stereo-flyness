# Step 4 report: controls and lesions on the cube

*Jacob and Shannyn, 2026-11-05. Analysis as fixed in D51 (with its amendment), all before any Step 4 result was read. **Skeleton written before the results were opened: every section marked "after opening" is empty on purpose.** Full tables: `results/step4/report.md` (git-ignored), made by `scripts/step4_report.py`.*

## Headline (after opening)
*To fill in. Lead with whether the play depends on the real wiring (a, d), then what (b) and (c) say about caveat 1.*

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

## Results (after opening)

### Every condition
*To fill in from `results/step4/report.md`:*
- progress and completions by difficulty;
- death classes;
- presses per second;
- first-spike θ;
- approaches with no Giant Fiber spike.

### The 12 comparisons (the Holm family)
*To fill in: better / worse / equal, p, Holm-adjusted p.*

### Readings fixed in D51
- **(a), (d): depends on the wiring?** *To fill in.*
- **(b), (c): the three relay bars** (progress, first-spike θ, (d1) share):
  - *To fill in.*
  - The bars use a 3-seed range, so they're strict: they make "relay" harder to claim, not easier.
  - If (b) or (c) does better than intact, that's the late-threshold effect (Step 3), not "a relay plays better".
- **E5b, E5c: specific to those neurons** (differs from intact and from its recruited-matched control, same direction)?
  - *To fill in.*
  - If E5c does better than intact, that's Step 3's late-threshold effect, not the lesion improving the fly.

### Against the predictions
*To fill in, one line each, hit or miss.*

### References (no brain)
- never press 6.3%;
- random presses 8.0%;
- always press: *to fill in*.

## What it means (after opening)
*To fill in. Keep interpretation labelled as interpretation. Points to cover whatever the results:*
- caveat 1, the relay;
- whole brain against subcircuit in closed loop (intact whole brain against the Step 2 subcircuit baseline, same levels and seeds; a first look for Step 7);
- "involved" is an approximation: neurons that fired in D46's 70 recruitment runs, not in the held-out games.

## Replays for the write-up (picked by rule: instance or draw 0, seed 0, the first held-out level alphabetically)
*To fill in after opening.*
