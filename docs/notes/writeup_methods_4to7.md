# Write-up: methods (draft, Steps 4–7 setup)

*Jacob, 2026-11-10. Continues `docs/notes/writeup_methods.md` (Steps 0–3), in the same way: a first draft for Step 8, from settled decisions only, for Shannyn to rewrite, cut or reorder. **No results:** the Step 4 and Step 7 reports are unopened (opened as two independent reads, 15–16 Nov), and the ship design isn't fixed. Every number is copied from the decision log, with its source. **[Shannyn]** marks outlines where the biology framing is hers.*

## 8. Does play depend on the real wiring? Controls and lesions (Step 4, D51)

All rules below were fixed before any Step 4 run (D51), and amended once before the second night, before any game result was read.

**Question.** 293 direct LC4/LPLC2 → Giant Fiber connections carry 19.9% of the Giant Fibers' input, so the fly could be little more than a relay plus a threshold. Does its play depend on the rest of the wiring?

**Setup.** The whole brain (D36), R = 150 Hz (D50), the Step 2 encoding (D41–D47), original signs. No recalibration for any control or lesion. The 20 held-out cube levels at seeds 0–2: 60 runs per condition, 11 conditions, 660 runs in all. The reference is the intact whole brain on the same levels and seeds. Every run records its connectivity file, its SHA-256 and any lesion.

**Control networks** (instance *k* at Poisson seed *k*, 3 each):
- **(a) Degree-preserving shuffle:** every neuron keeps its number of inputs and outputs; who connects to whom is randomised.
- **(b) Shuffle keeping the looming → Giant Fiber connections:** as (a), with the 293 connections held out of the shuffle and no new ones created.
- **(c) Relay-only network:** only those 293 connections.
- **(d) Random network:** the same neurons and number of connections, each neuron's sign kept, synapse counts drawn from the real distribution.

**Lesions** (whole cell types, both sides, silenced): **E5b**, the Giant Fiber's inhibitory input partners (22 neurons), and **E5c**, its excitatory partners (12 neurons), the pathway tests' E5b and E5c lesions (kept in D35). Each has two controls, 3 draws each:
- **a random-lesion control:** each lesioned neuron replaced by a random neuron of the same sign with total output within ±10% (never a Giant Fiber, LC4/LPLC2 or lesion-set neuron);
- **a recruited-matched control** (added before night 2): the same, but also matched on whether the neuron fired in the 70 recruitment runs of D46. So it silences as many "involved" neurons as the lesion (13 of E5b's 22, 10 of E5c's 12). Added because open loop, every random-lesion draw was identical to intact: the random neurons took no part in the loom response.

**Code check, before any run:** LC4/LPLC2 silenced on 2 held-out levels must give exactly 0 Giant Fiber spikes and 0 presses.

**Judging** (D51):
- **Every comparison:** per level, the median run across seeds or instances; D48's "equal"; two-sided sign test, "better" or "worse" only at p < 0.05.
- **"It's a relay" (b, c):** all three must hold: progress shows no clear difference; the pooled median first-spike θ (without carry-over) is within the largest difference between two intact seeds; the (d1) death share passes the same bar.
- **"It's those neurons" (E5b, E5c):** differs from intact **and** from its recruited-matched control, p < 0.05, same direction.
- **Holm correction** over a family of 12 sign tests named in advance; each is also reported on its own.
- **A fixed reading:** if (b), (c) or E5c plays *better* than intact, it's read as the late-threshold effect seen in Step 3 (D49), not as "a relay plays better" or "the lesion improved the fly".
- **Predictions** were written before any run (`step4_proposal.md` §5) and are reported as hit or miss.

**Not run, and why** (D51): silencing the Giant Fiber (our output reads its spikes, so it would only test our rule; real flies still escape through the long-mode pathway, von Reyn et al. 2014), and LC4 or LPLC2 alone (with both calibrated together, it acts like lowering R).

**[Shannyn]** The biology of each control and lesion: what a shuffle keeps and destroys, why the inhibitory and excitatory partners, and what "specific" can and can't mean with a recruitment-based "involved".

## 9. Whole brain against the subcircuit in closed loop (Step 7, D52)

Fixed before the Step 4 report was opened (D52).

**Question.** Does the final subcircuit (D46) play the cube like the whole brain on unseen levels, with the fly driving?

**Two pairings, 60 pairs each** (the 20 held-out cube levels × seeds 0–2; θ_full = 200°, R × f, collision course; the same level and Poisson seed within a pair):
- **150 Hz (the fly of record):** Step 2's subcircuit runs against Step 4's intact whole-brain runs. No new runs.
- **50 Hz (the labelled variant, D50):** Step 3's held-out subcircuit runs against 60 new whole-brain runs at 50 Hz, run blind.

