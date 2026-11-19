# Write-up, Part 2: methods (draft)

*Jacob, 2026-11-16. Written **while the held-out runs were going and before any result from them or from Stereo Madness's new seeds was seen**. It is drawn from settled decisions only (D55–D59, plus D60 once #87 is merged). Every number is copied from the decision log or the note it cites. It's a first draft for Shannyn to rewrite, cut or reorder, as with Part 1's methods (`writeup_methods.md`, `writeup_methods_4to7.md`). **[Shannyn]** marks where the biology framing is hers. Results go in `writeup_part2.md` (P1–P9), not here.*

*Every Part 2 section carries D55's label: "exploratory: interface adjusted after seeing Stereo Madness; brain wiring unchanged."*

## M1. What stayed fixed, and what could change (D55)

- **Frozen:** the FlyWire v783 connectome and Shiu et al.'s model, as in Part 1 (§1); everything Part 1 reported; the fly of record, unchanged:
  - the whole brain;
  - θ_full 200°, calibrated to the real fly's mean threshold, 39° (D43);
  - R × f at R = 150 Hz (D45, D50);
  - original signs;
  - the collision-course encoding (D41–D47);
  - the output rule: press while the Giant Fiber fires.
- **What could change:** our interface (`src/stereo_flyness/interface/`) only. One fix at a time, each with:
  - a dated design note;
  - Shannyn's biology argument and predictions, written before it ran;
  - at most 2–3 new dials across iteration 2, set on training levels only.

  **No fix used a dial:** fix 1 adds no number, and fixes 2 and 3 built nothing.
- **Stereo Madness was spent** as a held-out test in Part 1 (D54). In iteration 2 we may look at it, and say so (hard rule 5 lifted for iteration 2 only). It never judges a fix: it shows only how far the fly then gets, on new seeds (100 onwards) with N fixed beforehand.
- **Extra runs** on any held-out levels or on Stereo Madness were agreed by both of us before they ran.

## M2. How each fix was tested (D55)

The same order for every fix, each step fixed in writing before it ran:

