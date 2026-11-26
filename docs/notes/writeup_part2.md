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
- **Fix 3, the ship:** only after fixes 1 and 2, and only if they let the cube reach a ship section (D55). None did, so fix 3 stopped (D59, P7).

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

**Setup:** 40 iteration-2 held-out levels and iteration 1's 20 held-out cube levels × unfixed / fix 1 (ii) × seeds 0–2, 360 runs from `17d552e`, blind. Read from one report fixed before the runs, checksummed before opening, and scored by rules agreed beforehand (D61).

**Result, in the wording fixed above:** "Fix 1 counts: on levels it was never designed on, the fly gets past the drop more often (10 better, 0 worse, 29 tied; p = 0.00195), and it does no harm on the levels of Part 1."

The fixed fly clears 52.4% of the fix-case drops it reaches (44 of 84), against 0 of 62 unfixed; training gave 54.3%, and the ideal fly 58.1%. As in training:
- pits at or one cell from the edge are mostly cleared (80%, 68%);
- pits two cells out almost never are (1 of 25);
- the runs it frees mostly die next at the double spike (deaths 14 → 24).

On iteration 1's levels, fix 1 changed the input on 16 of 20 levels, and the fly passed the same obstacles on 19 (1 better, 0 worse). The fresh unfixed runs there match Part 1's tick for tick on 60 of 60.

| | unfixed | fix 1 (ii) |
|---|---|---|
| **Iteration-2 held-out (the test)** | | |
| Levels past the feature (2 of 3 seeds, of 39) | 0 | **10** |
| Fix-case drops reached, cleared | 0 / 62 | **44 / 84** |
| … k = 0 / k = 1 / k = 2 | 0 / 19, 0 / 26, 0 / 17 | 20 / 25, 23 / 34, 1 / 25 |
| Control drops reached, cleared | 18 / 21 | 23 / 26 |
| Jumps on top of plain step-downs | 0 (of 38 reached) | 0 (of 72 reached) |
| Runs / levels completed | 0 / 0 | 4 / 1 |
| Median progress (per level) | 10.9% | 11.7% |
| Deaths at fix-case drops / double spikes | 62 / 14 | 40 / 24 |
| **Iteration 1's held-out (no-harm check)** | | |
| Levels better / worse / tied (obstacles passed) | | 1 / 0 / 19 |
| Runs / levels completed | 6 / 2 | 6 / 2 |
| Median progress (per level) | 18.0% | 18.6% |

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

**Setup (D60, fixed before any run):** the fly of record with fix 1 (ii), ship B at 150 Hz, whole brain; N = 100, seeds 100–199; 100 runs from one clean commit, blind. The report was fixed before the runs, passed every check, and was checksummed before it was opened together (D62).

**With fix 1, the median run on Stereo Madness is unchanged at 9.2%, because the double spike still ends half the runs. No run dies in the pits any more, and 38 of 100 get further than any run in Part 1.** None reaches the ship.

| | Fix 1 (ii), seeds 100–199 | *Part 1, seeds 0–99 (context, D54)* |
|---|---|---|
| Completed | 0 of 100 | *0 of 100* |
| Median progress (quartiles; range) | **9.2%** (9.2–11.6%; 2.0–15.0%) | *9.2% (9.2–10.9%; 2.0–10.9%)* |
| Died at the double spike (x 2382–2418) | 50 | *60* |
| Died in the pits after the raised platform (x 2830.5–2899.5) | **0** | *35* |
| Died at the spike at x 3072–3078 | 37 | *0* |
| Died elsewhere | 13 | *5* |
| Past Part 1's furthest point (alive past x 2899.5) | **38** | *0* |
| Reached the first ship portal (~30%) / cleared the first ship section | 0 / 0 | *0 / 0* |

Part 1's runs are context, not a comparison: different seeds and no fix 1. Nothing here is tested for significance, and it judges nothing; fix 1 was judged on the held-out suite (P5).

**Reading:** fix 1 removes the pit wall on Stereo Madness as it did on the held-out levels, and moves the death forward. The median holds because the double spike comes first (P6). Fix 1 changed frames in 88 of 100 runs; the other 12 died before the first place it acts.

**Interpretation (D62; from the run logs, not a result):** the new wall, the spike at x 3072, is an encoding limit of the kind Part 1 already found (D44 (b)), not fix 1. The spike sits on the raised row the cube lands on, and our encoding shows it with its block as one 60-unit column, so it looms early and the fly jumps too soon (θ 27–40°, at gaps of 80–125). Checking it with the ideal fly would be an extra Stereo Madness run, which needs both of us to agree.

**Videos (local only, D9):** the run closest to the median (seed 109, 9.2%) and, captioned "the furthest of 100", seed 188 (15.0%).

## P9. Predictions, scored

