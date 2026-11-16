# Iteration 2: Stereo Madness on new seeds (run plan, P8)

*Jacob, 2026-11-16. A plan for Shannyn to agree **before anything runs**. It's the last run set of iteration 2 (D59), after fix 1's held-out opening (`fix1_heldout_plan.md`). Exploratory (D55).*

**What it is, and isn't (D55):** Stereo Madness is spent as a held-out test (D54). These runs show **only how far the fly gets** with iteration 2's interface. They never judge a fix: fix 1 is judged by its held-out opening alone. **Agreeing this plan is agreeing these extra Stereo Madness runs (D55's rule on extra runs):** the runs below, once, and no others.

## What runs

| | |
|---|---|
| **The fly** | The fly of record (whole brain, θ_full 200°, R × f at R = 150 Hz, original signs) **with fix 1 (ii)** exactly as in step 3 and the held-out opening. Fix 2 adds nothing (a limit, D56/D58); fix 3 stopped (D59) |
| **Ship sections** | D53's design of record, B, R_ship 150 Hz, untuned, as in D54. Needed to run the level at all; changed in nothing |
| **Seeds** | **100–199** (D55: new seeds from 100; Part 1 used 0–99) |
| **N** | **100**, fixed now (question 1) |
| **Arms** | **Fix 1 (ii) only** (question 2) |
| **Commit** | One clean commit for all runs, stamped in each; no tracked edits while they run |
| **Output** | `results/iteration2/stereo_madness/…` (rule 7), never Part 1's `results/stereo_madness/` |
| **Blind** | Only progress and stuck flags are printed (D33) |

**Why N = 100:** D54's headline was 10 runs, and the 90 extra runs that followed showed the same two walls (53 at the double spike, 33 at the pits). The fly gets past the double spike about half the time (D56, D57), so with N = 10 only ~5 runs would even reach the pits, too few to say what happens there or beyond. With N = 100, about 50 do. It also matches Part 1's 100 runs (seeds 0–99), which become the context.

**Time:** Part 1's runs ended by ~11% of the level. Runs that get further take longer, so roughly **2–4 hours** on 4 workers.

**When:** after the held-out opening's runs have finished, so the two never share a commit window. It can run before or after that report is opened. The two don't depend on each other, since these runs judge nothing.

## The report, fixed before any run

Checks first, as D54's: every run present, settings and connectome right, one clean commit, exact replay, stuck runs counted. Nothing is reported if a check fails. Then:
- **The headline:** completed **k of 100**; **median progress** (quartiles, range). Never the best run as the headline.
- **Where runs ended, by place:** the killing object and its x, grouped (as D54: "the double spike", "the pits after the raised platform", …), cube or ship section.
- **Milestones, each reached or not, with how many runs:** past 10.9% (Part 1's furthest); the first ship portal (~30%); the first ship section cleared; a complete run.
- **Context, not a comparison:** Part 1's 100 record runs (seeds 0–99, no fix 1) by the same measures. They're different seeds and judge nothing; they show what changed in where the fly stops.
- **Frames fix 1 changed, per run** (its `predicted` flag), so it's clear where the fix acted.
- **The showcase replay** (D54's rule): the run closest to the median, ties to the lowest seed; optional and labelled, the furthest run, captioned "the furthest of 100". Both carry the exploratory label and the landing-level label (D55, hard rule 10).
- **Scored at opening: Shannyn's fix 1 prediction 8:** "Median unchanged at ~9.2%; the furthest run passes 10.9%", high confidence for the median, medium for the furthest run. *Before the runs, we fix what "unchanged" means (question 3).*

**Opened together**, after the report is checksummed, as before.

## Code needed (a separate PR, before any run)

- **The runner:** `play_level.py` refuses Stereo Madness with `--iteration2`, and with `--fix1` alone it would write into Part 1's `results/stereo_madness/`. It needs a way to run Stereo Madness for iteration 2 into `results/iteration2/stereo_madness/`, still only with `--stereo-madness-final`.
- **The batch:** `configs/iteration2/stereo_madness.toml` (the decision logging this plan, seeds 100–199, fix 1 (ii), ship B at 150 Hz) and `stereo_madness_runs.py` able to read it. D54's own config stays untouched.
- **The report:** D54's report extended with the milestones, Part 1's context and the changed frames, tested on Part 1's 100 opened runs as stand-ins.
- **D54's gates** (the ship open-loop gate, the mixed-level switching check) are rechecked by the runner. Since D54's runs (`e72c2d7`), only the cube encoder has changed (fix 1, off by default); the ship encoding, the mode switching, the game and the brain code are unchanged (checked 2026-11-16).

## Questions for Shannyn

1. **N = 100, seeds 100–199?** Or D54's N = 10, which would leave only ~5 runs at the pits?
2. **Fix 1 (ii) only, or the unfixed fly too, on the same seeds?** I'd run fix 1 only and use Part 1's 100 runs as context. These runs judge nothing, and a same-seed unfixed arm would invite exactly the comparison D55 rules out. Its one advantage: your identical-until-changed check, run for run (it held on all 150 step 3 pairs).
3. **What counts as "unchanged" for prediction 8?** A proposal, fixed before the runs: the median is unchanged if it's within ±1 percentage point of 9.2% (8.2–10.2%), since Part 1's 100 runs ended at a few fixed places. It's a hit if the median is in that band and the furthest run passes 10.9%.
4. **Anything else in the report,** or predictions to add, before the runs?
