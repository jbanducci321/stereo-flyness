# Write-up: results and discussion (skeleton, Steps 0–7)

*Jacob, 2026-11-14. The second half of the Step 8 write-up; the methods are in `docs/notes/writeup_methods.md` (§1–7) and `docs/notes/writeup_methods_4to7.md` (§8–13), and aren't repeated here. **Written before any Stereo Madness run:** its sections are empty, with their order and wording fixed now so the results can't shape how they're framed. Every number in the finished sections is copied from the decision log or the note it cites, with its source; nothing here is new. **[Shannyn]** marks where the biology framing is hers (PROJECT_BRIEF §8: she leads biology, methods and limitations; Jacob engineering and reproducibility). **[after the runs]** marks what's filled in only after the Stereo Madness report is opened, as D54 fixes.*

**How to read every result below:**
- The headline is always the fly of record: the **untuned, calibrated fly** (R = 150 Hz, D50) on **held-out** levels, never the best run or a tuned variant.
- Every rule for judging a result was written down before the result was seen (D33). Where a result went against a prediction, it's reported as plainly as one that matched.
- "Completed" counts are per run unless they say "levels (median run)".

---

## R1. The pathways carry the game's signals (Step 0)

Source: `docs/pathway_results.md`, D39.
- **Escape** (LC4/LPLC2 → Giant Fiber): **GO.** It drives the Giant Fiber in every trial at every rate, within ~8–13 ms, and stops within ~3–13 ms of input off.
- **Steering** (T4/T5 → VS → DNp20), original signs: **GO.** "Down" drives VS cells and DNp20 in every trial; "up" gives exactly 0 and suppresses "down". Corrected signs: the same pattern, ~10–15% stronger.
- **What this does and doesn't show:** the model *can* carry the signals; it isn't evidence the fly can play. **[Shannyn]** one or two sentences on what the open-loop responses mean biologically.

## R2. The untuned fly plays the cube (Step 2)

Source: D48, `docs/notes/step2_report.md`.
- **6 of 60 runs completed, all on easy levels; mean progress 29%** (20 held-out levels × seeds 0–2, final subcircuit, R = 150 Hz).
- **Further than random pressing on 18 of 20 levels** (against the mean of 10 random draws per level). On the other 2, the first object is a raised slab, which kills every player including the ideal 39° fly.
- **How it dies:** mostly early jumps (d1); most of the rest are the encoding's limits (things it can't see, D47).
- *Figure R2:* progress per level: fly, never press, random presses, ideal 39° fly. **[to make]**
- **[Shannyn]** early jumps against the real fly's ~39° threshold and its variability (D46: first-spike s.d. 8.5° against 14° in the fly).

## R3. Tuning helps only by leaving the real fly's range (Step 3)

Source: D49, D50, `docs/notes/step3_report.md`.
- R tuned on 50 training levels picks **50 Hz**, which fires at an open-loop θ ~84°, **outside the range measured in real flies**.
- On held-out levels: **11 better, 4 worse, 5 equal; p = 0.118, no clear difference** (23 against 6 runs completed, described only).
- **So the calibrated 150 Hz fly stays the fly of record** (D50). 50 Hz is carried forward only as a labelled "tuned" variant, always reported second.

## R4. The play depends on the real wiring (Step 4)

Source: D51, `docs/notes/step4_report.md`.
- **Shuffled and random networks never jump:** both are worse than intact (0 better, 18 worse, 2 equal; p < 0.001, both survive Holm). Their Giant Fiber never fires, so they play exactly like never press (6.3%).
- **A relay alone plays *further*, by firing later:** the looming-kept shuffle and the relay-only network give identical results, 59.4% against 29.4% progress (24 of 24 easy runs completed against 6). Better at p = 0.013 alone, **not after Holm** (p = 0.129). They fire ~10° later (46.5° against 36.6°), so by D51's fixed reading this is the same late-threshold effect as Step 3, **not** "a relay plays better".
- **So the rest of the wiring mostly makes the Giant Fiber fire earlier,** close to the real fly's 39°, which at 150 Hz happens to cost progress.
- **Neither lesion is specific:** E5b and E5c show no clear difference against intact or their matched controls, although E5c moves the first spike much later (100° against 37°).
- **[Shannyn]** what the 293 direct LC4/LPLC2 → Giant Fiber connections (19.9% of its input) mean for "relay plus threshold", and why the rest of the brain pulls the threshold earlier.

## R5. The subcircuit stands for the whole brain (Step 7)

Source: D52.
- **60 of 60 games identical, tick for tick,** at 150 Hz and at 50 Hz (bar: ≥ 57 of 60 per rate).
- So every cube result above, run on the subcircuit, stands for the whole brain in this setting. Stereo Madness runs on the whole brain anyway (D54).

## R6. The ship: steering works, descending doesn't (Step 5)

Source: D53 and its result, `docs/notes/ship_baseline_results.md`.
- **Design B** (D53; Shannyn led the design): image motion from the ship's vertical speed against the speed needed to reach the target opening, ω_full 30°/s; any DNp22 spike releases, silence holds. Untuned R_ship = 150 Hz, on 20 held-out ship levels, median run per level:

  | | Levels completed | Mean progress |
  |---|---|---|
  | **B (record)** | **6 of 20** (5/8 easy, 1/8 medium, 0/4 hard) | **45.6%** |
  | B, corrected signs | 7 of 20 | 53.0% |
  | B90 (faster anchor) | 0 of 20 | 26.1% |
  | C (control, without the self-motion term) | 0 of 20 | 14.9% |
  | Ideal ship (no brain) | 14 of 20 | 81.4% |

