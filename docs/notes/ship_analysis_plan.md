# Ship baseline analysis plan: how the untuned ship will be judged

*Shannyn, 2026-11-10. Updated the same day for the redesign (option B, with C as its control; `ship_proposals.md` §8, D53). **Written before any fly-driven ship run, with the held-out ship levels unseen.** It builds on the Step 2 plan (`docs/notes/step2_analysis_plan.md`, D48) and on `docs/notes/ship_proposals.md`. Fixed with D53, before the baseline runs.*

The ship baseline asks: with nothing tuned, does the fly fly the ship levels at all, and does it do better than holding or not holding? This plan fixes now what we'll measure, how deaths are classified and how comparisons are read.

**Not covered here:** mixed levels and Stereo Madness (Step 6), and any ship tuning (decided after the baseline, as agreed).

## What gets run

On the **20 held-out ship levels** (easy 8, medium 8, hard 4), closed loop, **whole brain**, **seeds 0, 1 and 2** (60 runs per condition):

| Run | Settings | Role |
|---|---|---|
| **B, baseline of record** | ω_self(vy − v_req); ω_full = 30°/s; R_ship = 150 Hz; DNp22 rule (spike → release next tick) | The result |
| **C, control** | ω_self(−v_req), otherwise identical | Steering without the fly's stabiliser: does the stabiliser help? |
| **Faster-anchor variant** | B with ω_full = 90°/s (3×, ~3 Hz, active-state range; Strother et al. 2018) | Labelled, always reported second (as D50) |

**No-brain references** (deterministic, or 10 random draws per level):
- **Never hold** and **always hold.**
- **Random holds:** alternating hold and release stretches drawn at random from the baseline's own hold- and release-length distributions (per level, 10 draws). So chance holds as often and switches as often as the fly; only the timing differs.
- **The ideal ships** of B, C and self-motion only (sign-only rule, no brain), as run against D53's bars. The failed draft's two ideal ships are reported as described, not compared.

## Before the baseline: open-loop checks

Run on the whole brain, both eyes, 10 trials each, and recorded as **description** (not pass/fail), except where marked:
1. **Zero input gives zero:** no ship input → 0 DNp22 spikes (as D30). **Gate:** if this fails, nothing runs until it's understood.
2. **Response to motion speed:** wide-field downward motion at f = 0.25, 0.5, 1 (i.e. 7.5, 15, 30°/s at ω_full = 30°/s), and the same for upward. DNp22 and VS rates per side. This is the ship's version of the cube's open-loop calibration check.
3. **Left eye only** (agreed): does the left side reach DNp22? Reported per side.
4. **Both together:** "down" with "up" at the same f (the S2-style suppression).

## Primary result

- **Levels completed** out of 20, and runs completed out of 60, by difficulty.
- **Mean progress** (%), by difficulty.

Read against, in this order:
1. **The references** (never hold, always hold, random holds): is the fly better than not trying, and better than holding at random as often as it does?
2. **B's ideal ship:** how close does a noisy brain get to the encoding's own noiseless use?

**Predictions:** written after the ideal-ship results are in and before the baseline runs, so they can use them. Dated and logged with this plan.

## How each death is classified

Every death gets exactly one class, decided by a fixed procedure, in this order:

| Class | Meaning | How it's decided |
|---|---|---|
| **(s) stuck** | The brain was in the stuck state (D38) | The stuck flag was on at death |
| **(a) unseen** | The killing object never reached the eye | It was never the nearest surface in any of the 37 viewing directions before contact (e.g. hidden behind a nearer surface) |
| **(b) the encoding's limit** | Even the ideal ship dies here | **Re-play** from the tick the killing object was first seen, using the run's own holds up to then, with B's ideal ship from there (C's for C runs). If the ideal ship also dies on the same object, it's (b) |
| **(d) the fly's control** | The ideal ship would have survived; this fly didn't | Everything else. Split by where the fly was against the ideal ship on the death tick, re-played from the same state: **(d↑) too high** (the fly's y above the ideal ship's) or **(d↓) too low** |
| **(u) unclassified** | Anything the rules above can't decide | Counted and listed; expected to be 0 |

- **The re-play is exact:** the game is deterministic, so the run's holds rebuild the state, and the ideal ship needs no brain.
- **(d) is the class that's about the brain.** (a) and (b) are limits of what the fly is shown or of the encoding itself.
- **Caveat:** the ideal ship is on/off (sign only), not optimal. A brain could survive where the ideal ship dies; those deaths can't happen in (b) by construction, and a fly that beats the ideal ship somewhere shows up as fewer deaths overall, not as a class.
- **(d↑) and (d↓) tell us which way the fly errs.** With silence = hold, a fly whose DNp22 fires too little drifts up; one that fires too much drifts down.

## How the fly flies (every ship tick)

- **Holding:** share of ticks held, median hold and release lengths, switches per second (built).
- **Input → output:** DNp22 spikes per frame against the pooled image motion f (and, separately, against our steering input v_req). Reported as the mean DNp22 rate in bins of f, per side. A working pathway should rise with downward f and stay near 0 for upward f.
- **Which side releases:** share of releases from left DNp22 only, right only, or both (the v783 asymmetry, `ship_proposals.md` §3).
- **Lag:** ticks between the pooled motion turning downward and the next release, as a distribution. Described only.
- **Tracking:** the ship's vy against v_req over time, and the error to the target centre when each column is passed.
- **DNp20 and VS cells:** recorded and described (DNp20 isn't in the rule).

## The comparisons

- **Every comparison:** per level, each condition's median run across the three seeds; D48's "equal" (both completed, or both died on the same object); two-sided sign test across levels, "better" or "worse" only at p < 0.05, otherwise "no clear difference".
- **Fly against each reference:** never hold, always hold, random holds (each random draw compared, as in D48, plus the mean of the draws).
- **Faster-anchor variant against the baseline:** read as "does the anchor's state matter?", not "which is better tuned". The headline is the baseline whichever does better (as D50).
- **C against B:** read as "does the fly's stabiliser improve steering?" (B better: yes; no clear difference: the stabiliser adds nothing we can see; C better: it hurts).
- **Noise line:** seed against seed for the baseline, as context.

## Stuck runs (D38)

Counted as they played out, also reported with stuck runs left out, plus the stuck rate per simulated second.

## Fixed in advance

- **No changes after seeing results:** not to the encoding, the opening rule, v_req, the field of view, the pooling, ω_full, R_ship, the output rule or the levels. Nothing is re-run with new seeds and no level is dropped.
- **D33:** nobody looks until the whole batch has finished; only the stuck flag and the run checks are live.
- **The analysis code is tested first** on training-level runs that don't count.
- **Replays for the write-up are picked by rule:** the lowest-seed completed level, and the lowest-seed death of each class, each with the brain panel's ship column.
- **Stereo Madness isn't touched** (D7).

## Questions for Jacob

1. Random holds drawn from the fly's own hold and release lengths, instead of D48's rate-matched presses: OK to build?
2. Can the classifier re-play from "first seen" with the ideal ship, and find "first seen" from the 37 directions?
3. Cost of the three conditions (B, C, B's 3× variant): three overnight batches?
4. The open-loop checks: about how long on the whole brain?
