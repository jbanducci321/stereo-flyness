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
- **What this does and doesn't show:** the model *can* carry the signals; it isn't evidence the fly can play.
- **Biologically:** the escape pathway's fast, reliable response matches its structure: LC4 and LPLC2 are the Giant Fiber's main direct visual inputs (Ache et al. 2019), so one synapse separates our input from the readout. In the steering pathway, "up" giving exactly zero and suppressing "down" is the model's version of VS cells' motion opponency, where upward motion hyperpolarises them through an inhibitory interneuron (Mauss et al. 2015). The model's VS cells can't show a hyperpolarisation as spikes, only as fewer of them, so "zero" is as far as it can go.

## R2. The untuned fly plays the cube (Step 2)

Source: D48, `docs/notes/step2_report.md`.
- **6 of 60 runs completed, all on easy levels; mean progress 29%** (20 held-out levels × seeds 0–2, final subcircuit, R = 150 Hz).
- **Further than random pressing on 18 of 20 levels** (against the mean of 10 random draws per level). On the other 2, the first object is a raised slab, which kills every player including the ideal 39° fly.
- **How it dies:** mostly early jumps (d1); most of the rest are the encoding's limits (things it can't see, D47).
- *Figure R2:* progress per level: fly, never press, random presses, ideal 39° fly (`results/figures/R2_cube_progress.png`).
- **Early jumps and the real fly's threshold:** closed loop, the model's first Giant Fiber spike comes at 37.1 ± 7.3° (without carry-over), on the calibrated ~39° and **less variable than a real fly** (model s.d. 8.5° open loop, D46, against ~14° measured in flies). So the early jumps aren't the model misbehaving: they come from the low half of a normal, fly-like spread, and spike rows punish anything early. A real fly, with its larger spread, would be expected to jump early more often, not less. In real flies the threshold isn't a fixed angle either: the Giant Fiber sums looming size and speed (Ache et al. 2019), so its timing depends on the object's size-to-speed ratio. Every obstacle here approaches at the same speed, which is why one angle describes it well.

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
- **Relay plus threshold, and what the rest adds:** the 293 direct LC4/LPLC2 → Giant Fiber connections (19.9% of its input) are enough on their own to make the cube jump and to fly the easy levels. So "does play need the specific wiring?" has two answers. **The direct route is needed** (networks without it never jump), but that alone is close to trivial. **The rest of the real wiring changes *when*:** it brings the first spike ~10° earlier, from 46.5° to 36.6°, close to the real fly's ~39°. The lesions point to where that comes from: silencing the 12 excitatory partners (E5c) moves the first spike to ~100°, so extra excitation through partners beyond the direct inputs is what pulls the Giant Fiber to threshold sooner. This shift makes the model more like the real fly and, at 150 Hz, worse at this game; the two shouldn't be confused.

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
- **The descent limit is ours, not the fly's:** DNp22 firing at ~110 Hz is an ordinary rate for a spiking neuron (real DNOVS2 rates rise ~8–9 Hz per mV and by ~25 Hz in flight; Suver et al. 2016). The limit comes from our rule turning each spike into one 240 Hz tick of "release". A real fly doesn't steer altitude with a binary button: descending neurons adjust wing-stroke amplitude and timing gradually, through many neurons at once. So R6 says nothing about how well real flies descend.
- **Why the ship is the weaker claim:** (1) **our code does the steering** (where the opening is, and the speed to reach it); the fly only stabilises; (2) **DNOVS neurons encode body rotation**, and we use them for climbing and falling; (3) the model has no gap junctions or ocellar input, both prominent in this pathway in real flies. **What does stand:** with the fly's own stabilising term (B), the ship flies far better than without it (C, p < 0.001); with the brain, C is no better than random holding. So the fly's motion pathway does real work here, within our framing.

## R7. Switching modes works (Step 6, mixed levels)

Source: D54, `results/mixed_check/` reports.
- **Held-out mixed levels:** 60 of 60 runs, **25 mode switches, 0 mismatches** (mode, output rule, input encoding). Fly-driven, so later portals were reached only when the fly got there.
- **Bot-driven training levels,** every portal crossed: 50 of 50 runs, **105 switches, 0 mismatches.**
- **Described:** our input to each mode is off whenever that mode isn't shown, but LPLC2 still fires in ship sections through ~27,000 synapses from the ship's T4/T5, and so the Giant Fibers fire there too. The game ignores them in ship mode; the replay shows them as the model's activity.

---

## R8. Stereo Madness (Step 6, the final test)