1. **A design note** with Shannyn's biology argument and predictions. Predictions are scored hit or miss, with no partial credit; confidence isn't part of the score.
2. **A no-brain check:** the ideal fly, a scripted cube that presses exactly when an obstacle reaches a chosen θ. It runs on the iteration-2 training levels, with a gate fixed beforehand. If the gate fails, no fly runs are made.
3. **Fly runs on the training levels:** the fly of record, unfixed and fixed, seeds 0–2. **At most one revision per fix,** logged with its reason. These are descriptive.
4. **Once, at the end of iteration 2:** the fresh held-out suite (D55's bar, M6), and the no-harm check on iteration 1's held-out cube levels.

**The main measure** (Shannyn, D55) is **"gets past the feature"**: for each level, whether the median run over 3 seeds gets past the fix's feature. The fixed fly is compared with the unfixed fly by a two-sided **sign test** across the levels that differ. Progress and completions are reported beside it.

**The data rules carried over from Part 1 (D33):**
- runs are blind, printing only progress and stuck flags;
- all runs in a set come from one clean commit, stamped in each run;
- no tracked edits while runs are going;
- every run must replay exactly from its logged presses;
- one report script per run set, merged before the runs, which checks every run first and reports nothing if any check fails;
- the report is checksummed before it's opened;
- reports are opened together, section by section.

## M3. The new levels (`docs/notes/iteration2_levels.md`)

- **Generator v4** adds four kinds of obstacle:
  - raised platforms followed by pits (`platform_drop`, `step_down_pits`);
  - plain step-downs (`platform_step_down`), the no-harm control;
  - spaced pairs of obstacles.

  Their ranges were fixed from the game's physics, before Stereo Madness was studied further, and aren't centred on its spacings. Every level has at least one drop and one spaced pair. Iteration 1's v3 levels rebuild unchanged.
- **Fix case or control.** We simulate a cube that walks off the platform without pressing:
  - if it lands in the pits, the drop is a **fix case**;
  - if it lands on the ground first, the drop is a **control**.

  A fix case is also labelled by **k**, the number of ground cells between the edge and the first pit.
- **Suites, frozen before any run:**
  - 50 training levels: 20 easy, 20 medium, 10 hard;
  - 40 held-out levels: 16 easy, 16 medium, 8 hard, seeds from 2,000,000.

  The held-out suite was built unopened and is opened once. Every level's hash is tested.
- **Not comparable with Part 1 by tier name.** Iteration-2 "easy" levels are harder than iteration 1's (press windows down to 8–21 ms).

## M4. Fix 1: letting the fly see the drop (`docs/notes/fix1_design.md`)

**The problem.** The collision course shows the fly only objects that overlap the cube's current height. Standing on a raised platform, the pits past its edge are below the cube, so they never loom: the fly walks off and falls in. This was Stereo Madness's second wall in Part 1.

**The change has two parts:**
- **Which objects are on course.** While the cube stands on something raised, an object is on course if it overlaps the cube's **no-press path**. That is where the cube would go if the fly never pressed again, under the game's exact physics: walking on, falling off edges, landing on solids.
  - **This applies only on the ground.** In the air the old rule stays, so objects the cube lands onto stay invisible (agreed 2026-10-31).
  - **At floor level (y = 0) nothing changes,** because the floor is solid everywhere, so the path is flat.
  - **Plain edges stay silent.** Walking off onto empty ground puts nothing on the path.
- **How big an on-course object looks (θ).** With true optics, option (i), pits below a platform peak at 7–14°, well under the 39° threshold, so they would loom without ever triggering a jump. **Option (ii), the landing-level view,** shows an object that's on course only because of the fall as it would look from an eye at the object's base level (its bottom + 15), at the true horizontal distance. Objects already on course keep their usual θ.

**[Shannyn] Framing.** Our code supplies the foresight and the fly supplies the timing, as in ship design B. Her agreed wording: "From on top of a platform, pits below the edge never loom with true optics (they peak at 7–14°, below the ~39° threshold). We therefore show on-course objects as they would look from the level the object stands at. This is our encoding's prediction, not something the fly's eye computes; the fly's contribution is when it jumps." We make **no claim that flies use looming to cross gaps**: walking flies judge a gap's width by sight, most likely from the parallax of its far edge, and cross it by climbing, not by an escape jump (Pick & Strauss 2005).

**Conditions:**
- (i) is reported beside (ii) in every check;
- every frame where (ii) changes the input is flagged in the run log and labelled in replays: "θ shown from landing level, our construction";
- no number is added: θ_full, R, the rate scaling, the patch order and the 39° calibration are unchanged.

**The checks, in order:**
- **Code tests:**
  - with the option off, the encoding is identical on every tick of the bot's path through all iteration-1 training levels;
  - with it on, θ is identical wherever the cube is in the air or at floor level;
  - pits past a platform loom, and a plain step-down shows nothing.
- **Step 2, the ideal fly** at 39°, current encoding vs (i) vs (ii), on the iteration-2 training levels.

  **Gate (Shannyn):** with (ii), the ideal fly must clear at least 50% of the fix-case drops.

  It was refined before anything ran: it counts only pit strips of ≤ 3 cells, because a jump from a platform at the 39° point clears at most 3 cells. That way it tests the encoding, not the game's physics.
- **Step 3, fly runs:** 50 training levels × unfixed / fix 1 (ii) × seeds 0–2, 300 runs, with the measures fixed in `fix1_step3_plan.md`:
  - the feature is a level's first fix-case drop;
  - a level gets past it if 2 of its 3 seeds do;
  - beside that: every drop reached (by k and pit width), controls, jumps while on top of plain step-downs, progress, completions and deaths by obstacle type.
- **Step 4, held-out** (M6).

**The arms are compared in a clean way.** With the same seed, the two arms get identical input until fix 1 first changes a frame, so they must play identically up to that frame, and throughout where it changes none (Shannyn). This is checked before anything is reported. On step 3's runs it held for all 150 pairs (55 of 55 unchanged pairs identical throughout, 95 of 95 identical up to the first changed frame).

## M5. Fixes 2 and 3: checked, then stopped

**Fix 2, close obstacles** (`docs/notes/fix2_design.md`, D56). There was no brain for this one:
- **The spread-aware ideal fly:** thresholds drawn per approach from the fly's own measured spread (first spike at 37.1 ± 7.3°, 20 draws).
- **A shifted-mean sweep:** whether any mean threshold beats 37.1° by at least a margin N. N was fixed from noise before the sweep was read, and came out as N = 3.
- **Decided (D56): (a), reported as a limit.** **[Shannyn]** "Close groups of obstacles need an aimed jump. The Giant Fiber escape fires at a size threshold with a natural spread and doesn't aim…"
- **A later proposal, (e)** (`fix2_group_view.md`): show a group of touching spikes from its far end. It was **declined before anything was built (D58).** The double spike is shown correctly, and the fly fails it because its timing varies. Making up for that would be our code aiming the jump.

**Fix 3, the ship.** Its condition was fixed before any iteration-2 run: only if fixes 1 and 2 let the cube reach a ship section. No run did, so **it stopped (D59).** The ship's limit stays Part 1's finding (D53).

## M6. Fix 1 on held-out levels (`docs/notes/fix1_heldout_plan.md`)

**Setup.** The fly of record, unfixed and with fix 1 (ii) exactly as in step 3, with no revision (D57). Seeds 0–2. All runs come from one clean commit (`17d552e`), blind:

| | The test | The no-harm check |
|---|---|---|
| **Levels** | The 40 iteration-2 held-out levels, never run before | Iteration 1's 20 held-out cube levels, seen in Part 1 |
| **Runs** | 40 × 2 arms × 3 seeds = 240 | 20 × 2 × 3 = 120 |

Both arms were run fresh on iteration 1's levels, so the arms are treated identically (Shannyn). Whether the fresh unfixed runs match Part 1's tick for tick is reported as a side check, and not used to judge.

**Measures, fixed before any run:**
1. **The test (D55's bar):** levels past the feature (step 3's measure, unchanged), fixed against unfixed. **Fix 1 passes if it's better on more levels than worse, with a two-sided sign test p < 0.05.**
2. **The no-harm check.** These levels have no fix-case drops, so each level is scored as the median, over its 3 seeds, of the **obstacle groups passed** (a completed run passes them all). This means a run that dies at the same obstacle a few units further on isn't counted as "better" (agreed). **Fix 1 passes if there's no significant drop** (no p < 0.05 with more levels worse than better), **and it's worse on no more levels than better.**

   Also on both suites: no more jumps while on top of a plain step-down with the fix than without.
3. **What fix 1 changed** (Shannyn): the frames changed per level and seed, and for the no-harm check every level it changed, with what happened. Unchanged levels can't drift by chance (M4).

**Fix 1 counts only if it passes both** the test and the check. Otherwise the write-up says which part failed, reported as fully as a pass. There's no revision after this.

## M7. Stereo Madness on new seeds (`docs/notes/sm_newseeds_plan.md`, D60)

- **What it is:** only how far the fly gets with iteration 2's interface. It judges nothing (D55).
- **The fly:** the fly of record with fix 1 (ii), whether or not fix 1 counted.
- **Ship sections:** D53's design of record, B, at R_ship 150 Hz, untuned and unchanged from D54. It's needed only so the level can be run at all.
- **Seeds and N:** seeds 100–199, N = 100, fixed beforehand and agreed by both of us. One arm only.
- **The headline:** completed k of 100 and the median progress (the mean of the 50th and 51st runs), with quartiles and range. The best run is never the headline.
- **Reported beside it:**
  - where runs ended, by hazard strip;
  - the milestones:
    - past Part 1's furthest point (alive past the far edge of the pits where Part 1's best run died, x 2899.5; 10.9%);
    - the first ship portal (~30%);
    - the first ship section cleared;
    - a complete run;
  - the frames fix 1 changed;
  - the showcase replay: the run closest to the median (D54's rule).
- **Part 1's 100 runs** (seeds 0–99) are shown as context, not as a comparison: they are different seeds and had no fix.
- The report was tested on Part 1's opened runs as stand-ins, and reproduced D54 exactly.

## M8. Replays and labels (hard rule 10)

- Every closed-loop run logs every frame for the replay viewer (D19).
- Replays show the fly's recorded activity unaltered, and label our input separately from its spikes.
- Frames where fix 1 changed the input carry "θ shown from landing level, our construction".
- Every Part 2 video and figure carries D55's exploratory label.
