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

**What each control keeps and removes.** In the fly, the Giant Fiber (DNp01) is the descending neuron of the fastest escape take-off, and its main visual drive comes from the looming-sensitive lobula columnar (LC4) and lobula plate–lobula columnar (LPLC2) neurons (von Reyn et al. 2014, 2017). The controls take that wiring apart in steps:
- **(a) The degree-preserving shuffle** keeps how many partners each neuron has (so hubs stay hubs) and destroys *which* partners. It asks whether the specific wiring matters beyond the network's statistics.
- **(d) The random network** also destroys each neuron's number of partners, keeping only the neurons, their signs and the total number of connections.
- **(b) The looming-kept shuffle** keeps the direct route from the looming detectors to the Giant Fiber and shuffles everything else. It asks whether the rest of the brain's specific wiring adds anything to that route.
- **(c) The relay-only network** keeps only the direct route. It shows what a pure relay plus the Giant Fiber's threshold can do.

**What they can and can't show.** (a) and (d) also shuffle away the 293 direct connections, so they can't separate "the specific wiring matters" from "the Giant Fiber needs its direct looming input": a network in which the Giant Fiber never fires fails either way. **The informative comparison is (b) and (c) against intact:** both keep the direct route, so any difference is what the rest of the real wiring contributes.

**Why these lesions.** The Giant Fiber's input partners include both excitatory and inhibitory cell types (the pathway tests, `docs/pathway_results.md`). Silencing the inhibitory partners (E5b) tests whether inhibition delays or sharpens the Giant Fiber's response; silencing the excitatory partners (E5c) tests whether they add to the drive from LC4/LPLC2. Whole cell types are silenced on both sides, as a genetic silencing experiment would target a cell type rather than single neurons.

**What "specific" can and can't mean.** A lesion counts as specific only if it differs from the intact brain **and** from a control that silences as many "involved" neurons, of the same sign and similar output. "Involved" means the neuron fired in the 70 recruitment runs (D46), not necessarily in the held-out games. So "specific" means: these cell types change play more than silencing an equal number of other active neurons does. It doesn't mean they are the only neurons that matter, and with 20 levels, small effects can't be told apart from none. A lesion can also shift the Giant Fiber's timing clearly while play shows "no clear difference", if the shift helps some levels and hurts others; timing and play are reported separately for that reason.

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
- **Steps 4 and 7** were opened on 2026-11-10 by Jacob's Claude Code session at our request, judging every fixed question against D51 and D52's rules; we both reviewed its verdicts. (Two independent reads had been planned, `docs/notes/opening_verdicts.md`; we chose this instead.)

## 11. The closed loop in any mode, and the ship (Steps 5–6)

**Mode switching.** Stereo Madness has cube and ship sections. Each game mode has its own *controller*: which neurons its encoding drives, and how spikes become the button (`interface/modes.py`). On each tick, the controller for the mode the player is in sets its inputs and every other mode's inputs to 0, and the same controller's rule reads that frame's spikes. A portal switches the mode with the same one-tick delay as every press (D40). Cube runs through this loop match the Step 2–4 loop exactly.

**The ship's pathway in the fly.** Flies stabilise flight using wide-field optic flow, the motion of the whole scene across the eye as the body moves.
- **T4 and T5** are the fly's elementary motion detectors, for bright and dark edges respectively. Their subtypes each prefer one direction: **T4d/T5d downward and T4c/T5c upward** motion (Maisak et al. 2013). In resting flies they respond most to a temporal frequency of ~1 Hz (30°/s for a 30° pattern); active states shift tuning toward faster motion (Strother et al. 2018).
- **VS cells** (vertical system; VS1–VS8 in the FlyWire annotation) are large lobula plate neurons that pool T4/T5 input across the eye and respond to vertical motion: excited by downward motion and inhibited by upward motion, the inhibition relayed by lobula plate interneurons (Mauss et al. 2015). Their receptive fields match the optic flow of body rotations, so they signal the fly's own rotation for stabilising gaze and flight.
- **DNOVS neurons** carry VS signals to the thorax. In *Drosophila*, DNOVS1 (our DNp20) doesn't spike and targets neck motor neurons; DNOVS2 spikes, is coupled to VS2 and VS3, and reaches the neck, wing and haltere motor regions (Suver et al. 2016). In v783, DNp22's numbered VS inputs are exactly VS2 and VS3 (plus VSm), so we identify **DNp22 as DNOVS2** and read the ship from it.
- **How real flies set altitude** (Straw et al. 2010): they track the *position* of horizontal edges, through a circuit nobody has identified, alongside wide-field stabilisation and expansion avoidance.

