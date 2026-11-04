# Step 3 report: tuning R on the cube

*Jacob and Shannyn, 2026-11-04. Analysis as fixed in D49 before the grid. Held-out results opened together on 2026-11-04. Full tables: `results/step3/grid.md` and `results/step3/held_out.md` (git-ignored), made by `scripts/step3_report.py`.*

## Where the tuned fly sits against the real fly
**The tuned fly jumps outside the range measured in real flies.** The rule fixed in D49 picks R = 50 Hz. At that rate, on the calibration loom, the Giant Fiber first fires at **83.7 ± 22.0°** (10 of 10 trials fired), against the real fly's 39 ± 14° (25–53°). In closed loop on the training levels, its first spike (without carry-over) comes at 79.0°. Tuning R is in effect tuning the jump threshold, and the best threshold for these levels is about twice the real fly's.

## Setup
- **What's tuned:** R only, the peak rate of the driven LC4/LPLC2 neurons. Nothing else changes (D49).
- **Grid:** R ∈ {25, 50, 75, 100, 150, 200} Hz on all 50 cube training levels, seed 0.
  - 300 runs, all from clean commit `ccd900c`.
  - 0 stuck, 0 unclassified.
- **Score:** mean progress.
- **Tie margin:** measured from a second seed at 150 Hz (50 runs, commit `7115b8b`).

## The grid (training levels)

| R (Hz) | Mean progress | Completed (all easy) | Deaths (a) / (c) / (b) / (d1) / (d2) | Open-loop first-spike θ | Outside 25–53°? |
|---|---|---|---|---|---|
| 25 | 42.3% | 15/50 | 1 / 3 / 24 / 0 / 7 | 111.2° | yes |
| **50** | **49.6%** | **20/50** | 5 / 3 / 15 / 0 / 7 | **83.7°** | **yes** |
| 75 | 43.6% | 14/50 | 8 / 0 / 17 / 7 / 4 | 56.4° | yes |
| 100 | 28.4% | 5/50 | 7 / 0 / 9 / 24 / 5 | 50.1° | no |
| 150 (Step 2) | 22.7% | 1/50 | 6 / 0 / 11 / 31 / 1 | 38.0° | no |
| 200 | 17.2% | 0/50 | 6 / 0 / 9 / 35 / 0 | 33.2° | no |

- **Tie margin: 3.1 points.**
  - It's |22.7% − 25.8%|, seed 0 against seed 1 at 150 Hz.
  - 50 Hz leads 75 Hz by 6.0 points, so the tie-break isn't used.
- **No medium or hard training level is completed at any rate.**
- **Where the gain comes from:**
  - Lowering R removes the early jumps: (d1) deaths fall from 31 at 150 Hz to 0 at 50 Hz.
  - Below 50 Hz, more deaths come from objects a 39° jump can't clear either, (b): 24 at 25 Hz.
  - The peak is where those two cross.
- **Against the prediction** (recorded before the grid: "best R below 150, probably 75–100 Hz"):
  - Right that the best R is below 150 Hz.
  - Wrong about where: the best is 50 Hz. 100 Hz beats 150 Hz by 5.7 points but scores far below 75 and 50 Hz.
- **Carry-over and the spread:**
  - Carry-over falls with R: 22% of approaches at 150 Hz, 13% at 50 Hz, 4–5% at 75–100 Hz.
  - Without carry-over, the closed-loop first-spike θ stays within ~6° of the open-loop value at every rate (e.g. 37.5° against 38.0° at 150 Hz, 79.0° against 83.7° at 50 Hz).
  - So a lower R shifts the whole spread later, as the D49 framing predicted.

## The held-out check (fixed in D49 before the grid)
At R = 50 Hz against the Step 2 baseline (R = 150 Hz), both at seeds 0, 1 and 2 on the 20 held-out cube levels:
- 60 + 60 runs, all at clean commits (`61a9bf6` and `5d9de12`).
- Compared per level by each setting's median run.

| | Better | Worse | Equal | Sign test p | Reading |
|---|---|---|---|---|---|
| **R = 50 Hz against R = 150 Hz** | 11 | 4 | 5 | **0.118** | **no clear difference** |

- **By the test fixed beforehand, tuning R gives no clear difference on held-out levels.** With 15 levels that differ, p < 0.05 needed 12 or more better; we got 11.
- **Described beside it (no test fixed):**
  - The paired difference in median progress is **+23.5 points**.
  - The tuned fly completes **23 of 60 runs** against the baseline's 6, all on easy levels.
  - That's 23 of 24 easy runs, every seed 7–8 out of 20, and every easy level's median run completed.
  - The ideal 39° fly completes the same 8 easy levels (mean progress 59.2% over all 20, against the tuned fly's 52.8% and the baseline's 29%).
- **No sign of overfitting:** mean progress at 50 Hz is 49.6% on training and 52.8% on held-out.
- **The 4 worse levels:**
  - 2 hard levels die on objects a 39° jump can't clear either, (b), slightly earlier than the baseline.
  - 2 medium levels die on late jumps, (d2), where the baseline got further.

| Deaths over all 60 runs (described only) | (a) | (c) | (b) | (d1) | (d2) |
|---|---|---|---|---|---|
| R = 50 Hz (tuned) | 6 | 1 | 16 | 1 | **13** |
| R = 150 Hz (Step 2 baseline) | 5 | 0 | 14 | **33** | 2 |

- **Tuning trades early-jump deaths for late-jump deaths:** (d1) falls from 33 to 1, and (d2) rises from 2 to 13.
  - On easy levels the trade wins outright: every easy level's median run is completed.
  - On medium levels it's mixed: 5 better, 2 worse, 1 equal, nothing completed.
  - On hard levels it changes nothing that matters: the deaths are the encoding's limits, (a) and (b).

## What it means
- **The pick is outside biology.** The best R for these levels makes the fly jump at roughly twice the real fly's threshold. So this is a fact about the game and our encoding, not evidence that the fly plays better.
- **Part of the gain may make up for slabs not looming (D47).** A fly that jumps much later than it was calibrated to, and later than real flies, gets past things the encoding doesn't show it well. We don't present it as the fly getting better (D49).
- **The held-out test doesn't show a clear gain.**
  - "No clear difference" at p = 0.118 with 20 levels, not "no difference".
  - The direction is consistent (11 better against 4 worse; 23 against 6 completed), but a test fixed beforehand is what we report.
  - We don't add levels or seeds to push p below 0.05.
- **Interpretation (ours, not a tested result):** the grid supports the Step 2 reading that these levels punish early jumps far more than late ones. The penalty only turns at about twice the real fly's threshold, which is where late jumps start to die on medium levels.
- **Nothing here touched Stereo Madness (D7).**

## Still to decide (together, before Stereo Madness)
Which R goes forward to Stereo Madness and the later steps isn't fixed by D49. Jacob's proposal is in `docs/decisions.md`, "Open".
