# Write-up, Part 2: iteration 2, exploratory (skeleton)

*Jacob, 2026-11-15. **Written before any iteration-2 result exists**, as Part 1's results were written before Stereo Madness was run: the order, the headings and the wording for each possible outcome are fixed now, so the results can't shape how they're framed. Nothing below changes after the runs except the blanks. Every number that goes in is copied from the decision log or the note it cites. **[Shannyn]** marks her framing; **[after …]** marks what's filled in once that step's results are opened. Part 1 is `docs/notes/writeup_results.md`, tagged `v1.0-research`, and isn't changed by anything here.*

**How to read Part 2:**
- **It's exploratory.** Every result, figure and video carries: *"exploratory: interface adjusted after seeing this level; brain wiring unchanged"* (D55).
- **The brain never changed.** The connectome is the same frozen FlyWire v783 model as Part 1; only our interface (`src/stereo_flyness/interface/`) changed, one fix at a time.
- **Fixes are judged on general levels, never on Stereo Madness.** Stereo Madness is spent as a held-out test (D54); in Part 2 it shows only how far the fly then gets.
- **The fly of record is unchanged:** calibrated to the real fly's mean threshold (39°), R = 150 Hz. Any variant is labelled and reported second.
- Every rule for judging a result was written down before the result was seen. A result against a prediction is reported as plainly as one that matched.

---

## P1. What we changed, and why (D55)

Part 1 ended at two walls in Stereo Madness's first section (R8): the double spike (7 of 10 runs) and the pits after a raised platform (2 of 10). Part 2 asks how far the same fly gets once our interface stops limiting it.