- **B beats its control:** C is worse on 16 levels (p < 0.001). B90 is worse than B (p = 0.002). Corrected signs: no clear difference (better on 2, worse on 0); the original stays the version of record (D28).
- **Every control death is "too high"** (39 d_up, 0 d_down; 36 of the 39 hit an upper block's underside, 3 borderline).
- **Why:** holding pushes up at 0.5 g and releasing pulls down at only 0.32 g, so the ship needs ~61% releases to hold height. DNp22's ceiling (~110 Hz against 240 Hz ticks) allows at most ~67.5%, so it sinks at only ~−35 units/s. **R_ship can't fix this, and the output rule isn't changed after seeing it** (D53).
- **Shannyn's dated predictions:** 8 hits, 2 misses (one hit by the letter only).
- **[Shannyn]** DNp22's ceiling against the real fly's descending control; why the ship is the weaker claim (README limits).

## R7. Switching modes works (Step 6, mixed levels)

Source: D54 (once logged), `results/mixed_check/` reports.
- **Held-out mixed levels:** 60 of 60 runs, **25 mode switches, 0 mismatches** (mode, output rule, input encoding). Fly-driven, so later portals were reached only when the fly got there.
- **Bot-driven training levels,** every portal crossed: 50 of 50 runs, **105 switches, 0 mismatches.**
- **Described:** our input to each mode is off whenever that mode isn't shown, but LPLC2 still fires in ship sections through ~27,000 synapses from the ship's T4/T5, and so the Giant Fibers fire there too. The game ignores them in ship mode; the replay shows them as the model's activity.

---

## R8. Stereo Madness (Step 6, the final test)

*Everything in this section is fixed by D54 before any run. Order: the record first, the 50 Hz variant second, corrected signs alongside. Nothing below changes after the runs except the blanks.*

**Setup (fixed):** whole brain; N = 10 runs per variant, seeds 0–9; ship design B at R_ship 150 Hz, untuned; blind runs (D33); opened by **[D54: how]**. Of Stereo Madness, only its length (26,384 units, ~85 s) was read before the runs; never its layout (D7, hard rule 5).

### R8.1 The headline: the fly of record (150 Hz, original signs)

**[after the runs]** Completed **k of 10; median progress X%** (quartiles, range).
- Per run: where it ended (cube or ship section, and the object), and the ship sections reached and passed.
- Deaths by section: cube **[ ]**, ship **[ ]**.

### R8.2 The tuned variant (50 Hz), reported second

**[after the runs]** Completed **k of 10; median X%**. Always labelled: *a tuned variant, outside the range measured in real flies* (D50). Whichever does better, the headline stays R8.1.

### R8.3 Corrected signs (sensitivity check)

**[after the runs]** Completed **k of 10; median X%.** Reported alongside, never as the result (D28).

### R8.4 Shannyn's dated predictions (`docs/notes/step6_predictions.md`)

Scored by her rules, a hit or a miss each, no partial credit:

| # | Prediction | Hit or miss | From the report |
|---|---|---|---|
| 1 | No variant completes Stereo Madness | **[ ]** | |
| 2 | 50 Hz gets further than the record (median) | **[ ]** | |
| 3 | Corrected signs play exactly like the record in cube sections | **[ ]** | "Identical for every seed" line |
| 4 | ≥ 6 of 10 record runs end in a cube section | **[ ]** | |
| 5 | Every record ship-section death is on an object above | **[ ]** | (not scored if none) |
| 6 | At least one stuck run across the 30 | **[ ]** | |

### R8.5 The showcase replay

The record run whose progress is closest to its median, ties to the lowest seed (picked by rule, D54): **seed [ ], [ ]%.** Video: **[ ]**. Optional, captioned "the furthest of 10", never as the headline: **seed [ ]**.

### R8.6 Context only: the bot

The search bot completes the level in our engine: it's playable, which says nothing about what a fly should do.

---

## D. Discussion

**[Shannyn]** leads; outline only, written before the Stereo Madness results so its points don't follow them.
1. **What the connectome does here:** the escape circuit's wiring sets *when* the jump happens (R4); random wiring never jumps.
2. **What our code does:** looming, collision course, the patch, the output rules and mode switching are ours (README "the fly vs our code"). The fly never "decides to play".
3. **Threshold, not skill:** in the cube, firing later helps at 150 Hz (R3, R4), so better play isn't more fly-like play.
4. **The ship's asymmetry** (R6): a limit of our output rule against the game's physics, not evidence about real descending control.
5. **Stereo Madness:** **[after the runs]**, read against R2 and R6 and the predictions, never re-explained after the fact.
6. **What we'd do next:** **[Shannyn / Jacob]** (e.g. a ship output rule argued on its own merits; gap junctions; adaptation and noise for the stuck state).

## L. Limitations

Kept in one place, from the README ("Limits of the model", "Choices we made that happen to help the fly") and D53's ship limits (no gap junctions, no ocellar input, spiking VS cells, DNOVS rotation against the ship's translation, no behavioural state). **[Shannyn]** final wording; nothing is dropped from the README list.

## README update (Step 8)

**[after the runs]** Status line → the Stereo Madness headline (R8.1 in its fixed wording), then the steps' one-liners from R1–R7. The plan list is marked done. The showcase video is linked, labelled as a replay of a simulation, our input shown separately from the fly's spikes (hard rule 10).

## Figures (to make)

| Figure | Shows | Source |
|---|---|---|
| R2 | Cube progress per level: fly, never press, random, ideal | Step 2 report |
| R4 | Control networks and lesions against intact | Step 4 report |
| R6 | Ship: B, C, B90, corrected, ideal per level; the descent limit | Ship baseline report |
| R8 | Stereo Madness progress per run, per variant, with section boundaries | **[after the runs]** |
| Replay | Stills from the showcase at a cube jump and in a ship section | **[after the runs]** |