**Only the network differs** within a pair: the code changes between the commits involved were checked to touch nothing the runs use, and every setting recorded in each run matches within its pair.

**The bar, for each pairing: identical games in ≥ 57 of 60 pairs.** A pair is identical if the cube's position and vertical speed (x, y, vy) are exactly equal after every tick and both runs last the same number of ticks. The game is deterministic, so there's no tolerance. It's judged on the game, not the press log: a press in mid-air does nothing, so an extra mid-air press isn't a difference. For every pair that splits we report where, what was in view, which network pressed, and whether the outcome changed.

**Described only:** per obstacle approach, the first press within ±1 frame, up to each pair's first split; per level, the sign test; progress, completions, death classes, first-spike θ, stuck runs and presses per second.

**Fixed readings:** a pass means the subcircuit's results stand for the whole brain at that rate, in this setting (the cube, with our encoding). A fail means they stay valid as subcircuit results, and nothing is rerun.

## 10. Opening blind results

Held-out results are never looked at until the whole batch has finished and the analysis code is ready and checked (D33). Report scripts print only their checks (every run complete, every run replays exactly from its logged inputs, clean commits) until the results are opened.
- Steps 2 and 3 were opened together.
- **Steps 4 and 7 are opened as two independent reads** (agreed 2026-11-10): each of us reads the reports alone, in a fixed order, and writes a verdict on every fixed question and prediction before we compare (`docs/notes/opening_verdicts.md`). Differences are settled against the fixed rules.

## 11. The closed loop in any mode, and the ship (Steps 5–6)

**Mode switching.** Stereo Madness has cube and ship sections. Each game mode has its own *controller*: which neurons its encoding drives, and how spikes become the button (`interface/modes.py`). On each tick, the controller for the mode the player is in sets its inputs and every other mode's inputs to 0, and the same controller's rule reads that frame's spikes. A portal switches the mode with the same one-tick delay as every press (D40). Cube runs through this loop match the Step 2–4 loop exactly.

**The ship interface: not fixed yet.** Shannyn's draft (`docs/notes/ship_proposals.md`) used image motion computed from the level's geometry, driving the vertical motion detectors T4/T5, read out at DNp22 (≈ DNOVS2; any spike releases the button). Its first check, with no brain, failed: neither "ideal ship" (the encoding with a fixed rule in place of the brain) completed any of the 50 training ship levels (`docs/notes/ship_ideal.md`). The design is being revised; this section is rewritten once it's logged.

**[Shannyn]** The ship pathway's biology (VS cells, DNOVS, what the model can and can't carry: no gap junctions, no ocellar input, spiking VS cells), once the design is fixed.

## 12. The replay viewer and brain panel (D19, D25, R3)

- **Every closed-loop run logs every tick:** the game state, our input values, the watched neurons' spikes and every neuron's activity counts, with the run's settings, seed, commit and connectome checksum (hard rule 10).
- **The viewer** replays a run at 60 fps (every 4th tick drawn) from its log, with pause, scrub and slow motion, and exports video (pygame and ffmpeg, D25). It always says it is a replay of a simulation, and says who was driving (the fly or the bot).
- **The brain panel** (Shannyn's design, R3) runs in three columns, in the order the signal flows:
  1. **What we show the fly** (white/grey): our input, labelled as computed by our code from the game, never the fly's activity;
  2. **The fly's escape neurons** (amber): both Giant Fibers, their spike rasters and the presses on the same time axis;
  3. **The rest of the brain** (amber): neurons firing per tick (not counting the ones we stimulate) and the stuck-state share.
- **Nothing is smoothed, interpolated or rescaled.** Numbers shown "now" are sums over the ticks since the previous drawn frame (4 ticks), labelled as such.

## 13. Reproducibility

- **Environment:** Python with `uv` and its lockfile (`uv sync`); Brian2 needs a C++ compiler (on Windows, the Visual Studio Build Tools).
- **Data:** `scripts/download_data.py` fetches the v783 connectome files (~104 MB) and checks each against a SHA-256. The cell-type annotations are pinned to flywire_annotations v3.1.0 and checksummed.
- **Every run** records its git commit (marked `-dirty` if the tree had changes; reported runs are all on clean commits), its seed and settings, and its connectivity file's SHA-256. Every run replays exactly from its logged inputs, and every report checks this before comparing anything.
- **Levels:** generated from fixed seeds (`configs/level_suites.toml`), bot-validated, with training and held-out suites from separate seed ranges. Stereo Madness is never used for tuning and only runs behind its own flag, blind (D7).
- **Commands:** *(to add: the exact command for each step's runs and report.)*

## Still to add

- Step 4 and Step 7 **results**, after the opening (16 Nov).
- **Step 5:** the ship design, its checks and its baseline, once logged.
- **Step 6:** Stereo Madness (N, seeds and the network, fixed before any run) and the showcase replay rule.
- The exact commands in §13.
