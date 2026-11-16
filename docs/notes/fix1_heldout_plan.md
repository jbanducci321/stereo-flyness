# Iteration 2, fix 1, step 4: the held-out opening (run plan)

*Jacob, 2026-11-16; **Shannyn's answers folded in the same day** (end). Fix 3 has stopped (D59), so fix 1's held-out opening is what's left of iteration 2 before Stereo Madness's new seeds. Exploratory (D55).*

**Agreeing this plan is agreeing these extra held-out runs (D55's rule on extra runs):** the 360 runs below, once, and no others. The iteration-2 held-out suite is opened **once**. Nothing runs until this plan, the report script (#82) and Shannyn's predictions are all merged.

## What runs

| | Iteration-2 held-out (the test) | Iteration-1 held-out cube levels (the no-harm check) |
|---|---|---|
| **Levels** | The 40 frozen iteration-2 held-out levels (16 easy, 16 medium, 8 hard; seeds from 2,000,000; `configs/iteration2/level_suites.toml`), never run by anyone | Iteration 1's 20 held-out cube levels (`cube-*-1000000…`; 8 easy, 8 medium, 4 hard), seen in Part 1 |
| **Arms** | Unfixed and fix 1 (ii) | Unfixed and fix 1 (ii) |
| **Seeds** | 0, 1, 2 | 0, 1, 2 |
| **Runs** | 40 × 2 × 3 = **240** | 20 × 2 × 3 = **120** |

- **Brain and settings:** as step 3. Whole brain, the fly of record (θ_full 200°, R × f at R = 150 Hz, original signs), the collision course; fix 1 (ii) exactly as in step 3, no revision (D57).
- **One clean commit for all 360 runs**, stamped in each (no tracked edits while they run).
- **Blind:** held-out runs print only progress and stuck flags (D33/D48). Nothing is read until all 360 have finished.
- **Output:** everything under `results/iteration2/closed_loop/` (rule 7), including the iteration-1 levels (`…/whole_brain/iteration1_held_out/…`), so nothing is written into Part 1's results.
- **Time:** step 3's 300 runs took ~5 hours. Iteration-1 levels run longer (the fly gets further on them), so roughly **7–10 hours** on 4 workers, overnight, in 12 batches (suite × arm × seed), with `--resume` if one is interrupted.

## The measures, fixed before any run

**1. The test (D55's bar), on the iteration-2 held-out suite:** the main measure exactly as step 3 (`experiments/fix1_step3.py`).
- **The feature** of a level is its first fix-case drop; a level without one is left out and counted.
- A level **gets past it** if at least 2 of its 3 seeds do.
- **Fix 1 passes the test** if the fixed fly is better on more levels than worse, with a two-sided **sign test p < 0.05** over the levels that differ.
- Beside it, as in step 3: each level's feature with its k; every drop reached, by k and pit width; controls; jumps while on top of plain step-downs; progress, completions, deaths by obstacle type, stuck runs.

**2. The no-harm check (D55), on iteration 1's held-out cube levels.** These levels have been seen, so it's a check, not a test. They have no fix-case features, so it's judged on how far the fly gets:
- **Per level:** the median, over the 3 seeds, of the **number of obstacle groups passed** before the run ends (a completed run passes them all). Counting obstacles, not raw progress, means a run that dies at the same obstacle a few units later isn't counted as "better" (agreed, question 2).
- **Fix 1 passes the check** if (a) there's **no significant drop** (two-sided sign test over the levels that differ; a result with p < 0.05 and more levels worse than better fails), and (b) it's **worse on no more levels than better**.
- **Fix 1's own no-harm condition** (`fix1_design.md`), on both suites: no more jumps while on top of a plain step-down with the fix than without.
- Beside it: completions (levels completed by at least 2 of 3 seeds, and runs completed), progress, deaths by obstacle type.

**3. What fix 1 actually changed (Shannyn, 2026-11-16), on both suites.** Every fixed run logs which frames fix 1 changed (its `predicted` flag). Where it changed none, both arms get identical input with the same seed, so they must play identically and tie exactly. Only the levels where it changed something can differ.
- **A check, before anything is reported:** on each level and seed, the two arms are identical up to the first frame fix 1 changed, and throughout where it changed none. If not, nothing is reported. (Tested on step 3's opened runs: 55 of 55 identical where it changed nothing, 95 of 95 identical before the first changed frame.)
- **Reported:** the frames changed per level and seed; how many levels it changed at all; and, for the no-harm check, every level it changed, with what happened. This answers the chance-drift worry: unchanged levels can't drift.

**Fix 1 counts** (D55) only if it passes both the test and the check. Otherwise it doesn't count by our bar, and the write-up (P5) says which part failed, reported as fully as a pass.

## How it's read

- **One report script, fixed and merged before any run** (#82): `scripts/fix1_heldout_report.py`, reusing step 3's tested measures, with the no-harm measure and the changed-frames check added and tested. It checks every run first (all 360 present, right settings, one clean commit, exact replay, the arms identical until fix 1 changes a frame, stuck runs counted) and reports nothing if any check fails. The overall verdict comes last. Exercised end to end on stand-ins only: step 3's opened training runs (which it reproduces exactly) and random-press runs on training levels, never a held-out level.
- **Runner change, in the same PR:** `play_level.py` gets a way to play iteration 1's held-out cube levels with the iteration-2 label and output folder. It's refused without `--iteration2-final`, like the iteration-2 held-out suite.
- When the runs finish, the report is written without being opened and checksummed. It's then **opened together**, section by section, as in step 3: the test, then the no-harm check, then the rest.
- **Scored at opening:** Shannyn's fix 1 prediction 7 ("Real fly, iteration-2 held-out: does fix 1 pass the bar? **Yes**", medium-low confidence). Prediction 8 (Stereo Madness) waits for the new-seed runs (P8).
- **No revision after this.** D55 allows one revision per fix, decided on training levels; fix 1 had its chance at step 3 and wasn't revised (D57). Whatever the held-out result, it's the result.

## What comes after

1. Log the result (a D-entry) and fill P5 of Part 2's write-up.
2. **Stereo Madness on new seeds** (P8): N, seeds (100 onwards) and settings agreed by both of us first, with fix 1 (ii) as it stands, whether or not it counted. It shows only how far the fly gets; it never judges a fix.
3. Score fix 1's prediction 8, then finish the write-up.

## Questions for Shannyn (answered 2026-11-16, below)

1. **Fresh unfixed runs on the iteration-1 levels, or Part 1's?** Part 1 already has the unfixed whole-brain fly on these 20 levels, seeds 0–2 (Step 4's intact runs, `91989c6`). I'd run both arms fresh at one commit, so the two arms are treated identically. As a side check, I'd report whether the fresh unfixed runs match Part 1's tick for tick (they should; reported, not used to block). Reusing Part 1's runs would save ~60 runs (~1–2 hours), but would mix commits and runners.
2. **The no-harm measure: obstacles passed, or raw progress?** D55 doesn't say which. Fix 1 only changes the input while the cube stands on something raised. After one changed frame, a run can drift by chance either way, so with raw progress a fix that does nothing might well come out "worse on more levels than better" about half the time. Counting obstacles passed reduces that, but doesn't remove it. Are you happy with obstacles passed, fixed now, before anything runs?
3. **Anything to add**, e.g. predictions for the no-harm check, before the runs?

## Shannyn's answers (2026-11-16)

1. **Fresh runs for both arms,** one commit, with the tick-for-tick comparison to Part 1 as a side check (reported, not used to judge). Agreeing this plan counts as agreeing these extra held-out runs (D55); added at the top.
2. **Obstacles passed, fixed now.** Added: count per level the frames fix 1 actually changed, check that unchanged levels play identically, and list the changed levels with what happened (measure 3).
3. **She'll add predictions to fix 1's note before the runs.** The runs wait for that PR as well as the report script.