*Everything in this section is fixed by D54 before any run. Order: the record first, the 50 Hz variant second, corrected signs alongside. Nothing below changes after the runs except the blanks.*

**Setup (fixed):** whole brain; N = 10 runs per variant, seeds 0–9; ship design B at R_ship 150 Hz, untuned; blind runs (D33); opened together, in one sitting (D54). Of Stereo Madness, only its length (26,384 units, ~85 s) was read before the runs; never its layout (D7, hard rule 5).

### R8.1 The headline: the fly of record (150 Hz, original signs)

Completed **0 of 10; median progress 9.2%** (quartiles 9.1–9.2%, range 3.8–10.9%).[^extra]
- Per run: every run ended in the first cube section (of 5), and none reached a ship section (0 of 3 reached, 0 passed).
  - 7 runs (seeds 0, 1, 2, 4, 5, 7, 9) died at the double spike, at 9.1–9.2%.
  - 2 runs (seeds 6, 8) died in the pits after the raised platform, at 10.9%.
  - 1 run (seed 3) died at a spike, at 3.8%, after an early jump.
- Deaths by section: cube **10**, ship **0**. Stuck runs: 0.

[^extra]: Deviations from D54, listed in its result. After the opening, 90 further runs with the record's settings (seeds 10–99), not pre-specified, were run at the same commit (e72c2d7): 0 of 90 completed, the furthest reached 10.9%, and every death was at one of the places above. They aren't part of the result; the headline is the pre-registered 10. Where the runs died was looked at before the report was opened, and the report wasn't opened in one sitting. Stereo Madness is now spent as a held-out test.

### R8.2 The tuned variant (50 Hz), reported second

Completed **0 of 10; median 6.5%** (quartiles 6.0–6.5%, range 6.0–10.9%). All 10 ended in the first cube section: 9 in the pits after a block (seeds 0, 1, 5, 8 at 6.0%; 2, 4, 6, 7, 9 at 6.5%), 1 (seed 3) in the pits after the raised platform at 10.9%. Stuck runs: 0. Always labelled: *a tuned variant, outside the range measured in real flies* (D50). Whichever does better, the headline stays R8.1.

### R8.3 Corrected signs (sensitivity check)

Completed **0 of 10; median 9.2%** (quartiles 9.1–9.2%, range 3.8–10.9%), every seed ending where the record's did. Stuck runs: 0. Reported alongside, never as the result (D28).

### R8.4 Shannyn's dated predictions (`docs/notes/step6_predictions.md`)

Scored by her rules, a hit or a miss each, no partial credit:

| # | Prediction | Hit or miss | From the report |
|---|---|---|---|
| 1 | No variant completes Stereo Madness | **Hit** | 0 of 10 completed in each variant |
| 2 | 50 Hz gets further than the record (median) | **Miss** (6.5% vs 9.2%) | Medians: 50 Hz 6.5%, record 9.2% |
| 3 | Corrected signs play exactly like the record in cube sections | **Hit** (10/10 identical; no run reached a ship section, so it covers whole runs) | "Identical for every seed: yes" (10 of 10 seeds) |
| 4 | ≥ 6 of 10 record runs end in a cube section | **Hit** (10/10) | 10 of 10 ended in a cube section |
| 5 | Every record ship-section death is on an object above | **Not scored** (no ship-section deaths) | 0 record ship-section deaths (not scored if none) |
| 6 | At least one stuck run across the 30 | **Miss** (0 stuck) | 0 stuck of 30 |

**Total: 3 hits, 2 misses, 1 not scored** (scored by Shannyn, 2026-11-15).

### R8.5 The showcase replay

