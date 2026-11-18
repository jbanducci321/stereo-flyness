# Write-up, Part 2: iteration 2, exploratory (skeleton)

*Jacob, 2026-11-15. **Written before any iteration-2 result exists**, as Part 1's results were written before Stereo Madness was run: the order, the headings and the wording for each possible outcome are fixed now, so the results can't shape how they're framed. Nothing below changes after the runs except the blanks. Every number that goes in is copied from the decision log or the note it cites. **[Shannyn]** marks her framing; **[after …]** marks what's filled in once that step's results are opened. Part 1 is `docs/notes/writeup_results.md`, tagged `v1.0-research`, and isn't changed by anything here.*

**How to read Part 2:**
- **It's exploratory.** Every result, figure and video carries: *"exploratory: interface adjusted after seeing Stereo Madness; brain wiring unchanged"* (D55).
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

**Setup:** the ideal 39° fly (`ideal_fly.py --all --iteration2 --sweep 10 175 5 --by-obstacle --fix1`), with the current encoding, (i) and (ii). Run blind at `746a0e5`, opened together 2026-11-15 (D56).

**The gate:** with (ii), fix-case drops with strips of ≤ 3 cells cleared: **17 of 28, 60.7%** against ≥ 50%. **Passed.**

**Result, in the wording fixed above:** "With the landing-level view, an ideal fly at the real fly's average threshold clears 60.7% of the drops a jump at that moment can clear (17 of 28), against 0% with today's encoding and 0% with true optics. Fix 1 went on to fly runs." It fails every drop whose pits start two cells past the edge (0 of 11): the pits reach 39° only once the cube is already in the air.
- **If it passed:** "With the landing-level view, an ideal fly at the real fly's average threshold clears __% of the drops a jump at that moment can clear (__ of __), against __% with today's encoding and __% with true optics. Fix 1 went on to fly runs."
- **If it failed:** "With the landing-level view, an ideal fly at the real fly's average threshold clears only __% of the drops a jump at that moment can clear (gate: 50%). By the rule fixed beforehand, no fly runs were made with fix 1." Then why, from the per-obstacle table.

**Table (D56):**

| | current | (i) | (ii) |
|---|---|---|---|
| Fix cases, ≤ 3 cells (gate) | 0 / 23 | 0 / 23 | **17 / 28** |
| Fix cases, 4–5 cells | 0 / 2 | 0 / 2 | 1 / 3 |
| Fix cases, all | 0 / 25 | 0 / 25 | 18 / 31 |
| Controls | 9 / 9 | 9 / 9 | 11 / 11 |
| Jumps at plain step-downs | 0 (of 20 reached) | – | 0 (of 29 reached) |
| Levels completed (of 50) | 1 | 1 | 4 |

## P4. Fix 1, step 3: the fly on the training levels

*Only if the gate passed. Whole brain, R = 150 Hz, the record's settings. At most one revision, logged with its reason (D55 rule d).*

**Setup:** 50 frozen iteration-2 training levels × unfixed / fix 1 (ii) × seeds 0–2, 300 runs from `17a0ffe`, read from one report fixed before the runs and checksummed before opening (D57). Descriptive: D55's bar is the held-out suite (P5).

**Result:** "With the landing-level view, the real fly gets past the first drop-into-pits on 12 of 47 training levels, against 0 without it (12 better, 0 worse; p = 0.0005, descriptive). Per drop it reaches, it clears 54% (88% when the pits start at the edge), close to the ideal fly's 58%, and never when the pits start two cells out. It does no harm at plain edges or control drops." It completes no level in either arm: the runs it frees mostly die next at the double spike (deaths there 15 → 32), so median progress rises only from 11.8% to 13.5%.

