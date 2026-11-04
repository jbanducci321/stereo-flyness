# D49 draft: Step 3, tuning R on the cube

*Logged as D49 in `docs/decisions.md` on 2026-11-03; the log is the canonical version, this is the draft history.*

*Jacob, 2026-11-03. Draft for Shannyn. Goes into `docs/decisions.md` as D49 once she agrees, after Step 2 is done (D48). Built from `docs/notes/step3_proposal.md` and her answers of 2026-11-02. Written before the grid; no grid run exists yet.*

**D49. Step 3: tuning R on the cube, fixed before the grid** (date logged)
- **What's tuned:** R only, the peak per-neuron rate of the driven LC4/LPLC2 neurons (D45), within D43's range of 25–200 Hz. Nothing else changes: the encoding (D41, D45, D47), θ_full = 200° (D43), the output rule (D42), the final subcircuit (D46).
- **Plainly:** θ_full was calibrated at R = 150 so that the Giant Fiber first fires at ~39°. Changing R moves that point, so tuning R is in effect tuning the fly's jump threshold away from the calibrated one. The write-up says so.
- **Open-loop check, recorded before the grid** (calibration loom, start gap 245, R × f, θ_full = 200°, 10 trials, final subcircuit; `results/calibration/final/gap245_R*_scaled_step3/`):

  | R (Hz) | First Giant Fiber spike θ, mean ± s.d. | Trials fired | Outside the fly's 25–53°? |
  |---|---|---|---|
  | 25 | 111.2 ± 28.3° | 10/10 | **yes** |
  | 50 | 83.7 ± 22.0° | 10/10 | **yes** |
  | 75 | 56.4 ± 11.9° | 10/10 | **yes** |
  | 100 | 50.1 ± 10.1° | 10/10 | no |
  | 150 | 38.0 ± 6.3° | 10/10 | no |
  | 200 | 33.2 ± 5.1° | 10/10 | no |

  - θ rises steadily as R drops, so "closest to 39°" gives the same order as "closest to 150 Hz on a log scale": 150, 200, 100, 75, 50, 25.
  - Every R fires in all 10 trials, so the "fewer than half fire" rule doesn't come into play.
  - **Flag only, no restriction** (Shannyn): 25, 50 and 75 Hz are outside the fly's 1 s.d. band. If one of them wins, the write-up says "the tuned fly jumps outside the range measured in real flies".
- **The grid:** R = **25, 50, 75, 100, 150, 200 Hz** × **all 50 cube training levels**, fly-driven closed loop, baseline encoding, **seed 0**: 300 runs, one night (≤ ~8 h). Every frame logged (hard rule 10); stuck runs kept and counted (D38). The two Step 2 comparisons aren't tuned.
- **Score: mean progress over the 50 levels.** Levels completed by difficulty, D48's death classes per R and stuck runs are reported beside it. R can change (b), (c) and (d) deaths, not (a), so the classes show where any gain comes from.
- **Tie margin, measured:** max(1 point, |mean progress at seed 0 − at seed 1|, both at 150 Hz on the 50 training levels). The seed-1 run is done (50 runs, commit `7115b8b`); the seed-0 run is the grid's own 150 Hz run, so the margin is computed when the grid finishes, by this rule.
- **Tie-break:** among rates within the margin of the best, the one whose **open-loop first-spike θ is closest to 39°** (the table above). A rate where fewer than half the trials fire ranks last, then by trials fired; any remaining tie goes to the rate closest to 150 Hz on a log scale.
- **Headline:** the picked R, its mean progress, and its open-loop first-spike θ with trials fired. **The first thing the write-up says about Step 3 is where the tuned fly sits against the real fly's range** (39 ± 14°, so 25–53°): if the pick is 75 Hz or lower (open-loop θ 56° or more), "the tuned fly jumps outside the range measured in real flies"; at 100 Hz (50°), "near the late edge of it" (Shannyn). Not a footnote.
- **If 150 Hz wins,** tuning didn't help; that's the Step 3 result and the held-out run isn't repeated. **At an edge (25 or 200),** it's reported as at the edge; the range isn't widened (D43). **No second, finer grid.**
- **Held-out check** at the picked R: the 20 held-out cube levels at **seeds 0, 1 and 2** (60 runs, blind, D33), against the Step 2 baseline at the same seeds. Per level, each setting's **median run across the three seeds** is compared with D48's "equal" (same killing object, or both completed), then D48's two-sided sign test (p < 0.05). Also reported: the paired difference in median progress, runs completed, and the picked R's training score next to its held-out score, so any overfitting shows. No pass/fail bar: both outcomes are results.
- **Framing for the write-up** (Shannyn): if the best R is below 150 Hz, the fly is jumping later than it was calibrated to, and later than real flies on average, and part of any gain may make up for slabs not looming (D47). Say so, rather than present it as the fly getting better.
  - **Model artifact (agreed with Shannyn, 2026-11-03):** "Carry-over from the previous object (~20% of approaches) is a property of the model, but not the main cause of early jumps: the early (d1) jumps come from the low half of the normal spread. We therefore expect a lower R to shift the whole spread later. If it wins, the tuned fly jumps later than real flies do, partly making up for slabs not looming (D47), and the write-up says so." The shift is a prediction until the grid runs; the grid report gives the carry-over share and first-spike θ without it at each R, so it can be checked.
- **Prediction, recorded before the grid:** the ideal fly does best with a later threshold (45–50°, D47), and on the training check nearly all the fly-driven cube's deaths are early jumps, (d1): its first Giant Fiber spike, without carry-over, comes at 37.2 ± 6.5°, so about half its jumps come before 39°, which spike rows punish (D48 amendment). **So we expect the best R below 150, probably 75–100 Hz** (open-loop θ 50–56°). If lower rates miss too many obstacles, the middle wins. A prediction to check against, not a rule.
- **Code:** `configs/step3.toml`, `scripts/step3_grid.py` (`check`, `margin`, `grid`, `held-out --rate R`), `scripts/step3_report.py` (and `--held-out R`), `stereo_flyness.experiments.tuning` (tested).
- Stereo Madness isn't touched (D7).