**The ship interface (D53).** Every choice here is ours, not the fly's.
- **What the fly sees:** image motion, computed from the level's geometry, in 37 viewing directions (every 5° of elevation, about the fly's interommatidial angle), seeing the nearest surface up to 600 units ahead, pooled as the mean. Downward pooled motion drives all T4d + T5d neurons and upward motion all T4c + T5c, on both eyes, at R_ship × f, with f = |ω| / 30°/s capped at 1.
- **The first draft failed, and we report it:** following the scene's motion pulls the ship toward any nearby surface. With a fixed rule in place of the brain it completed none of 50 training levels, either with all of the scene's motion or with only the motion from the ship's own climb and fall (`ship_ideal.md`). **A wide-field stabiliser alone doesn't navigate**, consistent with VS cells' role.
- **The design of record, B:** our code stands in for edge tracking. It finds the next opening ahead and the vertical speed v_req that reaches its centre. The fly is shown its own vertical motion **relative to** that speed: the motion term computed with (vy − v_req), zero when the ship is on course. **The fly stabilises; our code steers**, and the replay labels the target and v_req as our input.
- **Controls:** C, steering without the stabiliser (the term with −v_req only), and self-motion only, stabilising without steering. Each differs from B by one term.
- **Output:** any DNp22 spike in a frame releases the button on the next tick; otherwise it's held. One dial, R_ship, left untuned at 150 Hz.
- **Network:** the whole brain, original signs, with the T4/T5-corrected connectome as D28's sensitivity check.

**What the model can't carry** (stated with every ship result):
- **No gap junctions:** VS cells are electrically coupled to each other and to DNOVS neurons in the fly; the model has chemical synapses only.
- **No ocellar input:** ocellar neurons are the largest input to DNp20 and DNp22 in v783, and are never driven.
- **Spiking VS cells:** real VS cells signal mostly with graded voltage; in the model every neuron spikes.
- **Rotation, not translation:** DNOVS neurons encode body rotation, while the ship only climbs and falls. Using this pathway for altitude is our mapping.
- **No behavioural state:** the model is neither resting nor flying (no octopamine), so the 30°/s anchor from resting flies is a choice; a 90°/s active-state variant is reported second.
- **The output's speed limit:** DNp22 fires up to ~110 Hz, but the button runs at 240 Hz, and in the game a falling ship only speeds up its fall if released on more than ~61% of ticks. So the fly climbs fast but descends slowly (D53). This comes from our output rule meeting the game's physics, not from the fly.
- **Cross-talk to the escape pathway:** in ship sections, the Giant Fiber still fires through T4/T5 → LPLC2 → Giant Fiber (LPLC2 gets ~27,000 synapses from T4/T5). The game ignores it in ship mode, and the replay shows it as the model's own activity.

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
- **Commands** (from each script's usage notes; `--quiet` marks blind runs, which print only progress and stuck flags). `$LEVELS` is the 20 held-out cube levels: `ls results/levels/held_out/cube-*.json | grep -v meta`, names only.

| Step | What | Command |
|---|---|---|
| Setup | Environment, tests, data | `uv sync`; `uv run pytest`; `uv run python scripts/download_data.py` |
| 0 | Target neurons (v783) | `uv run python scripts/find_target_neurons.py` |
| 0 | Corrected-sign copy (D27) | `uv run python scripts/make_corrected_connectivity.py` |
| 0 | Pathway tests and analysis | `uv run python scripts/run_pathway_tests.py --jobs 4`; `uv run python scripts/analyse_pathway_tests.py` |
| 1 | Level suites | `uv run python scripts/generate_levels.py` |
| 2.5 | θ_full calibration (whole brain) | `uv run python scripts/calibrate_theta_full.py --network whole_brain --rate-scaling --trials 10` (flat R: without `--rate-scaling`) |
| 2.6 | Recruitment, subcircuit, validation | `uv run python scripts/run_recruitment.py --jobs 4`; `uv run python scripts/extract_subcircuit.py configs/subcircuits/<name>.toml`; `uv run python scripts/validate_subcircuit.py <name>` |
| 2 | Baseline, per seed 0–2 | `uv run python scripts/play_cube.py $LEVELS --suite held_out --network final --theta-full 200 --rate 150 --rate-scaling --seed <s> --jobs 4 --quiet` |
| 2 | References, ideal fly, report | `uv run python scripts/reference_flies.py`; `uv run python scripts/ideal_fly.py --suite held_out --quiet`; `uv run python scripts/step2_report.py` |
| 3 | Tuning R | `uv run python scripts/step3_grid.py grid`, then `held-out --rate 50`; `uv run python scripts/step3_report.py --held-out 50` |
| 4 | Control networks | `uv run python scripts/make_control_connectivity.py all` |
| 4 | Runs and report | `uv run python scripts/step4_runs.py check`, `night1`, `night2`; `uv run python scripts/step4_report.py` |
| 7 | 50 Hz whole brain, per seed 0–2 | `uv run python scripts/play_cube.py $LEVELS --suite held_out --network whole_brain --theta-full 200 --rate 50 --rate-scaling --seed <s> --tag _step7 --jobs 4 --quiet` |
| 7 | Report | `uv run python scripts/step7_report.py` |
| 5 | Ship checks (no brain) | `uv run python scripts/check_ship_neurons.py`; `uv run python scripts/ideal_ship.py`; `uv run python scripts/ship_pathway_check.py` |
| Viewer | Replay, still, video | `uv run python scripts/replay.py <run folder>` (`--still <s>`, `--export`) |

*Steps 5 and 6 (fly-driven ship and Stereo Madness runs) are added when they're fixed.*

## Still to add

- Step 4 and Step 7 **results** (now in `step4_report.md` and D51/D52) in write-up form.
- **Step 5:** the ship baseline results (D53; `docs/notes/ship_baseline_results.md`) in write-up form.
- **Step 6:** Stereo Madness (N, seeds and the network, fixed before any run) and the showcase replay rule.