The record run whose progress is closest to its median, ties to the lowest seed (picked by rule, D54): **seed 5, 9.2%.** Video: `results/replays/showcase_record_seed5.mp4` (Stereo Madness replays aren't committed, D9). Optional, captioned "the furthest of 10", never as the headline: **seed 6** (10.9%; tied with seed 8, lowest seed).

### R8.6 Context only: the bot

The search bot completes the level in our engine: it's playable, which says nothing about what a fly should do.

---

## D. Discussion

**[Shannyn]** leads. Points 1–4 and 6 are drafted from R1–R7, before the Stereo Madness results were read into them; point 5 waits for R8.
1. **What the connectome does here:** the escape circuit's wiring sets *when* the jump happens (R4); random wiring never jumps. The direct looming → Giant Fiber route is enough to jump at all; the rest of the real wiring moves the first spike to ~37°, near the real fly's ~39°. That timing is the clearest thing the connectome contributes to play, and it emerges from the wiring: we calibrated one dial, not the timing of each jump.
2. **What our code does:** looming, collision course, the patch, the output rules and mode switching are ours (README "the fly vs our code"). The fly never "decides to play".
3. **Threshold, not skill:** in the cube, firing later helps at 150 Hz (R3, R4), so better play isn't more fly-like play. The game rewards a later jump than the escape reflex is built for. A real Giant Fiber escape is meant to get the fly airborne before a predator arrives, not to clear a row of spikes, so a calibrated fly playing "too early" is the expected result of putting an escape reflex into a timing game.
4. **The ship's asymmetry** (R6): a limit of our output rule against the game's physics, not evidence about real descending control. The positive finding is that the fly's own stabilising term makes steering work: a wide-field motion stabiliser (VS cells' role) is needed, but can't navigate by itself (the failed first draft).
5. **Stereo Madness:** **[after the runs]**, read against R2 and R6 and the predictions, never re-explained after the fact.
6. **What we'd do next:** **[Shannyn / Jacob]**
   - **A ship output rule argued on its own merits,** e.g. reading DNp22's rate as a graded command, as real descending control is graded.
   - **Gap junctions,** which the escape and steering circuits both use.
   - **Adaptation and noise,** our untested guess for the stuck state.
   - **Edge and gap vision:** real flies judge gaps from parallax and set altitude from edge position, through circuits not yet mapped; showing these to the model would replace parts of our code with the fly's own.

## L. Limitations

Kept in one place, from the README ("Limits of the model", "Choices we made that happen to help the fly") and D53's ship limits. **[Shannyn]** draft; nothing is dropped from the README list.

**The model**
- **Brain only:** no ventral nerve cord, so "the Giant Fiber spiked" stands in for "the fly jumped".
- **Only the fast escape** is modelled; real flies also escape through slower pathways without the Giant Fiber.
- **No gap junctions,** which both the escape and steering circuits use.
- **Predicted transmitter signs** (Eckstein et al. 2024), some wrong; T4/T5 is tested both ways and the original is the result of record.
- **No behavioural state** (no octopamine): the model is neither resting nor flying.
- **No adaptation or noise,** our guess for why it sometimes gets stuck (~0.2% per simulated second), flagged and counted.
- **Unrealistic firing:** the Giant Fiber fires at 100–200 Hz while driven, where a real one fires once or twice; the jump rule uses only the first spike.
- **Spiking VS cells;** real ones signal mostly with graded voltage.
- **No ocellar input,** the largest input to DNp20 and DNp22 in v783.

**Our code, not the fly**
- **We stimulate looming and motion detectors directly,** so looming detection, direction selectivity and our collision course come from our code.
- **Only objects on a collision course at the cube's height loom;** objects it lands onto are invisible (about a third of an ideal fly's deaths, D44, D47).
- **Which LC4/LPLC2 neurons an obstacle drives is approximated** from shared inputs, not real visual-field positions.
- **The ship's steering is ours:** our code finds the opening and the speed to reach it; the fly stabilises.
- **DNOVS neurons encode rotation;** we use them for climbing and falling.
- **The ship's button is binary** and runs at 240 Hz, which caps how fast the fly can descend.
- **Our code switches between cube and ship.**

**The README needs two updates** (Step 8): the ship readout is now DNp22, not DNp20; and Stereo Madness was run 10 times per variant (D54), not once.

## README update (Step 8)

**[after the runs]** Status line → the Stereo Madness headline (R8.1 in its fixed wording), then the steps' one-liners from R1–R7. The plan list is marked done. The showcase video is linked, labelled as a replay of a simulation, our input shown separately from the fly's spikes (hard rule 10).

## Figures

Made by `scripts/make_figures.py` from the reports' own results files, into `results/figures/` (not committed: R8 is drawn from Stereo Madness, D9). Every level or run is a dot.

| Figure | Shows | Source |
|---|---|---|
| R2 | Cube progress per level: fly, never press, random, ideal | Step 2 report |
| R4 | Control networks and lesions against intact | Step 4 report |
| R6 | Ship: B, corrected, B90, C per level (median run); the ideal ship's totals in the caption, as it isn't saved per level | Ship baseline report |
| R8 | Stereo Madness progress per run, per variant, with section boundaries | `results/stereo_madness/runs.csv` |
| Replay | Stills from the showcase (seed 5) at its first jump and at its death; no run reached a ship section | `results/replays/showcase_seed5_*.png` |