- **Fix 1, the pits: (ii) the landing-level view, with (i) true optics reported alongside** (`docs/notes/fix1_design.md`). **[Shannyn's agreed wording]** "From on top of a platform, pits below the edge never loom with true optics (they peak at 7–14°, below the ~39° threshold). We therefore show on-course objects as they would look from the level the object stands at. This is our encoding's prediction, not something the fly's eye computes; the fly's contribution is when it jumps." Our code supplies the foresight; the fly supplies the timing. No claim that flies use looming to cross gaps.
- **Fix 2, close obstacles** (`docs/notes/fix2_design.md`): first a no-brain check. The default is to report the double spike as a limit of a one-shot escape reflex; a later-threshold fly is allowed only as a labelled variant that passes a margin fixed in advance.
- **Fix 3, the ship:** only after fixes 1 and 2 (D55). **[after fixes 1 and 2]**

## P2. The new levels

- **Generator v4** (`docs/notes/iteration2_levels.md`): raised platforms followed by pits (`platform_drop`, `step_down_pits`), plain step-downs (`platform_step_down`) and spaced pairs, in ranges fixed from the game's physics before Stereo Madness was studied further. Every level has at least one drop and one spaced pair. Iteration 1's v3 levels rebuild unchanged.
- **Fix case or control** is decided per drop by simulating a cube that walks off without pressing: it lands in the pits (fix case) or on the ground first (control).
- **Suites, frozen before any run:** 50 training levels (20 easy, 20 medium, 10 hard) and 40 held-out (16/16/8), the held-out built unopened and opened once, at the end. Every level's hash is tested.
- **Not comparable with Part 1 by name:** iteration-2 "easy" levels are harder than iteration 1's (press windows down to 8–21 ms), so tiers aren't compared across parts.
- **Context, not a fly result** ("game geometry, scripted cube, our encoding's θ; not a fly result"): the geometry table (one jump clears a double spike from 38°, a triple spike from 97°; from a platform, a jump at the 39° point clears at most 3 pit cells, a jump right at the edge up to 5).

## P3. Fix 1, step 2: the ideal-fly check and the gate

*Fixed by fix 1's design note before it ran. No brain. Iteration-2 training levels only.*

**Setup:** the ideal 39° fly (`ideal_fly.py --all --iteration2 --sweep 10 175 5 --by-obstacle --fix1`), with the current encoding, (i) and (ii). **[after step 2]** commit, date.

**The gate:** with (ii), fix-case drops with strips of ≤ 3 cells cleared: **[__ of __, __%]** against ≥ 50%.
- **If it passed:** "With the landing-level view, an ideal fly at the real fly's average threshold clears __% of the drops a jump at that moment can clear (__ of __), against __% with today's encoding and __% with true optics. Fix 1 went on to fly runs."
- **If it failed:** "With the landing-level view, an ideal fly at the real fly's average threshold clears only __% of the drops a jump at that moment can clear (gate: 50%). By the rule fixed beforehand, no fly runs were made with fix 1." Then why, from the per-obstacle table.

**Table [after step 2]:** current / (i) / (ii): fix cases ≤ 3 cells, 4–5 cells, all; controls; plain step-downs (no-harm: edge jumps against the unfixed encoding); levels completed.

## P4. Fix 1, step 3: the fly on the training levels

*Only if the gate passed. Whole brain, R = 150 Hz, the record's settings. At most one revision, logged with its reason (D55 rule d).*

**[after step 3]** gets past the feature (median run per level over 3 seeds) with and without fix 1; progress; completions; the no-harm count at plain edges. **If revised:** what changed, why, and the result before and after, both shown.

## P5. Fix 1 on held-out levels (opened once, at the end of iteration 2)

*D55's bar, fixed before opening:*
- **Main measure:** gets past the feature (median run per level over 3 seeds), fixed fly against the unfixed fly, **sign test, p < 0.05**, on the 40 iteration-2 held-out levels. Progress and completions beside it.
- **No-harm check** (a check, not a test, since those levels have been seen): on iteration 1's 20 held-out cube levels, no significant drop, and worse on no more levels than better.

**[after opening]** better / worse / tied levels, p; the no-harm result.
- **If both pass:** "Fix 1 counts: on levels it was never designed on, the fly gets past the drop more often (__ better, __ worse, __ tied; p = __), and it does no harm on the levels of Part 1."
- **Otherwise:** "Fix 1 doesn't count by our bar: [which part failed]." Reported as fully as a pass.

## P6. Fix 2: close obstacles

*Fixed by fix 2's design note before the check ran. No brain.*

- **The spread-aware ideal fly** (thresholds drawn per approach from the fly's own spread, 37.1 ± 7.3°), on the iteration-2 training levels: **[after the check]** cleared share per obstacle type, double spikes and spaced pairs by gap; levels completed (a level counts if at least half its 20 draws complete it).
- **The margin, recorded before the shifted-mean sweep was read:** noise **[__]** levels, so N = **[__]**.
- **The decision:**
  - **(a) Report it as a limit** (the default): "**[Shannyn's agreed wording]** Close groups of obstacles need an aimed jump. The Giant Fiber escape fires at a size threshold with a natural spread and doesn't aim, so the fly clears a double spike only when its threshold falls on the late side of its spread, and can't clear triple spikes or close pairs at any threshold measured in real flies. We report this as a limit of a one-shot escape reflex in this game."
  - **(b), only if the best shifted mean beat 37.1° by at least N levels:** a labelled variant, *"a late-threshold fly, inside the range measured in real flies"*, with its own design note, reported second, held to D55's bar. Never the fly of record.

## P7. Fix 3: the ship

**[after fixes 1 and 2]** Only if fixes 1 and 2 let the cube reach a ship section. A new output rule, argued on its own merits (D55). If no run reaches a ship section, this section says so and stops.

## P8. Stereo Madness, new seeds

*Only how far the fly gets; never used to judge a fix. Seeds from 100 onwards, N fixed before each set and agreed by both of us (D55).*

**[before running: N, seeds, settings]** **[after the runs]** completed __ of N; median progress __%; where runs ended, by place. **Milestones,** each reported as reached or not: past 10.9% (Part 1's furthest); the first ship portal (~30%); the first ship section cleared; a complete run.

Read against Shannyn's prediction (fix 1's note): fix 1 alone leaves the median at ~9.2%, because 7 of 10 record runs die at the double spike before the pits.

## P9. Predictions, scored

Hit or miss each, by the rules in the notes that hold them, no partial credit.
- Fix 1 (`fix1_design.md`, 8 predictions): **[after each step]**
- Fix 2 (`fix2_design.md`, 6 predictions): **[after the check]**

## D2. Discussion

**[Shannyn]** leads; outline only, written before any iteration-2 result:
1. **What the interface was hiding:** how much of Part 1's wall was ours, not the fly's.
2. **Foresight vs timing:** what it means that our code supplies the prediction and the fly only the moment (fix 1).
3. **Spread, not threshold:** the double spike as a property of an escape reflex in a timing game (fix 2).
4. **What still needs a new mechanism:** landing onto things (slabs), aimed jumps (triple spikes, close pairs), graded descent (the ship).
5. **What we'd do next:** **[Shannyn / Jacob]**, including option B for gaps (showing the edge) and the long-mode take-off.

## L2. Limitations (in addition to Part 1's)

**[Shannyn]** final wording; nothing dropped:
- **(ii) is our construction:** no fly's eye predicts a fall. Reported beside (i), labelled in every replay frame where it's used.
- **Stereo Madness was seen** before Part 2, so nothing in Part 2 is blind there; only the new held-out suite is.
- **Landing onto things stays invisible** (agreed 2026-10-31), so getting onto a slab is a separate limit fix 1 doesn't touch.
- **Iteration-2 "easy" isn't Part 1's "easy".**
- **The fix-case label is our engine's walk-off,** not a measure of how a real fly would fall.

## Videos and figures

- Every Part 2 video and figure carries the exploratory label (D55), and replays label the landing-level frames: "θ shown from landing level, our construction".
- Figures go to `results/iteration2/figures/` (not committed).