Hit or miss each, by the rules in the notes that hold them, no partial credit.
- Fix 1 (`fix1_design.md`, 8 predictions): after step 2, **6 of 6 scored are hits** (D56); 7 (held-out: fix 1 passes the bar) **hit** (D61); 8 (Stereo Madness: median unchanged at ~9.2%, the furthest run past 10.9%) **hit** (D62: 9.2%, and 38 runs past Part 1's furthest point). **8 of 8.**
- Fix 1, held-out (`fix1_design.md`, 7 more predictions): **6 of 6 scored are hits, plus one check that held** (D61; with prediction 7, 7 of 7), scored by the readings agreed before opening (#88). One was a hit for a reason that turned out wrong: the iteration-1 levels tied (19 of 20, against ≥ 15), but not because fix 1 left them alone, as she reasoned; it changed frames on 16 of them without changing which obstacles the fly passed.
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

   **[Shannyn, 2026-11-18] The biology side of item 5.** The common thread: each next step should replace a piece of our code with a piece of the fly's own circuitry, rather than add more foresight on our side.
   - **Gaps.** Real flies do judge gaps by sight before trying to cross: walking *Drosophila* estimate a gap's width, most likely from the parallax motion of its far edge as they walk, and cross by climbing (Pick & Strauss 2005). So the honest model of a gap isn't a looming warning feeding an escape jump; it's a distance estimate from motion, read out as a decision to cross or turn back. Option B (showing the edge) would still be our construction. A pathway of the fly's own would need the neurons that carry that estimate, which aren't mapped for this behaviour yet.
   - **Close obstacles.** In our model the Giant Fiber's spike sets only *when* the jump happens; the jump itself is the game's fixed arc. Clearing a triple spike needs a jump aimed past a second obstacle, and nothing in the reflex we use plans a path over two objects. This is the clearest case where the game asks for something the circuit wasn't built to do, and we'd report it that way rather than look for a fix.
   - **The long-mode take-off.** This is the most promising biological next step. Flies whose Giant Fibers are silenced still take off, through parallel pathways that raise the wings first and have a lower threshold; in intact flies, which mode happens depends on when the Giant Fiber spikes relative to those pathways (von Reyn et al. 2014). Reading one of those pathways would give the fly a second, earlier and slower way to jump, chosen by its own spike timing rather than by us. It needs those descending neurons identified in the connectome first.
   - **Landing.** Flies use looming for landing as well as escape (cited in Pick & Strauss 2005), but it's a different behaviour with a different output. Making the objects the cube lands on visible would need a readout for that behaviour, not a change to the escape input.
   - **The ship.** DNOVS2 reports body rotation (Suver et al. 2016), not climbing or falling. A ship that descends well needs a readout whose real job is height control, not a faster version of ours.

## L2. Limitations (in addition to Part 1's)

*Shannyn, 2026-11-18, written before the Stereo Madness new-seed runs were opened. Nothing from the earlier draft is dropped.*

**How Part 2 was run**
- **It's exploratory.** We changed our interface after seeing where the fly failed in Stereo Madness (D55). The new levels were built from the game's physics, not Stereo Madness's spacings, but the problems they test were chosen because Stereo Madness showed them.
- **Stereo Madness was seen** before Part 2, so nothing in Part 2 is blind there. It shows only how far the fly gets (D60), never whether a fix works.
- **Fix 1 was judged once.** The iteration-2 held-out suite is now spent (D61), so there's no second independent test of it. Any further fix would need a third suite.
- **Iteration 1's held-out cube levels have now been run in Part 1 and again for the no-harm check,** which is why that check is a check, not a test (D55).
- **Three seeds per level.** Each level's result is the median of three runs. That's enough to judge levels against each other, not to say how often one fly passes one particular drop.
- **The sign tests on training levels are descriptive** (D57). Only the held-out test decides whether a fix counts.
- **One decision was made after seeing results.** Fix 2's rule didn't say which encoding governs option (b); we chose (a), report it as a limit, after the check (D56) and logged that. Both readings are reported.

**What fix 1 is, and isn't**
- **(ii) is our construction.** No fly's eye predicts a fall: from on top of a platform the pits peak at 7–14°, far below the ~39° threshold (option (i), true optics, reported beside it). Fix 1's frames are labelled in every replay.
- **Real flies don't cross gaps this way.** Walking flies judge a gap's width by sight, most likely from the parallax of its far edge, and cross it by climbing, not by an escape jump (Pick & Strauss 2005). So fix 1 shows that the fly's escape reflex can *time* a jump over a gap once our code supplies the warning; it doesn't show how flies handle gaps.
- **Fix 1 works only when the pits start at or near the platform's edge.** When they start two cells out, the pits reach the threshold only after the cube has walked off, where it can't jump: 1 of 25 such drops cleared on held-out levels, 0 of 29 in training (D57, D61). This is a limit of a jump triggered by a fixed threshold, not something fix 1 can reach.
- **The fix-case label is our engine's walk-off,** not a measure of how a real fly would fall.
- **A limit of our encoding that Part 1 already found is now the next wall.** A spike sitting on a block is shown together with the block as one 60-unit column, so it looms early and the fly jumps too soon (D44, kind (b)). On Stereo Madness it ended 37 of the 38 runs that got past the pits (D62; from the run logs, not a separate check). We didn't fix it: it showed up on Stereo Madness after fix 1 had been judged.

**What the fly still can't do**
- **Close groups of spikes.** The real fly clears a double spike about half the time (48%), the rate its timing spread predicts, and never a triple spike or a 1-cell pair (D56, D57). A one-shot escape reflex fires at a size threshold and doesn't aim, so this is a property of the reflex in a timing game, not of our interface. We declined to move where a spike group appears to start, since that would be our code aiming the jump (D58).
- **Landing onto things stays invisible** (agreed 2026-10-31), so getting onto a slab is a separate limit fix 1 doesn't touch.
- **The ship wasn't revisited.** No run reached a ship section, so fix 3 stopped (D59), and the ship's limit is Part 1's (D53).

**Comparing with Part 1**
- **Iteration-2 "easy" isn't Part 1's "easy":** the new levels' press windows are as short as 8–21 ms, so tiers aren't compared across the two parts.

## Videos and figures

- Every Part 2 video and figure carries the exploratory label (D55), and replays label the landing-level frames: "θ shown from landing level, our construction".
- Figures go to `results/iteration2/figures/` (not committed).
