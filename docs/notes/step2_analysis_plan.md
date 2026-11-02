# Step 2 analysis plan: how the untuned baseline will be judged

*Shannyn, 2026-11-01. Draft for agreement with Jacob. **Written before any Step 2 baseline run, with the held-out levels unseen** (D44). Once agreed, it's logged in `docs/decisions.md`, as with D29–D31 and D43.*

The baseline is the project's first real result: does the fly, with nothing tuned, play the cube levels at all? This plan fixes now what we'll measure, how deaths are classified and how the comparisons are read, so the results can't shape the analysis.

## What gets run (from D43, plus two proposed additions)

On the **20 held-out cube levels** (easy 8, medium 8, hard 4), closed loop, on the final subcircuit:

| Run | Settings | Role |
|---|---|---|
| **Baseline of record** | R × f, θ_full = 200° (calibrated), collision-course looming, R = 150 Hz | The result |
| Comparison 1 | Flat R, θ_full = 1,082° (its own calibration) | Does rate scaling (D45) matter? |
| Comparison 2 | "Every object looms", θ_full = 200° | Does the collision-course rule matter? In cube levels this only tests objects below the cube and objects landed onto, since cube levels have no ceilings (`docs/notes/encoding_check.md`) |
| Ideal 39° fly (D44) | No brain; presses one tick after θ ≥ 39° | Reference: a fly that fires exactly at the calibration target |

**Proposed additions** (Jacob's views needed on cost):
1. **Three seeds per level for the baseline of record** (60 runs instead of 20). The brain's input is random (Poisson), so one run per level can't separate the fly's skill from luck. How often the same level gives the same outcome is itself a result: how reliable the fly is. The comparisons stay at one seed per level.
2. **Two no-brain reference runs**, both cheap and deterministic:
   - **Never press:** how far a cube gets without jumping at all. This is the floor.
   - **Random presses at the fly's own press rate:** presses placed at random times, at the same average rate as the baseline's presses, with 10 random draws per level. If the fly doesn't beat this, its timing isn't doing anything.

## Primary result

- **Levels completed** out of 20 (and out of 60 runs, with seeds), by difficulty.
- **Mean progress:** how far through each level the cube got (%), by difficulty.

Read against, in this order:
1. **The floor** (never press) and **chance** (random presses): does the fly do better than not trying, and better than pressing at random?
2. **The ideal 39° fly:** how close does a real, noisy brain get to a perfectly calibrated one?

**Prediction, recorded now:** with the ground clip (D47), the ideal fly completes easy 20/20, medium 1/20 and hard 0/10 on the training levels (21/50; before D47 it was 26/50). In proportion, that's **~8–9 of the 20 held-out levels** for the ideal fly, nearly all of them easy. We expect the baseline at or below that: most easy levels completed, almost no medium or hard ones. On the training levels the ideal fly's deaths were mostly class (b) (19 of 29) with the rest class (a) (10), so we expect (a) and (b) to dominate, and anything beyond that to show up as class (c).

## How each death is classified

Every death gets exactly one class, decided by a fixed procedure, in this order:

| Class | Meaning | How it's decided |
|---|---|---|
| **(s) stuck** | The brain was in the stuck state (D38) | The stuck flag was on at the time of death |
| **(a) invisible** | The fly couldn't see what killed it | The killing object never loomed before contact (landed onto, or below the cube) |
| **(r) short run-up** | It appeared already too big | When it first became the nearest looming object, its θ was already ≥ 39° |
| **(b) wrong moment** | Visible, but 39° is the wrong time to jump | **Re-play** the game from the moment the object first loomed, with the ideal 39° policy. If the ideal fly also dies there, it's (b) |
| **(c) the fly's timing** | The ideal fly would have survived; this fly didn't | Everything else. Split by what the fly did: **(c1)** pressed too early, **(c2)** pressed too late, **(c3)** never pressed |

- **The re-play is exact:** the game is deterministic, so the run's own presses up to that moment rebuild the state, and from there the ideal policy needs no brain.
- **(c) is the class that's about the brain.** Classes (a), (r) and (b) are limits of the encoding or the 39° target, the same for any fly; (c) is where this fly's spikes made the difference. It's the most interesting number in the analysis.

## Timing, for every obstacle approach

For each approach (as defined in D46: from when an object becomes the nearest looming one until it stops looming):
- **θ at the first Giant Fiber spike.** Report its distribution against the calibration (39°, model s.d. 8.5°) and the real fly (39° ± 14°). Closed loop should match the open-loop calibration; if it doesn't, that's a finding.
- **Press timing against the press window,** where the window is known (single spikes: gap 1–73 units).
- **Presses with nothing looming** (should be ~0, since no input gives no spikes, D30) are counted.

## The comparisons

- **Paired by level** (and seed, where it matches): for each level, did the comparison do better, worse or the same as the baseline?
- **We only say one setting is "better" if a paired sign test across levels gives p < 0.05.** Otherwise it's reported as "no clear difference". With 20 levels, small differences won't be distinguishable, and that's said plainly.
- **Comparison 1 (flat R):** read as "does rate scaling change how the fly plays?", not "is R × f better tuned". Nothing is tuned.
- **Comparison 2 (every object looms):** read for its effect on class (a) and (b) deaths.

## Stuck runs (D38)

- Counted in the main results as they played out.
- Also reported with stuck runs left out, plus the stuck rate per simulated second.
- Jump timing (θ at first spike) is compared between stuck and normal stretches.

## Fixed in advance

- **No changes after seeing results:** not to the encoding, the jump rule, θ_full, R or the levels. Nothing is re-run with new seeds, and no level is dropped. Step 2 is untuned by design. Tuning is Step 3, on training levels only.
- **D33's ground rules apply:** nobody looks until the whole batch has finished. The stuck-state flag is the only live check.
- **The analysis code is tested before the held-out runs are opened,** on runs that don't count: the rule 5 validation runs on training levels, or fly-driven runs on training levels.
- **Replays chosen for the write-up are picked by rule, not by eye:** the lowest-seed level that's completed, and the lowest-seed death of each class. Each is shown with the brain panel (R3).

## Questions for Jacob

1. Is three seeds per level for the baseline affordable? At D46's measured speed (4 runs of ~30 s in 6.4 min), 60 runs is about 1.5–2 h with 4 at once.
2. Can the death classifier re-play from a state with the ideal policy (for class b vs c)?
3. OK to add the two no-brain references (never press; random presses at the fly's rate)?
4. Which runs can serve as the analysis dry run: the rule 5 validation runs, or a few fly-driven training-level runs?
