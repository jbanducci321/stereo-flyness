# Step 3: tuning R on the cube (proposal)

*Jacob, 2026-11-02. Draft for discussion with Shannyn. Nothing here is decided until it's logged in `docs/decisions.md`. Written before any Step 2 result, and before any fly-driven run at an R other than 150 Hz.*

Step 3 tunes the cube's one dial and checks whether the tuned value carries over to levels it wasn't tuned on (PROJECT_BRIEF §8). Like every step so far, the rules are fixed before the runs: which values are tried, on which levels, how the winner is picked, and what is reported. Nothing else changes: the encoding (D41, D45, D47), θ_full = 200° (D43: "if R is tuned, θ_full stays"), the output rule (D42), the network (the final subcircuit, D46).

## 1. What R does, and what tuning it means

- **R** is the peak per-neuron rate of the driven LC4/LPLC2 neurons, reached near contact (D45). The range is **25–200 Hz** (D43); rule 5 passed at 25, 150 and 200 (D46), so the whole range runs on the subcircuit.
- θ_full was calibrated at R = 150, so that the Giant Fiber first fires at ~39°, the fly's threshold. **Changing R moves that point:** a lower R should make it fire later (at a larger θ) or not at all, and a higher R earlier. So tuning R is, in effect, tuning the fly's jump threshold away from the calibrated one.
- That is allowed (R is the agreed dial), but it has to be said plainly in the write-up, and it is why the biological check in §2 matters.
- **Already known (D46, bot-driven):** at R = 25 the subcircuit didn't press at all on 92 of 325 approaches, against 38 at R = 150. So at the low end the fly misses obstacles, not only jumps late.

## 2. Before the grid: where each R fires (open loop, no game)