| | unfixed | fix 1 (ii) |
|---|---|---|
| Levels past the feature (2 of 3 seeds, of 47) | 0 | **12** |
| Fix-case drops reached, cleared | 0 / 68 | **44 / 81** |
| … k = 0 / k = 1 / k = 2 | 0 / 30, 0 / 13, 0 / 25 | 30 / 34, 14 / 18, 0 / 29 |
| Control drops reached, cleared | 19 / 28 | 22 / 32 |
| Jumps on top of plain step-downs | 0 (of 53 reached) | 0 (of 68 reached) |
| Levels completed (of 50) | 0 | 0 |
| Median progress (per level) | 11.8% | 13.5% |
| Deaths at fix-case drops / double spikes | 68 / 15 | 37 / 32 |

**Not revised** (D57): the fixed fly came close to the ideal fly wherever it reached a drop.

## P5. Fix 1 on held-out levels (opened once, at the end of iteration 2)

*D55's bar, fixed before opening:*
- **Main measure:** gets past the feature (median run per level over 3 seeds), fixed fly against the unfixed fly, **sign test, p < 0.05**, on the 40 iteration-2 held-out levels. Progress and completions beside it.
- **No-harm check** (a check, not a test, since those levels have been seen): on iteration 1's 20 held-out cube levels, no significant drop, and worse on no more levels than better.

**[after opening]** better / worse / tied levels, p; the no-harm result.
- **If both pass:** "Fix 1 counts: on levels it was never designed on, the fly gets past the drop more often (__ better, __ worse, __ tied; p = __), and it does no harm on the levels of Part 1."
- **Otherwise:** "Fix 1 doesn't count by our bar: [which part failed]." Reported as fully as a pass.

## P6. Fix 2: close obstacles

*Fixed by fix 2's design note before the check ran. No brain.*

- **The spread-aware ideal fly** (thresholds drawn per approach from the fly's own spread, 37.1 ± 7.3°), on the iteration-2 training levels, current encoding / with fix 1 (ii): double spike cleared **48% / 51%**; triple spike 0% / 0%; spike, 1 cell, spike 0% / 0%; spike, 2 cells, spike 54% / 55%; spike, 3 cells, spike 96% / 98%. No level is completed by at least half its draws at 37.1° (D56).
- **The margin, recorded before the shifted-mean sweep was read:** noise **0** levels, so N = **3**.
- **The shifted means:** current encoding, best 46° at +1 level (fails N); with fix 1 (ii), best 50° at +7 (passes N). **Decided after seeing this (D56; the rule hadn't said which encoding governs): (a) for now**, since fix 1 hasn't yet passed its held-out bar; (b) may be raised again only if it does. Both readings reported.
- **The decision:**
  - **(a) Report it as a limit** (the default): "**[Shannyn's agreed wording]** Close groups of obstacles need an aimed jump. The Giant Fiber escape fires at a size threshold with a natural spread and doesn't aim, so the fly clears a double spike only when its threshold falls on the late side of its spread, and can't clear triple spikes or close pairs at any threshold measured in real flies. We report this as a limit of a one-shot escape reflex in this game."
  - **(b), only if the best shifted mean beat 37.1° by at least N levels:** a labelled variant, *"a late-threshold fly, inside the range measured in real flies"*, with its own design note, reported second, held to D55's bar. Never the fly of record.

## P7. Fix 3: the ship

*Only if fixes 1 and 2 let the cube reach a ship section. A new output rule, argued on its own merits (D55). If no run reaches a ship section, this section says so and stops.*

**No run reached a ship section, so fix 3 stops here (D59).** Part 1's furthest Stereo Madness run reached 10.9%, short of the first ship portal (~30%); the iteration-2 levels are cube only; and the double and triple spikes, which come before the ship, stay a limit (D56, D58). Testing the ship on ship-only levels instead would have changed this condition after seeing the cube results. The ship's own limit stays Part 1's finding (D53: DNp22 can't fire fast enough to descend); fixing it would need a new output rule, and is named as future work in the discussion.

## P8. Stereo Madness, new seeds

*Only how far the fly gets; never used to judge a fix. Seeds from 100 onwards, N fixed before each set and agreed by both of us (D55).*

**[before running: N, seeds, settings]** **[after the runs]** completed __ of N; median progress __%; where runs ended, by place. **Milestones,** each reported as reached or not: past 10.9% (Part 1's furthest); the first ship portal (~30%); the first ship section cleared; a complete run.

Read against Shannyn's prediction (fix 1's note): fix 1 alone leaves the median at ~9.2%, because 7 of 10 record runs die at the double spike before the pits.

## P9. Predictions, scored

Hit or miss each, by the rules in the notes that hold them, no partial credit.
- Fix 1 (`fix1_design.md`, 8 predictions): after step 2, **6 of 6 scored are hits**; 7 and 8 (held-out, Stereo Madness) **[later]** (D56).
- Fix 1, step 3 (`fix1_design.md`, 7 predictions): **7 of 7 hits** (D57). Two were close: the fixed fly's share cleared (54.3%, near the top of its 25–55% range, and below the ideal fly's 58.1% but not by a margin that means anything), and levels completed (a hit by its wording, 0 and 0; its reasoning expected a few completions with the fix, and there were none, because the runs it freed died next at the double spike).
- Fix 2 (`fix2_design.md`, 6 predictions): **5 hits, 1 miss** (prediction 5: no threshold beats 39° on the current encoding), scored on the current encoding by D56's decision; with the (ii) reading, 5 would be a hit and 6 a miss.