- Run the official calibration loom (start gap 245, R × f, θ_full = 200°, 10 trials) at **each R in the grid**, on the final subcircuit (it reproduces the whole brain's calibration frame for frame, D46).
- Report the first Giant Fiber spike θ (mean ± s.d.) and how many trials fire, per R. Tooling exists: `calibrate_theta_full.py --network final --rate-scaling --grid 200 --rate <R> --trials 10`.
- This tells us, **before any performance is seen**, how far each R moves the fly from 39° ± 14°. About 10 minutes in all.
- **Question 1 (Shannyn):** should this restrict the range? My suggestion: no restriction, but any R whose first-spike θ falls outside the fly's 1 s.d. band (25–53°) is flagged in advance, and if it wins, the write-up says "the tuned fly jumps outside the range measured in real flies". The alternative is to drop those R values from the grid now.

## 3. The grid

- **R values (6):** **25, 50, 75, 100, 150, 200 Hz.** That covers the agreed range, includes the Step 2 default (150), and reuses the recruitment values (25, 50, 100, 150, 200) plus 75 to fill the biggest gap at the low end, where we expect the most change.
- **Levels: all 50 cube training levels** (easy 20, medium 20, hard 10). No subset to choose, and medium and hard are where the fly currently dies. They include the 10 recruitment and 5 rule 5 levels; that's fine, they're training levels, and those runs were bot-driven.
- **Runs:** fly-driven closed loop, baseline encoding (collision course, R × f, θ_full = 200°), **seed 0**, one run per level × R: **300 runs**.
- **Time:** at most ~8 h with 4 at once (5.4 h per 200 full-length runs, D46). Fly-driven runs end when the cube dies, so it should be well under that. Inside D37's 10 h limit.
- Every frame is logged and labelled fly-driven (hard rule 10). ~0.2–0.4 MB per run, so ~100 MB on disk.
- **Stuck runs** are kept and counted as they ended, and the stuck count per R is reported (D38).
- **Not tuned:** the two Step 2 comparisons (flat R, every object looms). They stay comparisons; Step 3 tunes the baseline only.

## 4. How the winner is picked

- **Score: mean progress over the 50 levels** (the share of each level reached, averaged).
  - Why not levels completed: even the ideal 39° fly completes only 21/50, nearly all easy (1/20 medium, 0/10 hard; D47). A count of completions would be decided by the easy levels alone, and would treat 10% and 90% on a hard level the same.
  - Levels completed, by difficulty, are reported beside it.
- **Ties:** any R within **1 percentage point** of the best mean progress counts as tied, and among tied values the one **closest to 150 Hz** (on a log scale) wins, i.e. the one that moves the fly least from its calibrated state.
- **If the winner is 150:** tuning didn't help. That's the Step 3 result; the held-out run would repeat Step 2, so it isn't run again.
- **If the winner is at an edge (25 or 200):** it's reported as at the edge. The range isn't widened (D43).
- **No second, finer grid.** It would be a choice made after seeing the first one. If we want one, we agree it now (Question 2).

## 5. The held-out check (the Step 3 result)

- **Run once,** at the chosen R, on the **20 held-out cube levels**, seed 0, baseline encoding, final subcircuit.
- **Reported next to the Step 2 baseline** (same levels, same seed, R = 150) and the ideal fly, in the Step 2 report format: per level progress and death class, totals by difficulty, mean progress.
- **The comparison:** the paired difference in mean progress, tuned minus untuned, and how many of the 20 levels got better, worse or stayed the same. No pass/fail bar: it's a measurement of whether the tuning carries over, and both outcomes are results.
- **Also reported:** the tuned R's training score next to its held-out score, so any overfitting to the training levels is visible.
- Stereo Madness isn't touched (D7).

## 6. Prediction, recorded before the runs

The ideal fly does best with a later threshold (45–50° complete 22/50; 20–35° complete none; D47), and on training levels the fly-driven cube mostly presses early (θ ≈ 20–37° before landing-onto deaths; a check, not interpreted). **So we expect the best R to be below 150,** where the Giant Fiber fires later. If R = 25 misses too many obstacles (§1), the best may be in the middle (50–100). This is a prediction to check against, not a rule.

## 7. Open questions for Shannyn

1. Should the open-loop first-spike θ (§2) restrict the R range, or only flag values outside the fly's band? (Suggestion: flag only.)
2. One grid, or a pre-agreed finer second grid around the winner (e.g. its two neighbours' midpoints, 100 more runs)? (Suggestion: one grid.)
3. One seed, or extra seeds? With one seed, a single level's outcome can flip on a small timing shift (D44). Options: two seeds on the training grid (600 runs, two nights), or extra held-out seeds for both the tuned and the Step 2 runs (e.g. seeds 1–2, 80 runs, ~2 h) to show how much of the held-out difference is noise. (Suggestion: one seed for the grid, extra held-out seeds for both.)
4. Is the 1-point tie margin reasonable, and is "closest to 150" the right tie-break (rather than "closest to calibrated 39°" from §2, which should give the same order)?

### Shannyn's answers (2026-11-02), to go into Step 3's decision entry

1. **Flag only**, agreed. Also report the **share of calibration trials that fire** at each R, and put the winner's open-loop first-spike θ in the **headline result**, not only in a flag.
2. **One grid**, agreed.
3. **Seeds:** one seed on the grid; **seeds 0–2 on the held-out levels** for both tuned and untuned (matching Step 2, D48). **The tie margin is measured, not guessed:** run R = 150 at seed 1 on the 50 training levels before the grid (50 runs, ~1.5 h); **tie margin = max(1 point, the seed 0 vs seed 1 difference in mean progress at R = 150).**
4. **Tie-break, reworded:** the tied R whose **open-loop first-spike θ is closest to 39°** (the actual reason; the same order as "closest to 150" if θ rises steadily as R drops, and flagged if it doesn't).
   - **An R where fewer than half the calibration trials fire ranks last.** If more than one does, they're ranked by how many trials fire (more is better). Their mean θ from the trials that fired still goes in the report, labelled "n of 10 fired".

Three additions:
- **Death classes per R on the grid** (D48's classes). R can only change (b), (c) and (d) deaths, never (a), so this shows where any gain comes from.
- **The held-out check uses Step 2's rule for "better"** (paired sign test, p < 0.05), next to the paired difference.
- **Framing for the write-up:** if the best R is below 150, the fly is jumping later than real flies do, and partly that would make up for the encoding not making slabs loom (D47). Say so, rather than present it as the fly getting better.

## 8. Code (written, not run)

- `configs/step3.toml` holds the settings above; changing an answer to §7 is an edit there.
- `scripts/step3_grid.py check` runs §2, and `scripts/step3_grid.py grid` runs §3. Both call the existing scripts once per R, into their own `_step3` folders, so the D46 records at R = 150 aren't overwritten.
- `scripts/step3_report.py` scores the grid by §4 (`stereo_flyness.experiments.tuning.pick_rate`, tested), and picks nothing until every R has all 50 levels.
- The held-out run reuses `play_cube.py --suite held_out` and `step2_report.py` with the tuned setting added as a column (not written yet).