## D2. Discussion

**[Shannyn]** leads; outline only, written before any iteration-2 result:
1. **What the interface was hiding:** how much of Part 1's wall was ours, not the fly's.
2. **Foresight vs timing:** what it means that our code supplies the prediction and the fly only the moment (fix 1).
3. **Spread, not threshold:** the double spike as a property of an escape reflex in a timing game (fix 2).
4. **What still needs a new mechanism:** landing onto things (slabs), aimed jumps (triple spikes, close pairs), graded descent (the ship).
5. **What we'd do next:** **[Shannyn / Jacob]**, including option B for gaps (showing the edge) and the long-mode take-off.

   **[Jacob's draft for item 5, the engineering side; Shannyn to edit and add the biology]** Each item is something iteration 2 showed needs a new mechanism or a new readout, not another interface tweak:
   - **Gaps the fly can't see coming (k = 2), and gaps in general: option B.** Fix 1 shows pits that start at the platform's edge, but not pits two cells out, which reach threshold only once the cube is falling (0 of 29, D57). Walking flies judge a gap's width by sight, most likely from the parallax motion of its far edge rather than from looming, and they cross it by climbing, not jumping (Pick & Strauss 2005). A gap pathway would need its own input encoding and output rule.
   - **Aimed jumps: triple spikes and close pairs.** No threshold a real fly shows clears them in one jump (D56), and the real fly clears the double spike at the rate its timing spread predicts (48%, D57). Showing a spike group from its far end (fix 2 (e)) would lift the double spike to ~96% on geometry alone, but it was declined because it means our code aims the jump (D58). A real answer needs a mechanism that plans a trajectory, which a one-shot escape reflex doesn't have.
   - **The long-mode take-off.** A slower take-off with the wings raised first, which can happen without the Giant Fiber, and which slower looms favour (von Reyn et al. 2014). Using it needs a readout from descending neurons that aren't yet mapped for this behaviour, and a new output rule.
   - **Graded descent in the ship.** DNp22 can't fire fast enough to bring the ship down to lower openings (D53). No run reached a ship section in iteration 2, so fix 3 stopped (D59). A ship fix needs a new output rule, tested on ship levels with its own condition fixed before it runs.
   - **Landing onto things (slabs).** Objects the cube lands onto stay invisible (agreed 2026-10-31). Landing is a different behaviour from escape and would need its own input.
   - **Engineering, for any of these:** whole-brain runs take ~11 minutes per full level, so 300 runs take a night. The subcircuit plays cube levels identically (D52) and is several times faster. It could carry larger N for cube-only work once each new input or readout is checked on it. Every fix kept the same discipline: a design note, predictions, a gate checked without a brain, then fly runs. That's what let us tell our encoding's limits from the fly's.

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
