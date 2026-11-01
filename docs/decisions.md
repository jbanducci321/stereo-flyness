# Decision log

One entry per decision: what we chose, what else we considered, and why. Newest at the bottom. Mark an entry superseded instead of deleting it.

## Decided

**D1. Project name: stereo-flyness** (2026-10-21)
The earlier working name "fly-dash" is retired.

**D2. Connectome: FlyWire FAFB v783** (2026-10-21)
This is the public release the Shiu et al. model supports. We use one version for the whole project. MaleCNS (with the ventral nerve cord) may come later, not in v1.

**D3. Simulation base: the Shiu et al. 2024 Brian2 model** (2026-10-21)
- Alternatives: eonsystemspbc/fly-brain, which packages the same model with GPU backends. It's GPL-2.0-or-later (copying its code would make this repo GPL) and is built for Linux/WSL2.
- Why: the Shiu code is MIT-licensed, published in *Nature*, and works on native Windows. fly-brain stays a reference for the GPU phase.

**D4. Environment: Python 3.12 with uv and a committed lockfile** (2026-10-21)
- Alternatives: conda (what Shiu's repo uses), or plain venv + pip.
- Why: Brian2 requires Python ≥ 3.12, and uv's lockfile gives both of our Windows machines identical versions.

**D5. Connectome weights are frozen** (2026-10-21)
Weights come from synapse counts, and signs from predicted neurotransmitters. We tune at most 2–3 interface dials, and fewer dials means more credit to the fly's wiring. The only exception is lesions: silencing neurons is an experiment, not tuning.

**D6. Game scope: cube (blocks, spikes) and ship only** (2026-10-21)
Stereo Madness has no jump pads or orbs, so we don't build them.

**D7. Stereo Madness is the held-out final test** (2026-10-21)
- We tune only on procedurally generated levels (cube-only, ship-only, mixed), and run Stereo Madness once, with everything frozen.
- Generator difficulty comes from the physics (jump reach, reaction room), not from Stereo Madness's layout. Comparing summary stats to it afterward is allowed.

**D8. Game physics: our own implementation, informed by reverse-engineered references** (2026-10-21)
- camila314/gdp (2.2 branch, no license) is read as a reference only, and no code is copied.
- Any 2.1 vs 2.2 differences get flagged.
- A search-based bot must be able to beat each level before we trust it.

**D9. Geometry Dash level data stays local** (2026-10-21)
The level design belongs to RobTop Games. Only the fetch-and-convert script is committed; extracted data lives in the git-ignored `data/` folder.

**D10. v1 input comes from game state, not pixels** (2026-10-21)
The looming signal is computed from obstacle distance, size and expansion rate. A pixel-based compound eye may come later.

**D11. Mode switching is an interface choice** (2026-10-21)
In mixed levels, our code picks the readout: jump neurons in cube mode, steering neurons in ship mode. The fly doesn't decide this.

**D12. Workflow: Step 0 on main, then branches + pull requests** (2026-10-21)
Jacob commits Step 0 work on main with Shannyn as co-author. After setup, each change goes through a branch and a reviewed pull request.

**D13. Public repo, with no data committed** (2026-10-21)
The GitHub repo is public. The FlyWire connectivity data is CC BY 4.0 and Shiu's code is MIT, but data files and level data are never committed either way. A code LICENSE (likely MIT) waits until the license check is complete.

**D14. Shiu's model code is vendored unchanged** (2026-10-21)
- `brain/shiu_model.py` and `brain/shiu_utils.py` are byte-for-byte copies of commit `91bdd1e`, with only a docstring added. The MIT license is kept in `brain/SHIU_LICENSE.txt`.
- Why: results stay directly comparable to the paper. Our changes (closed-loop stepping, subcircuits) go in separate modules.

**D15. Sugar GRN list mapped to v783** (2026-10-21)
- `720575940620900446` (v630) was replaced by `720575940639259967` (v783), matching eonsystemspbc/fly-brain. We checked it ourselves: 95% of its downstream partners are shared with the other sugar GRNs.
- Lesson: any neuron ID taken from a v630-era source must be checked against v783.

**D16. Frame stepping uses a changeable Poisson input equivalent to Shiu's** (2026-10-22)
- Shiu's `PoissonInput` fixes its rate when the network is built, so the game couldn't change stimulation between frames.
- `BrainStepper` instead gives each stimulated neuron its own `PoissonGroup` source, connected one-to-one with `v += w_syn * f_poi`. That's the same per-step event probability (`rate * dt`), weight, target variable and time slot, but with rates that can be reassigned at any time. Stimulated neurons get no refractory period, as in Shiu's code.
- Alternatives considered: rebuilding the PoissonInputs every frame (forces code regeneration, slow), or adding a rate variable to the neuron equations (changes Shiu's model).
- Evidence:
  - on a tiny network, it matches Shiu's PoissonInput side by side (`tests/test_stepper.py`);
  - on the whole brain, MN9 is 67.8 vs 67.7 Hz (Welch t = 0.03), and MN9 follows on/off input switching within ~2 frames (`scripts/validate_stepping.py`, FEASIBILITY.md).

**D17. Closed-loop runs use `BrainStepper.run_frames()`, not one `step()` per frame** (2026-10-22)
- Each `step()` is a separate Brian2 `Network.run`, and Brian2 regenerates code objects and garbage-collects on every call, costing ~100–250 ms regardless of network size.
- `run_frames(n, frame, on_frame)` runs all frames in one `Network.run` and calls `on_frame(i, counts)` at each frame boundary through a `network_operation` (in the 'start' slot, so each callback sees exactly k frames of simulation). The callback reads spikes and may call `set_rate` for the next frame.
- Tested to give results identical to a `step()` loop, including rate changes. 5–100× faster for small networks (see FEASIBILITY.md Benchmarks).
- `step()` stays for one-off experiments.
- Consequence for the game loop: the game advances inside the callback, so the brain drives the loop. The game is still step-locked to the brain.

**D18. Subcircuit size target: up to ~20k neurons / ~3M connections** (2026-10-22, provisional)
- Based on benchmarks with neighbourhood stand-ins: one 90 s level in a few minutes on one core, and a tuning grid overnight.
- The extraction rule itself is still open (Shannyn's S5). This only bounds its size. To be revisited with the real subcircuit (J5).
- **Updated by D36 (2026-10-28):** the limit is now ~25k neurons / ~3M connections.
- **Replaced by D37 (2026-10-30):** the limit is now a tuning time (a 200-run grid on 30 s practice levels in ≤ 10 h, 4 at once, on Jacob's laptop), not a neuron count.

**D19. End deliverable: a record-and-replay viewer of the fly playing Stereo Madness** (2026-10-22)
- **Goal:** watch the fly brain play Stereo Madness at real speed, with its brain activity shown beside the game. Looming neurons (LC4/LPLC2) light up as obstacles approach, the Giant Fiber flashes when it fires, and the cube jumps. Steering neurons drive hold/release in ship sections.
- **Approach: record, then replay.**
  - Closed-loop runs log every frame (game state, input rates, watched spike counts) from the `run_frames` callback.
  - A viewer plays the log back at true 60 fps, however long the simulation took. The whole brain runs ~16–26× slower than real time (D17/D18), so live whole-brain viewing isn't possible on a laptop.
- **Live mode is optional:** only small subcircuits (~1k–5k neurons) run near real time.
- **Honesty requirements:**
  - The viewer must visibly separate our input encoding (the looming signal we compute) from the fly's own spikes.
  - It must say it is a replay of a simulation.
  - It must not smooth or alter recorded activity.
- **Why:** it's the project's centerpiece and makes the "fly vs our code" distinction visible.
- **Dependencies:** the viewer library (likely pygame) and any 3D/morphology rendering are chosen when the viewer is built, with the user's approval.

**D20. Game physics: Geometry Dash 2.2, exact gameplay, native units** (2026-10-22)
- **Version:** 2.2 physics: fixed 240 Hz tick, deterministic, and the best documented (camila314/gdp 2.2). The Stereo Madness copies are 2.1 uploads, but its layout is believed unchanged. Revisit only if the bot can't beat the converted level.
- **Fidelity:** exact for everything that affects gameplay (gravity, jump, ship acceleration and limits, speed, tick rate, hitboxes, landing and death rules, stair snapping). Visuals don't need to match.
- **Units:** GD native units internally (1 block = 30 units, velocities per 1/60 s, 240 Hz ticks). Convert only for display.
- **Numerics:** 64-bit floats with the game's update order (velocity, then position, then collisions). No bit-exact float32 matching.
- **Sources:** facts only, each cited in `docs/game_physics.md`. No code copied from camila314/gdp (no license) or OpenGD (GPL-3.0).
- **Audio:** the song and sound effects (copyrighted) are loaded from the user's own local files for replays and never committed.

**D21. Stereo Madness layout source: official main-level data, cross-checked** (2026-10-23)
- The layout comes from the official main-level data in Open-GD/OpenGD `mainLevels.json` (pinned commit and SHA-256). It's decoded with the standard library, so no new dependency.
- It's cross-checked against the archived server copy 77236587: all 1,399 gameplay objects are identical.
- Server level 94729537 was rejected: it's a different level, despite its name.
- Fetched and decoded by `scripts/fetch_stereo_madness.py` into git-ignored `data/gd/` (D9).

**D22. Level format: JSON hitboxes, ground at y = 0** (2026-10-23)
- **Structure:** one JSON file per level, in GD units with the ground at y = 0. Gameplay objects are stored as ready-made axis-aligned hitboxes (`kind`, corners, original GD ID), so the engine only does rectangle overlaps.
- **Portals** store x/y/mode. The engine derives ship floor/ceiling from the portal's y with the GD rule, keeping it in one place for Stereo Madness and generated levels.
- **Dropped:** decoration, triggers and coins.
- **Where it lives:** spec in `docs/level_format.md`; code in `src/stereo_flyness/game/level.py` and `objects.py`.
- **Alternatives considered:**
  - storing raw GD object IDs and resolving hitboxes at runtime (more engine logic, and the GD table leaks into the generators);
  - precomputed ship bounds in the file (the rule would live in two places).

**D23. Engine interface: one boolean input per 240 Hz tick; every run is logged** (2026-10-23)
- **Input:** `Game.tick(held)` advances one physics tick with the button held or not. That's the only input. The bot, test scripts and the brain interface all drive the game this way.
- **Frames:** one 60 fps frame = 4 ticks. How often the brain is consulted, and how spikes map to presses, stays open (T4).
- **Rules:** the engine is deterministic, and `game/` never imports `brain/` or `interface/`.
- **Logging:** runs are logged per tick (`game/recorder.py`, R1). Replaying a log's inputs reproduces the run exactly.
- **Alternatives considered:**
  - Frame-level input (60 Hz): loses the physics' 240 Hz resolution.
  - Separate press/release events: equivalent, but harder to log and to drive from spikes.
- Spec: `docs/game_engine.md`.

**D24. Search bot validates levels; Stereo Madness is beatable in our engine** (2026-10-24)
- **The bot:** a depth-first search over per-frame hold/release with rewinding and failed-state memory (`game/bot.py`, `docs/bot.md`). Ship states are merged in buckets, with a mandatory finer re-check before any "impossible" verdict.
- **The result:** it beats Stereo Madness in ~5 s, with portal timings matching the data and the video.
- **What that proves:** a sensitivity check shows the level stays beatable under several plausible physics errors. So this validates the conversion and the rough physics, not fine details (`game_physics.md` §11).
- **A correction it found:** the third ship portal is unreachable (rotated 90°, above a tunnel roof), so the final section keeps the 0/300 area. This corrects the J3 conversion report.
- **Going forward:** every generated level must be bot-beatable (Step 1.4).

**D25. Replay viewer: pygame window + ffmpeg export, hitbox-accurate visuals for now** (2026-10-24)
- **What it does:** `viewer/` plays recorded runs in a pygame window (controls and overlay), saves stills, and exports MP4 via the ffmpeg program. pygame 2.6.1 is added as a dependency (LGPL), with Jacob's approval.
- **Visuals:** objects are drawn as their real hitboxes. That's simple, honest and good for debugging. Polished graphics, the brain panel (R3) and music come last, for the final showcase, built on this viewer.
- **Audio:** only ever loaded from the user's own local files; publishing needs permission or a royalty-free track.
- **Alternatives considered:** matplotlib animation (clunky for real-time playback); a web viewer (more moving parts).
- Spec: `docs/replay_viewer.md`.

**D26. Practice levels: seeded chunk generator, physics-based tiers, bot-validated, seeds-only suites** (2026-10-27)
- **How levels are built:** random chunks from a physics-based library, with gaps measured in seconds of reaction time. Easy/medium/hard tiers set gaps, chunk mix, stair width and ship opening height. Generator v3.
- **Always beatable:** every level is beaten by the search bot; unbeatable candidates are re-rolled deterministically.
- **No Stereo Madness influence:** the design uses SM's object kinds only, never its layout (D7).
- **Difficulty is measured per level** (reaction gaps, cube press windows, ship openings). Measurements showed staircases and platform spikes need ~17 ms presses, so easy omits them (tightest window ~142 ms, 0% under 50 ms).
- **Suites:**
  - **training:** 50 cube / 50 ship / 50 mixed;
  - **held-out:** 20 / 20 / 20, from a separate seed range, never used for tuning.
  - Only the seeds are committed (`configs/level_suites.toml`); levels are built and cached locally.
- **Alternatives considered:** free random placement (mostly junk or impossible levels); committing generated level files (large, and redundant with seeds).
- Spec: `docs/level_generators.md`.

**D27. Steering tests run on original and T4/T5-corrected signs** (2026-10-27)
- **The problem:** the model's signs (`Excitatory` in `Connectivity_783.parquet`) are machine-learning neurotransmitter predictions (Eckstein et al. 2024). They mark 13.7% of T4d and 12.1% of T5d neurons inhibitory. T4/T5 are known to be cholinergic, and FlyWire's own annotation table (`top_nt`) calls ~98% of them acetylcholine. T4d/T5d are the main input to VS cells, so ~13% of that input has the wrong sign in the model.
- **What we do:** each steering pathway test runs twice:
  - **original:** the connectome exactly as Shiu's model uses it. This stays the main result.
  - **corrected:** a copy of the connectivity file with every connection from a T4 or T5 neuron (T4a–d, T5a–d) set to excitatory. Nothing else changes.
- **Rules:**
  - Only T4/T5 are corrected, because their transmitter has independent biological evidence. We don't look for other neurons to correct; that would be tuning the connectome.
  - The corrected file is written by a script into git-ignored `data/` and never replaces the original. Shiu's code stays unchanged (D14).
  - Every result is labelled `original` or `corrected`.
  - The escape pathway is unaffected (all LC4/LPLC2 → Giant Fiber synapses are excitatory), so the escape tests run on the original only.
- **Relation to D5:** this is a labelled sensitivity check, like a lesion, not tuning. The main results keep the frozen weights.
- **Alternatives considered:**
  - Original only, reporting the sign errors as a limitation: simpler, but leaves us unable to tell a failed steering pathway from a data error.
  - Correcting signs everywhere: breaks comparability with Shiu et al. and would mean rewriting D5/D14.
- **Which version carries forward:** decided in D28.
- Details: `docs/pathway_tests.md` ("Two sign versions").

**Pathway-test rules (D28–D35), set before round 1** (2026-10-28)
- **Agreement:** Jacob proposed D28–D34; Shannyn reviewed and amended them; both agreed on 2026-10-28.
- **What they are:**
  - D28–D33 are rules for *judging* the pathway tests (J4, checkpoint 3). They change nothing about what gets simulated.
  - D34 changes what gets *recorded*, the one thing that can't be fixed after a run without re-running it.
  - D35 removes one experiment.
- **When they were written:** before the full results exist, but **after the 9-trial pilot** (2026-10-28; one trial each at 150 Hz of E1 LC4/LPLC2/both, E5a, and S1 down/up on both sign versions). Those numbers were known:

| Pilot trial (150 Hz, n = 1) | Right Giant Fiber | Left Giant Fiber | Right VS | Right DNp20 |
|---|---|---|---|---|
| E1 LC4 | 121 Hz | 31 Hz | | |
| E1 LPLC2 | 158 Hz | 100 Hz | | |
| E1 LC4 + LPLC2 | 190 Hz | 96 Hz | | |
| S1 down, original / corrected | | | 223 / 239 Hz | 137 / 138 Hz |
| S1 up, original / corrected | | | 0 / 0 Hz | 0 / 0 Hz |

**D28. Sign version carried forward: original by default, corrected only by a written fallback rule** (2026-10-28)
- **The original connectome is the main version** for all later stages (ship pathway, Step 5; mixed levels and Stereo Madness, Step 6). The T4/T5-corrected version (D27) is always reported alongside it as a sensitivity check.
- **Fallback:** if, and only if, the original fails the steering go/no-go (D31) and the corrected version passes it:
  - we report that as a finding ("a known sign-labelling error breaks the circuit");
  - later stages continue with the corrected version, labelled as such everywhere.
- **Written after the pilot:** the 9-trial pilot showed both sign versions behaving similarly (n = 1).
- **Why:** it keeps the strongest claim ("the unaltered connectome") by default. It doesn't let a data error everyone agrees is wrong sink the ship pathway. And any switch comes from a rule written before the results, not from a preference.
- **Alternatives considered:**
  - Always original: could abandon the ship pathway over a labelling error.
  - Always corrected: weakens the headline claim even when the correction makes no difference.
- **Resolves** the open D27 question.

**D29. Escape pathway go/no-go** (2026-10-28)
- **Definitions:**
  - "Fires" means the right Giant Fiber spikes at least once in a trial. "Reliably" means in at least 9 of 10 trials (D33).
  - "Pooled SD" is the trial-to-trial SD pooled across the two groups compared (an effect-size bar, not a standard error).
  - **Judged on E1 with LC4 + LPLC2 together** (the input the game will use). LC4 alone and LPLC2 alone are reported as findings.
- The escape pathway is a **GO** if all four rules hold:
  0. **It responds at all:** the right Giant Fiber fires reliably at one or more sweep rates. (Without this, rule 2 would pass automatically if it never fired.)
  1. **It rises with input:** the right Giant Fiber's mean rate at 200 Hz exceeds its mean rate at 25 Hz by more than 2 pooled SDs. Small dips between neighbouring rates are allowed.
  2. **The stimulated side dominates:** at every sweep rate where the right Giant Fiber fires reliably, its mean rate exceeds the left Giant Fiber's by more than 2 pooled SDs.
     - The right/left ratio and the left Giant Fiber's rate are reported as findings.
     - **This rule changed after the pilot.** The first draft required the right side to be ≥ 2× the left, replacing the S4 plan's "left stays near zero". The pilot's single trials gave ratios of ~3.9× (LC4), ~1.6× (LPLC2) and ~1.98× (both). Lowering the ratio to fit those numbers would have been fitting the rule to the data. Instead the rule tests what "dominates" means directly (a clear difference), and the ratio is always reported.
     - The left Giant Fiber is reached through indirect routes (no LC4/LPLC2 synapse crosses sides). D34's recording is meant to trace them.
  3. **It's fast and consistent enough for the game:** in E2, the mean onset latency (input on → first right Giant Fiber spike) is **under 100 ms**, **and** 4 × its SD is under 238 ms.
     - The SD condition means one fixed input lead time can land the jump inside the ~238 ms window to clear a single spike (`docs/game_physics.md` §3) nearly every time.
     - A mean under 50 ms is reported as ideal.
- **Offset** (how long firing continues after input stops) is measured and reported, but **is not part of the go/no-go**. It's handled by the output rule, decided after round 1 (e.g. a refractory window after each jump).

**D30. Specificity controls (E4)** (2026-10-28)
- **No input (E4 baseline, and S0 for steering):** every neuron must fire **exactly 0 spikes**. Shiu's model has no internal noise, so anything else is a bug.
  - The runner checks this automatically for every trial with no input, and stops the round if it fails. Baselines run first.
- **LC10a and sugar controls:**
  - A control counts as **quiet** if the right Giant Fiber's mean rate is **under 10%** of its E1 rate with LC4 + LPLC2 at 150 Hz.
  - A control above that is reported as a **model finding**, not a failure of the escape go/no-go. The S4 plan already notes that LC10a reaches the Giant Fiber through two-step routes (314 synapses).
  - For each control, the fraction of trials with at least one Giant Fiber spike is also reported.

**D31. Steering pathway go/no-go** (2026-10-28)
Judged on the right side (the stimulated side), for each sign version separately.
- **Definitions:**
  - "VS cells fire reliably" means at least one right VS cell fires in 9 of 10 trials.
  - VS rates are group means.
  - "DNp20 fires reliably" means it fires in 9 of 10 trials.
- The steering pathway is a **GO** if all three rules hold:
  1. **Downward motion drives the output:** at one or more sweep rates, "down" input (T4d + T5d) makes the right VS cells and the right DNp20 fire reliably.
  2. **It's direction-selective:** at that same rate, "up" input (T4c + T5c) gives **both** the right VS cells and the right DNp20 less than 10% of the mean rate that "down" gives.
     - This is a sanity check: "up" reaches VS cells only through inhibitory LPi neurons, so near-zero is expected.
  3. **It isn't just any motion:** horizontal input (T4a/b + T5a/b, S3) gives the right VS cells a mean rate lower than "down" by more than 2 pooled SDs, at the same input rate.
     - **The rate that counts is D32's half-of-maximum rate**, run in round 2, because VS cells are near saturation at 150 Hz, where horizontal and downward input could look alike for the wrong reason.
     - The 150 Hz comparison (round 1) is reported alongside it.
- **S2** (does added upward motion lower VS activity?) is reported as a biological check. **It is not part of the go/no-go**: the game only needs "down drives the output, up doesn't".
- **Output neuron:** rules 1–2 use DNp20 (DNOVS1), which gets the strongest VS input. DNp22 is reported alongside it. The ship control rule itself is decided later.

**D32. How round 2's rates are picked** (2026-10-28)
Two numbers that only round 1 provides; these rules pick them, not us:
- **E2's lower rate:** the lowest sweep rate at which the right Giant Fiber (E1, LC4 + LPLC2) fires **within the first 100 ms in at least 9 of 10 trials**. If no rate qualifies, use 200 Hz and report that the pathway never became fully reliable.
- **Half-of-maximum "down" rate** (used for S2's fixed "down" drive and for the S3 comparison, D31): the lowest sweep rate at which the right VS cells' mean rate (S1, "down") reaches **at least half** of their highest mean rate across the sweep.
  - Picked per sign version.
  - If 25 Hz (the lowest sweep rate) already qualifies, use 25 Hz and say so.
  - **Why not 150 Hz:** the pilot showed VS cells near their maximum at 150 Hz (~220–240 Hz), where added inhibition is hard to see.

**D33. Ground rules for the pathway-test data** (2026-10-28)
- **No peeking mid-run:** nobody analyses a round until it has fully finished. The automatic zero-input check (D30) is the only exception.
- **The pilot doesn't count:** the pilot trials were a systems check. All reported results come from the full runs, which start from an empty results folder.
- **Code is frozen during a round:** no changes to simulation or runner code between the start and end of a round. If something must change, the affected trials are re-run. Every trial file records the git commit that produced it.
- **Statistics:**
  - results are reported as mean ± SD across a condition's trials;
  - "reliably" means in at least 9 of 10 trials;
  - E3 uses 5 random LC4 subsets × 2 trials per fraction (10 per fraction), because which neurons get picked matters more than repeating trials on one subset.
- **Changing a rule:** a rule in D28–D35 may change after results only if it can't be applied as written (e.g. no rate qualifies). The change and its reason go in this log, and results are reported under both the old and new rule.

**D34. Record every neuron that fires, frame by frame** (2026-10-28)
- **The change:** each pathway-test trial also saves the per-frame spike counts of **every neuron that fires at least once**, anywhere in the brain. This is on top of the named watch groups.
  - Saved sparsely: only non-zero frame counts.
  - The simulation already counts all neurons, so this keeps numbers that were previously thrown away.
- **Our input stays labelled:** the record includes the stimulated neurons, whose spikes are driven by our input. Each trial file lists the stimulated groups and their IDs, and analyses and the viewer must label or exclude them as our input (hard rule 10).
- **Why:**
  - Unsaved activity can only be recovered by re-running hours of trials.
  - It lets us trace how signals spread (e.g. how the left Giant Fiber is reached, D29).
  - It gives S5 (subcircuit rule) the complete set of neurons each input recruits.
  - It feeds the replay viewer's brain panel (D19).
- **Cost:** most neurons never fire (the sugar test activated ~400 of 138,639). The whole run is expected to stay well under ~1 GB in git-ignored `results/`.
- **Alternatives considered:**
  - Watch groups only: smallest, but open questions would need re-runs.
  - Per-trial totals for every neuron: shows *which* neurons fired, but not *when*, so signal paths can't be traced.

**D35. E5a dropped** (2026-10-28)
- E5a (stimulate LC4 with LPLC2 silenced, and the reverse) can only show whether one looming type recruits the other. In this model, unstimulated neurons are silent unless driven, so silencing them changes little: in the pilot, LC4 → right Giant Fiber was 121 Hz with and without LPLC2 silenced.
- E1's all-neuron record (D34) answers the same question directly, by showing whether LC4-only input makes any LPLC2 neuron fire.
- E5b and E5c (silencing the Giant Fiber's inhibitory and excitatory partners) are kept.

**D36. Subcircuit rule (S5): recruited neurons plus their strong inputs, built in two stages** (2026-10-28)
Proposed by Shannyn (S5), from the J5 candidate comparison (`docs/subcircuit_candidates.md`). Agreed by both on 2026-10-28.
- **The rule ("a2-style"):**
  1. **Recruited neurons:** every neuron that fires in whole-brain runs of the inputs the game uses.
  2. **Plus their strong inputs:** every neuron with a connection of **≥ 30 synapses** onto a recruited neuron.
  3. **Plus every neuron the pathway tests stimulate or watch**, so the subcircuit can be validated.
  - Everything is kept with every connection between kept neurons. Weights are unchanged (D5).
- **"Inputs the game uses":**
  - the pathway tests that stimulate game inputs: LC4/LPLC2 (E1–E3, E5) and T4/T5 (S1–S3);
  - on **both sides** (right, left and both together);
  - on **both sign versions** (D27);
  - and, once T4 has decided the encoding, whole-brain runs of that encoding.
  - E4's controls (LC10a, sugar) are not game inputs and are excluded.
- **Two stages** (this resolves the ordering J5 → T3 → T4):
  - **Interim subcircuit (J5, for T3):** built from all current pathway tests plus new left-side and both-sides whole-brain runs. It is validated against the tolerance below and is the feasibility evidence for T3.
  - **Final subcircuit (after T4):** rebuilt with the same recipe once the encoding is known, adding whole-brain runs of that encoding. It is validated again before tuning (Step 3).
- **Tolerance:**
  - It is judged on **held-out, game-like runs**, never on Stereo Madness (D7).
  - It is agreed now, before the final validation, as with D29–D31.
  - The subcircuit is faithful enough if:
    1. the D29 and D31 go/no-go verdicts are the same as the whole brain's;
    2. key-group rates (Giant Fibers, VS, DNp20/22, LPi09) are within **10%** of the whole brain's, or within **1 Hz** for groups under 10 Hz;
    3. Giant Fiber first spikes fall within **one frame** (4.2 ms) of the whole brain's in **≥ 95%** of events;
    4. the median share of whole-brain-active neurons that stay active is **≥ 90%**;
    5. **later, in closed loop (Step 2 onward):** the same jump/hold actions within **±1 frame** for **≥ 95%** of actions.
- **Tolerance clarified (agreed by both, 2026-10-30, before any subcircuit ran the probes):**
  - **Held-out probes** (`[probes]` in `configs/pathway_tests.toml`), never used to build a subcircuit:
    - **P1** expanding loom in random chunks;
    - **P2** looming ramp;
    - **P3** up/down switching;
    - **P4** downward motion on and off over scrolling;
    - **P5** a spatial loom growing from a small patch (8 steps of 40 ms at 150 Hz, neighbourhoods by shared input partners);
    - **P6** P1's loom plus constant front-to-back T4a + T5a at 50 Hz, watching the Giant Fibers and the steering groups;
    - **P7** all LC4 + LPLC2 at 150 Hz, 100 ms on / 50 ms off × 4.
    - Each runs on the right side, the left side and both sides, with 5 trials. P3, P4 and P6 run on both sign versions.
    - The probes are now **locked**: no changes before J5 4c.
  - **Rule 2** also covers the left key groups: DNp20_L, DNp22_L and LPi09_L.
  - **Rule 4:**
    - The share is of **all** whole-brain-active neurons (stimulated ones excluded), not only those inside the subcircuit. Neurons the build cut out count as lost.
    - It is judged **per probe type**: the median must be ≥ 90% in each type, and the lowest is reported.
  - **Cascades (D37):** trial pairs where either network's trial is a runaway cascade are left out of rules 2–4 and reported separately. Rule 1 uses every trial.
  - **Stuck state:** the validation also reports whether any subcircuit trial enters the stuck state (≥ 50% of the stuck-state neurons it contains fire).
  - Rules 1–3 are otherwise unchanged.
  - **Code:** `scripts/validate_subcircuit.py`, `src/stereo_flyness/experiments/subcircuit_validation.py`.
- **If it doesn't fit or doesn't pass:**
  - **Over the size limit:** raise the synapse cut-off above 30 until it fits, as long as the tolerance still holds. If no cut-off fits, raise the limit (and log it) or rethink the rule.
  - **Fails the tolerance at ≥ 30 synapses:** lower the cut-off to **≥ 20** (keeps more inputs, so the subcircuit gets bigger), then re-check size and tolerance.
- **Size limit:** **~25k neurons / ~3M connections** (updates D18). **Replaced by D37:** a tuning-time limit.
- **Controls (Step 4):**
  - The controls run on the **whole brain**.
  - If tuning uses the subcircuit, the shuffled-connectome control goes through the same pipeline: shuffle the whole brain, run the same pathway tests on it, apply this rule, build its own subcircuit.
- **Why this rule:**
  - In the candidate comparison, only the a2-style rule kept ≥ 90% of active neurons on the one genuinely new input (horizontal motion, S3: 92–93%, key-group errors ≤ 8%).
  - Wiring-only rules (1–3 steps upstream of the outputs) kept ~70–85%, with key-rate errors up to 40–150%.
  - Activity-only over-fired VS cells on S3 (15 → 39 Hz), because it missed recruited inhibition.
  - The 2-step hybrid (`h1`) kept 84–87% on S3, below the 90% bar.
- **Known limits:**
  - The candidate comparison stimulated the right side only.
  - Its "held-out" conditions mostly reused the training inputs, so S3 was the only genuinely new input. Hence the both-sides runs and game-like validation above.
  - The wiring sweep changed steps and synapse cut-off together, so it doesn't isolate either.
- **Alternatives considered:**
  - wiring-only rules (smaller and faster, not faithful enough);
  - activity-only (fails on unseen input);
  - the 2-step hybrid (just below the bar on S3).

**D37. Cascade trials are left out of subcircuit builds; the size limit is a tuning-time limit** (2026-10-30)
Proposed by Shannyn after J5 checkpoint 4b showed that D36 as written doesn't fit the ~25k limit (`docs/subcircuit_candidates.md`, "Interim size"). Agreed by both on 2026-10-30, before any subcircuit was validated or run on probes.
- **Change to D36, the cascade test:**
  - A whole-brain trial is a **runaway cascade** if its number of active neurons is **more than 2× the median** of the same condition's other trials **and more than 5,000 above it**.
  - Cascade trials are **left out of the recruited set** (D36 step 1) and **out of validation rules 2–4**, and are reported separately.
  - The settings are in `[cascade]` in `configs/pathway_tests.toml`, and the code is in `src/stereo_flyness/experiments/cascades.py`.
  - Everything else in D36 is unchanged, including the **≥ 30-synapse** cut-off.
- **Diagnostic:**
  - Each flagged trial also reports the share of the known stuck-state neurons that fire: 8,189 neurons, listed in `configs/stuck_state_783.csv` (see `docs/cascades.md`).
  - The known cascades score 97–98%, and every other trial at most 8.1%.
  - A trial is "in the stuck state" if ≥ 50% of them fire.
- **Size limit:**
  - A **200-run tuning grid on 30 s practice levels** must finish in **≤ 10 h with 4 runs at once on Jacob's laptop**: Intel Core i7-10750H, 6 cores / 12 threads, 32 GB RAM, Windows 11.
  - This replaces D36's ~25k / ~3M limit, which was a stand-in for speed.
- **Practice levels for tuning are 30 s long.**
  - The time limit depends on it: with 90 s levels, the grid would take ~21.5 h.
  - Stereo Madness keeps its real length. It's run once and never tuned on (D7).
- **Interim build** (`configs/subcircuits/interim.toml`; not validated yet):
  - **33,480 neurons / 3.39M connections**, identical to the measurement build `d36_nocascade_30`.
  - Speed: 8.9× slower than real time alone, 17.2× each with 4 at once, so the grid takes ~7.2 h.
  - The Giant Fibers keep 87–88% of their input (82% of their inhibitory input).
- **Check before the rebuild (2026-10-30):** the test, applied to all 1,410 whole-brain trials (probes included), flags exactly the 3 known cascades:
  - their ratios are 3.7×, 2.6× and 3.3×, with +7,963 to +8,135 extra neurons;
  - every other trial is at most 1.62× and at most +531.
- **Why:**
  - About 7,400 of the 27,960 recruited neurons fired only in 3 of 1,350 trials. Those trials entered a self-sustaining state (~8,300 neurons, centred on the mushroom body) that never stops, and the subcircuit isn't meant to reproduce it.
  - Longer encoding runs in the final build would add more of these neurons each time.
  - Raising the cut-off to fit 25k (≥ 75 synapses) would have cut the Giant Fibers' inhibitory input to 62–67%, the very input D36 was chosen to keep.
  - It was decided before any subcircuit was validated or run on probes.
- **Model property:**
  - The stuck state is treated as a property of the model, not of the fly. The write-up says so, and says the hypothesis is untested (`docs/cascades.md`): no adaptation, no noise and a spiking APL let a recurrent mushroom-body loop lock in, whereas real APL inhibition is graded.
  - The link to upward motion isn't supported (p = 0.24 within steering trials).
  - Revisit if later tests show otherwise.
- **Alternatives considered:**
  - D36 as written, with the limit raised to ~45k / 4.5M;
  - cascades excluded at ≥ 75 synapses;
  - a 3× ratio test (it missed the S2 cascade, at 2.6×);
  - the stuck-state test as the rule: precise, but it only recognises the state we've already seen.

**D38. How runs that enter the stuck state are counted (Step 2 onward)** (2026-10-30)
Agreed by both, with D37. It covers closed-loop runs on the subcircuit and the whole brain.
- Stuck runs are **kept and counted in the main results**. The model does this, so we report it.
- They are **flagged in the run log and the replay** (D19).
- Results are **also reported with stuck runs excluded**, plus the **stuck rate**.
- **No re-running with new seeds until a run works.**
- **Flags, built into the run recorder (R1) in Step 2, saved in the log and shown in the replay:**
  - **Main flag, the stuck-state share:** ≥ 50% of the stuck-state neurons firing over a rolling ~100 ms window.
    - The stuck-state list is fixed: the whole-brain list (`configs/stuck_state_783.csv`, 8,189 neurons) restricted to the network that's running.
    - For the interim subcircuit that's **1,904 neurons**.
    - On a subcircuit this is the flag that works. D37's cascade test needs 5,000 extra active neurons, more than the subcircuit's stuck-state neurons.
  - **Backup flag:** active neurons over a 100 ms window above **3× the run's own median**. It's reported alongside, in case a different runaway state appears.
- **The 50% line separates cleanly on both networks** (checked 2026-10-30 on all 1,410 trials):

  | Network | Stuck trials | Highest share among the other trials |
  |---|---|---|
  | Whole brain | 97–98% (3 trials) | 8.1% |
  | Interim subcircuit | 78–81% (4 trials) | 35% |

  - The gap is narrower on the subcircuit, but there is still no trial between 35% and 78%.
- **The subcircuit gets stuck about as often as the whole brain** (4 vs 3 in ~1,400 trials), **but not always in the same trials:** E4 LC10a trial 3 got stuck only on the subcircuit. It reproduces the rate, not which runs get stuck.
- **Separate random streams per input group** (to test the natural stuck state with extra input): only if Step 2 shows stuck runs matter.
- Updated 2026-10-30 with Shannyn's review of J5 4c.
- **Amendment (2026-10-31), agreed by both: the backup flag's floor.**
  - The backup flag also needs **at least 1,000 active neurons** in the window, besides 3× the run's median. A quiet run's median can be near 0, and 3 × 0 would flag any activity.
  - 1,000 sits ~3× above a normal looming peak (~300 neurons) and below the stuck state's smallest size (~2,000).
  - **The count leaves out the neurons we stimulate** (hard rule 10). Otherwise our own input would count as the fly's activity: in ship mode thousands of T4/T5 are driven and would trip it all the time. The raw count is still logged.
  - The main flag (the stuck-state share) is unchanged.
  - **Looked at again for ship mode in Step 5.**

**D39. Step 0 go/no-go (T3): GO, cube first** (2026-10-30)
Agreed by both, from a joint draft (Jacob) reviewed and extended by Shannyn. Full write-up: `docs/FEASIBILITY.md` ("Go / no-go", "Risks", "Scientific limits we accept"). Step 0 is closed.
- **Verdict:**
  - **Cube (escape pathway): GO.**
  - **Ship (steering pathway): GO, with more risk.** It's built after cube, as planned (Step 5). Ship is the more fragile claim: in the real fly, DNp20/DNOVS mainly move the head.
- **What GO means:** the model can carry the signals the game needs. It is **not yet evidence that the fly can play.** That's Step 2's question.
- **Evidence:**
  - Shiu et al. reproduced on v783;
  - frame-by-frame stepping matches the unstepped model;
  - escape and steering pathway tests GO (D29, D31);
  - the interim subcircuit passes the D36 tolerance on all held-out probes (D36, D37);
  - a 200-run tuning grid takes ~7.2 h (D37);
  - the game is built (Step 1).
  - Every check was judged by rules agreed before its results were seen.
- **Speed is conditional:** the ~7.2 h grid assumes 30 s practice levels (decided with D37) and stand-in input. The final subcircuit is re-benchmarked after T4.
- **Accepted risks, carried into Step 2:**
  - the stuck state (D38);
  - sustained Giant Fiber firing (handled by the T4 output rule);
  - horizontal motion driving the ship pathway;
  - unbiological firing rates;
  - a subcircuit validated on stand-in probes;
  - the cube possibly jumping too early.
- **What would send us back:**
  - the final subcircuit (after T4) fails the D36 tolerance even with D36's fallbacks;
  - the final subcircuit with the real encoding exceeds D37's 10 h limit, and D36/D37's fallbacks can't fix it;
  - the untuned closed loop never produces a timed jump, whatever the dials;
  - stuck runs turn out to be common in game-length runs **and** to block jumping.
- **Scientific limits we accept** (the README must say so):
  - brain only: there is no ventral nerve cord, so the Giant Fiber → TTM jump step is outside the data;
  - no gap junctions;
  - ML-predicted neurotransmitter signs (D27, D28);
  - our direct input builds in looming and direction selectivity;
  - the stuck state is treated as a model property.
- **Planned cost:** the Step 4 shuffled-connectome control needs the full D36 pipeline on a shuffled brain (pathway tests, recruitment, build, validation).
- **Step 0 tasks:**
  - all done, except S3 (background reading), which is **ongoing, not blocking**. Next up are Giant Fiber escape (von Reyn 2014), then LC4/LPLC2 rates and the angular threshold (von Reyn Fig. 5b), for T4's θ_full question.
- **Next:** T4 (interface decisions), from Shannyn's cube draft (`docs/notes/t4_proposals.md`) and Jacob's answers (`docs/notes/t4_engineering_answers.md`).
- **Step 7 (whole brain on GPU):** at ~0.2% per simulated second, roughly 1 in 6 whole-brain 90 s runs would get stuck. The subcircuit-vs-whole-brain comparison reports the stuck rate.
  - That rate comes from 1 s tests in which the state only took off after ~0.6 s, so it's a rough guide for long runs.

**D40. Brain time: real time, consulted every physics tick (T4)** (2026-10-30)
Agreed by both, from Shannyn's T4 cube draft (`docs/notes/t4_proposals.md` §1) and Jacob's answers (`docs/notes/t4_engineering_answers.md`).
- **Brain time runs at real game time.** One brain frame per 240 Hz physics tick, exactly 1000/240 ms.
  - The frame callback runs on the exact interval, so Brian2 alternates 42, 42 and 41 steps of 0.1 ms. Every 3 frames is 12.5 ms, and brain time equals game time with no drift (tested).
  - This replaces `run_frames`' rounding to 4.2 ms for the closed loop. The pathway tests keep their 4.2 ms frames.
- **Order within a tick:**
  1. game state at tick *i* sets the input for brain frame *i*;
  2. the brain runs frame *i*;
  3. its spikes set `held` for game tick *i* + 1.
  - That's one tick (~4.2 ms) of delay, the same for every press.
- **Why:**
  - The timings that matter are physiological (8–13 ms from LC4/LPLC2 to the Giant Fiber, E2). Running the brain faster or slower than the game would rescale them.
  - A 16.7 ms frame is longer than the Giant Fiber's whole onset latency, so 60 fps steps would blur it.
  - With `run_frames`, the cost depends on simulated time, not on how often the game talks to the brain.
- **No dial.**

**D41. Input encoding for the cube: a growing LC4/LPLC2 patch tracking the nearest obstacle's angular size (T4)** (2026-10-30)
Agreed by both (draft §2, with Jacob's real-height change and Shannyn's corrections). Ship mode is decided in Step 5.
- **The eye** sits at the cube's front face (x + 15), at the cube's centre height, looking along the direction of travel.
- **What the eye sees is visual cells, not hitboxes.**
  - Each object fills a 30 × 30 cell: its hitbox centre ± 15. So a spike looks 30 units tall, not 12.
  - Cells in the same column that touch vertically are **merged into one object**, so a two-block wall is one object 60 units tall.
- **Which objects loom:** columns ahead of the eye that overlap the cube's current vertical extent, i.e. on a collision course. Solids and hazards are treated alike, because the fly can't tell them apart.
- **Angular size:** θ = atan((top − eye) / d) + atan((eye − bottom) / d), for the nearest looming column, where *d* is the gap from the eye to its front face. This is geometry, not a dial.
- **Which neurons are driven:**
  - On each side, the fraction **f = min(1, θ / θ_full)** of the LC4 neurons and the same fraction of the LPLC2 neurons, on both eyes equally.
  - Neurons are added in a fixed patch order grown by shared input partners: probe P5's construction and code (`loom_patches`, seed fixed per side, never tuned).
  - Every driven neuron gets the same Poisson rate **R**; the rest get 0 Hz.
  - It's implemented as one "loom" input group with per-neuron rates, so the input structure is fixed for the whole run.
- **Logged every tick, separately from the fly's spikes** (hard rule 10): θ, f, R, and which neurons are driven.
- **Choices we state as ours** (they go in the README):
  - Ceilings and other objects off the collision course don't loom, which happens to help the cube.
  - The collision course uses the cube's current height, so obstacles below stop looming mid-jump.
  - θ_full and the patch shape are geometric assumptions, not measured receptive fields.
  - **Objects the cube lands onto are invisible to the encoding** (added 2026-10-31, agreed by both). No "loom from below" rule: the Giant Fiber escape is a takeoff response to things approaching head-on or from the side, while landing on something uses a different behaviour (the landing response). It also wouldn't help, because a press in mid-air does nothing. This is the main cause of the ideal fly's deaths (D44).
- **Kept as a later option:** splitting the features, with LC4 following dθ/dt and LPLC2 following θ. For a single 30-unit object r/v is fixed (48 ms), so θ would determine dθ/dt. But with real heights a two-block wall has r/v ≈ 96 ms, so the split could tell tall objects from close ones. It's left out of v1 for simplicity.

**D42. Output rule: any Giant Fiber spike is a one-tick press (T4)** (2026-10-30)
Agreed by both (draft §3).
- `held` is true on tick *i* + 1 if **either** Giant Fiber spiked in brain frame *i*. Otherwise it's false.
- No spike count, no threshold, no refractory window.
- **Why:**
  - A single Giant Fiber spike drives the jump in the real fly, and real looms gave one or two spikes (von Reyn et al. 2014).
  - The cube only jumps from the ground, so spikes in mid-air do nothing.
  - A press lasts one tick, so holding never re-jumps by itself.
  - With no input the model gives zero spikes (D30), so there are no spurious presses.
- **What it gives up:** the model's Giant Fiber fires at 100–200 Hz while driven, against one or two spikes per loom in the fly. The rule takes the first spike. The README states the rates are unrealistic.
- **No dial.** Stuck runs are counted as they play out (D38). In a stuck state the Giant Fiber may fire late (`docs/cascades.md`).

**D43. Cube dials, θ_full calibration, Step 2 runs and their order (T4)** (2026-10-30)
Agreed by both (draft §4, Shannyn's threshold on `sc-t4-threshold`, and the follow-up messages).
- **One cube dial: R**, the stimulation rate of driven neurons. Step 2 uses 150 Hz (Shiu's default); the Step 3 tuning range is 25–200 Hz. (D45 restates R as the peak per-neuron rate near contact, if R × f is adopted.)
  - The other two dials allowed by D5 are kept for ship mode, or as a spare.
  - Not dials:
    - brain time (D40);
    - the output rule (D42);
    - which objects loom, object size and patch order (D41);
    - θ_full (calibrated, below).
- **θ_full is calibrated to the fly, not tuned:**
  - **Target:** the mean angular-size threshold of short-mode (Giant Fiber-driven) takeoffs at r/v = 40 ms in von Reyn et al. 2014 Fig. 5b: **θ ≈ 39° (s.d. ≈ 14°)**. Shannyn and her Claude read it independently.
    - Short mode, because our Giant Fiber spike stands in for that escape.
    - r/v = 40 ms is the condition closest to the game's 48 ms.
    - The mean, because the figure plots mean ± s.d. The s.d. is reported as the spread.
    - **Caveat:** their threshold is the retinal size at a fixed neural delay before takeoff, which we treat as the size at which the Giant Fiber pathway triggers. Close, but not identical.
  - **Method:**
    - Find the θ_full at which the **whole brain's** Giant Fiber (right or left) first spikes, on average, when a game-like loom (θ growing as in D41, r/v = 48 ms) reaches 39°.
    - This is open-loop, on the whole brain (the reference network, which also avoids a circular dependency on the final subcircuit), at R = 150 Hz.
    - About 10 θ_full values × 10 trials of ~1 s, under an hour with 4 workers.
  - **Fixed once, before the Step 2 baseline, and logged.** It isn't revisited in Step 3: if R is tuned, θ_full stays.
  - **Result (2026-10-31, D45): θ_full = 200° (R × f, start gap 245)**, and 1,082° for the flat-rate comparison.
- **Predictions, recorded before Step 2:**
  - **Calibrated:** the cube presses about mid-way through the single-spike window, at a gap of ~42 units, ~136 ms before contact (θ = 39°; the window is θ > ~23°).
  - **θ_full = 180°:** it jumps at or before the window opens. In P5 the Giant Fiber fired at the first step, 19 neurons per side, ≈ 22.5°.
- **Step 2 runs**, all untuned, with nothing chosen afterwards. They're played closed-loop on the 20 held-out cube levels, on the final subcircuit:
  - **Baseline of record:** calibrated θ_full, collision-course looming, R = 150 Hz.
  - **Comparison 1:** θ_full = 180° (uncalibrated). **Replaced by D45:** the pre-D45 encoding (flat R, calibrated the same way).
  - **Comparison 2:** "every object ahead looms", with calibrated θ_full.
  - The comparisons are reported next to the baseline and never replace it.
- **Order of work for Step 2:**
  1. encoding and output code (D40–D42);
  2. whole-brain calibration;
  3. whole-brain recruitment runs;
  4. the final subcircuit: build, validate, benchmark;
  5. the baseline of record and the comparisons.
- **Whole-brain recruitment runs (for the final subcircuit, D36):**
  - **Bot-driven:** the cube follows the bot's winning path while the brain sees the level through the encoding. The brain doesn't control the cube, so every part of each level is seen.
  - **Labelled bot-driven** in the logs and any replay, so a recruitment run can never be shown as the fly playing (hard rule 10, D19).
  - **Levels:** 10 cube training levels, fixed now and in proportion to the suite: easy seeds 0–3, medium 0–3, hard 0–1 (`cube-easy-0` … `cube-hard-1`).
  - **Settings**, one run per level × setting, ~70 runs of 30 s, about an overnight run with 4 at once:
    - the calibrated θ_full at R = 25, 50, 100, 150 and 200 Hz (the Step 3 range);
    - θ_full = 180° at R = 150 Hz (**replaced by D45:** the pre-D45 encoding, flat R = 150 Hz at its own calibrated θ_full);
    - "every object looms" with the calibrated θ_full at R = 150 Hz.
  - **Poisson seeds:** fixed from `base_seed` and each run's name, as in the pathway tests.
  - **Stuck runs:** D37's cascade test needs repeat trials, and these runs are one per level × setting, so D38's stuck-state flag is used instead (≥ 50% of the stuck-state neurons over ~100 ms). A stuck run is dropped from the frame the flag starts.
- **Validating the final subcircuit:**
  - **D36's tolerance**, on closed-loop runs on different levels from the recruitment runs: the next cube training levels (easy 4–5, medium 4–5, hard 2), never the held-out suite or Stereo Madness.
    - **Amended by D46 (2026-11-01):** rule 5 is judged on bot-driven runs, per obstacle approach, at five settings.
  - **It must also reproduce the calibration:** on the calibration looms, the Giant Fiber's first spike falls within one frame of the whole brain's (D36 rule 3). Near 39° that is about ±1.1°.
  - It is benchmarked against D37's time limit.
- **Ship mode (Step 5):** constraints only, in the draft §5.

**D44. Reference ceiling: the ideal 39° fly, logged before any Step 2 result** (2026-10-31)
Shannyn's request, agreed by both. `scripts/ideal_fly.py`, no brain.
- **The ideal fly** presses on every tick after one where the nearest looming object's θ ≥ 39° (one tick late, as D40/D42). It's a fly whose Giant Fiber fires exactly at the calibration target, every time. Real results are read against it.
- **Each death is classified:** (a) invisible to the encoding (the object never loomed), or (b) visible, but 39° is the wrong moment to jump.
- **The 10 recruitment levels (D43):**

  | | Easy | Medium | Hard |
  |---|---|---|---|
  | Collision-course looming (baseline encoding) | 4/4 | 0/4 | 0/2 |
  | Every object looms (comparison 2) | 4/4 | 2/4 | 0/2 |

  - Collision course: 6 deaths, **4 (a)** (a ground spike right after an obstacle: below the airborne cube, landed onto) and **2 (b)** (a spike on a block merges into a 60-unit column, reaches 39° at a gap of ~80 instead of ~42, and the jump comes too early).
  - Every object looms: the 2 (b) levels are completed. The other 4 deaths remain: the spike now looms, but only reaches ~11° seen from above (b).
- **All 50 cube training levels:** collision course easy 20/20, medium 6/20, hard 0/10 (24 deaths: **19 (a), 5 (b)**). Every object looms: 20/20, 9/20, 0/10 (21 deaths, all (b)).
- **Is 39° a fair ceiling? Mostly, but it isn't the best fixed threshold.** A check of other fixed thresholds (10–90°, never used to choose one: D43 fixes 39°):
  - 39° completes 26/50. The best fixed thresholds (44–50°) complete 29/50, and no fixed threshold completes more than 29.
  - It isn't smooth. Thresholds of 14–36° complete no level at all, even easy ones. On `cube-easy-0`, 24–36° clears the first spike but lands on a later one. So a small timing shift changes where the cube lands. With the fly's real spread (s.d. ~14°), real runs can do better or worse than the ideal fly on any one level.
  - So "the best any fly with this encoding could do" holds only roughly: ~29/50 for any single fixed threshold.
- **Step 2:** the ideal fly is run on the 20 held-out levels **together with the baseline**, at 39° only, and reported next to it. The held-out levels aren't looked at before then.
- **Deaths by obstacle type** in Step 2 use the same (a)/(b) classes, plus (c) short run-up (D45).

**D45. The cube encoding's rates scale with the patch: R × f** (2026-10-31)
Shannyn's proposal, after the interim dry run gave θ_full ≈ 1,165°. The whole-brain calibration and the recruitment runs waited for this, since the recruited set depends on the encoding. **Adopted after the check-3 rerun passed (below).**
- **Why the current encoding is a problem:**
  - At θ_full ≈ 1,165° the patch never passes ~15% of the neurons, even at contact. Jump timing is set by how long ~6–11 neurons fire at full R, not by the growing patch.
  - A 3° object barely expanding drives the Giant Fiber, which isn't biological: LC4/LPLC2 respond weakly to small, slow images.
  - The start gap becomes a hidden dial, and the spread near the target (59 ± 60° at θ_full = 2,880°) is several times the fly's (39 ± 14°).
- **Proposed: rate scaling.** The same patch and f, but each driven neuron fires at **R × f** instead of R. No new dial or constant: θ_full stays the only calibrated number, with the same target and method. A distant 3° object then drives ~5 neurons at a few Hz, and the total input grows steeply as it nears. (`CubeEncoder(rate_scaling=True)`, off by default until this is decided.)
  - Background (Shannyn, to be checked in her S3 reading before D41 changes): LC4 tracks angular velocity and LPLC2 angular size (von Reyn et al. 2017).
- **Dry run on the interim subcircuit, judged against a bar fixed before the run** (Shannyn's suggested numbers, agreed):
  1. calibrated θ_full ≤ ~360° (the patch grows to a large fraction of the neurons near contact);
  2. s.d. of the first-spike θ at the calibrated value ≤ ~28° (2× the fly's);
  3. the first-spike θ moves by < ~5° between start gaps of 600 and 1,200 units.
  - **If it passes:** D41 and D43 are updated and the change logged. **If it fails:** we discuss the LC4 = dθ/dt, LPLC2 = θ split (D41's later option).
- **The calibration start gap comes from the levels, not by choice** (agreed): the median run-up before an obstacle in the cube training suite, with sensitivity at the 10th and 90th percentiles.
  - Measured (`scripts/measure_run_up.py`): each obstacle's gap when it first becomes the nearest looming object, along the bot's path on the 50 cube training levels.
  - **What counts as a new approach (agreed 2026-10-31):** only a continuation of the same object is left out, i.e. a column touching the previous looming one with the same bottom and top (e.g. the second column of a two-wide block, 800 of 2,462). A touching column with a different top or bottom (a staircase step) is a new approach.
  - **Result: P10 30, median 245, P90 628 units** (n = 1,662). The dry run below used 270, from a first definition that also left out staircase steps (P10 115, median 270, P90 719). Counting every column gives 29 / 138 / 480.
  - **The P10 can't be a calibration start:** at 30 units a 30-unit spike already subtends ~53°, past the 39° target.
  - **Agreed (2026-10-31): the official calibration starts at 245 units** (the median, by the agreed rule, so not a choice). **Sensitivity is reported at the P25 (135 units) and the P90 (628 units)**, in place of the P10. The P25 had to be comfortably above the 39° point of a single block (~42 units, so ≥ ~60), and it is.
  - **Short run-ups:** **10.7%** of approaches start with the object already at or past 39° (after landings and staircase steps), so the fly can't respond "at 39°" there. The Step 2 death analysis adds **(c) short run-up** to D44's (a)/(b). The ideal 39° fly has no (c) deaths on the 50 training levels: it presses at once and clears them. The class matters for the real fly, which responds later.
  - Our earlier 600 is longer than 90% of real run-ups, so the first dry run's θ_full ≈ 1,165° came from an unusually long approach.
- **Dry run result (2026-10-31; interim subcircuit, R × f, R = 150 Hz, 10 trials per point, θ_full 90–540°, start gaps 270 / 600 / 1,200 / 115 / 719):**

  | Check (bar fixed before the run) | Result | |
  |---|---|---|
  | 1. calibrated θ_full ≤ 360° (judged at gap 270) | **204°** | pass |
  | 2. s.d. at the calibrated value ≤ 28° | **8.1°** | pass |
  | 3. first-spike θ shift, gap 600 vs 1,200, < 5° | 44.3° vs 39.0°: **5.3°** | **fail, by 0.3°** |

  - At θ_full = 204°, the first-spike θ per start gap: 115 → 41.4°, 270 → 39.0°, 600 → 44.3°, 719 → 41.1°, 1,200 → 39.0°. The calibrated θ_full from each gap alone: 196°, 204°, 191°, 197°, 204°.
  - The shift doesn't grow with distance: 1,200 matches 270, and only 600 is off. With ~8° s.d. and 10 trials, the uncertainty of a difference of two means is ~3.5°, so 5.3° can't be told apart from no shift. But the bar was set in advance and it isn't met as written. **Decision pending (Shannyn).**
  - At 39° the patch drives ~60 of 314 neurons (~19%), each at ~29 Hz. No trial got stuck.
  - **The calibrated 204° is close to the geometric 180°** (the old uncalibrated comparison): with R × f, calibration lands near the value geometry alone suggests.
- **Check 3 is rerun, with rules fixed before the run** (Shannyn, 2026-10-31): 30 fresh trials (new seeds, trials 10–39) at θ_full = 204°, start gaps 600 vs 1,200, judged alone (not pooled with the first 10), same bar (< 5°). **Pass:** R × f is adopted, and both the 10-trial fail and the 30-trial result are reported here. **Fail:** it's a fail, and we discuss the LC4/LPLC2 split.
- **Rerun result (2026-10-31): pass.** First-spike θ at θ_full = 204°: **37.6 ± 6.6° from 600 and 37.8 ± 10.6° from 1,200, a shift of 0.1°** (bar < 5°). 30/30 trials fired at each gap, none got stuck.
  - Both results are reported, as agreed: the first 10-trial run missed the bar by 0.3° (5.3°), and the fresh 30-trial run passes (0.1°).
  - **So R × f is adopted** for the cube encoding (the rule set before the rerun). D41's text is updated after Shannyn's von Reyn et al. 2017 check. Until then the code keeps `rate_scaling` as an explicit switch, and every run states which encoding it used.
- **Agreed with the rerun (2026-10-31), updating D43:**
  - **Comparison 1 is now the pre-D45 encoding:** flat rate R = 150 Hz, calibrated the same way (first Giant Fiber spike at 39°, same start gap, R = 150), and labelled "pre-D45 encoding". It shows the effect of the one encoding change we made after seeing data. It replaces θ_full = 180° in the Step 2 comparisons and in the recruitment runs (`preD45_flat_R150`). So the whole-brain calibration is run twice: R × f and flat R.
  - **R's range stays 25–200 Hz**, restated: R is the **peak per-neuron rate, reached near contact** (f = 1). At the 39° threshold each driven neuron fires at ~0.19 × R.
- **Official whole-brain calibration (2026-10-31, commit `c930c77`):** R = 150 Hz, start gap 245, 10 trials per θ_full, open loop, no trial stuck. Results in `results/calibration/whole_brain/` (git-ignored); values in `configs/recruitment.toml`.

  | Encoding | Grid (°) | **Calibrated θ_full** | s.d. at it | Neurons driven at 39° |
  |---|---|---|---|---|
  | **R × f (baseline of record)** | 90, 135, 180, 270, 360, 540 | **200°** | 8.5° | 62 of 314, each at ~29 Hz |
  | Flat R (comparison 1, pre-D45) | 360, 720, 1,440, 2,880, 5,760 | **1,082°** | 9.3° | 12 of 314, each at 150 Hz |

  - The whole brain's 200° is within 4° of the interim subcircuit's 204°.
  - **Sensitivity** (R × f at 200°, 20 fresh trials per gap): first Giant Fiber spike at **37.4 ± 8.5° from the P25 (135 units)** and **35.8 ± 8.8° from the P90 (628 units)**, against 39° at the median by construction. The start gap moves it by ≤ ~3°.
  - **Recording quirk, not a result:** with flat R at θ_full = 5,760°, 2 of 10 trials fired only after the spike's front face had passed the eye, where the encoding reads θ = 0 (the hitbox is smaller than the visual cell). So that row shows 0°. It doesn't affect the calibration, which comes from the 720–1,440° bracket.
  - With flat R, the Giant Fiber still fires with only ~8–14 neurons driven, so jump timing depends on integration time. That is what comparison 1 is there to show.

**D46. The final subcircuit: build, checks so far, and how rule 5 is judged** (2026-11-01)
Rule 5's method and settings proposed by Jacob and amended by Shannyn; agreed by both on 2026-11-01, before any rule 5 run.
- **Recruitment runs (2026-11-01, commit `66601f1`):** 70 whole-brain, bot-driven runs (10 levels × 7 settings, `configs/recruitment.toml`), 4 at once in 6 h 57 min. All completed; **none entered the stuck state**, so no frames were dropped (515,004 frames used).
- **Build** (`configs/subcircuits/final.toml`): **33,486 neurons, 3,392,494 connections** (24.2% / 22.5% of the brain).
  - The recruitment runs fired 1,250 neurons (per setting: 367 for flat R up to 1,207 at R = 200). All but **6** were already in the interim build (33,480), so the real encoding adds almost nothing the pathway tests hadn't recruited.
  - The Giant Fibers keep 87–88% of their input (82% of their inhibitory input), as in the interim build.
- **D36 rules 1–4 on the held-out probes: pass.** 248 conditions, same seeds as the whole brain. Same go/no-go verdicts; key-group rates worst 7.1% (DNp20 left in P6, 2.8 → 3.0 Hz); Giant Fiber first spikes 360/360 within one frame; lowest per-type share of active neurons kept 97% (P6).
  - 4 subcircuit trials entered the stuck state (3 on the whole brain): the 3 known cascades, plus one E4 control (LC10a), which isn't a game input.
- **Calibration reproduced: pass.** On the official calibration looms (same θ_full, trial and seed; `scripts/compare_calibration.py`), the Giant Fiber's first spike falls on **the same frame in 110/110 trials**: 60/60 R × f and 50/50 flat R.
  - **For the write-up (Shannyn):** the model's spread at the calibrated θ_full (s.d. 8.5°) is smaller than the fly's (14°), so the model is a less variable fly.
- **Speed (D37 limit, ≤ 10 h for 200 runs of 30 s, 4 at once): pass.** Stand-in input: 16.5× slower than real time each, ~6.9 h for the grid. Real levels, bot-driven, R × f at R = 150: 4 runs of ~30 s in 6.4 min, ~5.4 h for the grid.
- **Rule 5 is judged on bot-driven runs** (amends D36 rule 5 and D43's "closed-loop runs"):
  - **Why:** in fly-driven closed loop the two networks' games split at their first different jump, and the fly dies early on medium and hard levels (D44: 0/6 even for the ideal fly), so few actions would be compared. With the bot driving, both networks see identical input over the whole level.
  - **Levels:** cube training easy 4–5, medium 4–5, hard 2 (unchanged). Same Poisson seed on both networks.
  - **Unit: one obstacle approach**, from when an object becomes the nearest looming one until it stops looming. Each obstacle gives a burst of presses, so only **the first press of each approach** is compared.
    - **Matched** if both networks' first presses fall within **±1 frame**. **A miss** if only one network presses during the approach, or both do but further apart.
    - **Pass at ≥ 95% of approaches** in which at least one network presses. Approaches where neither presses are counted and reported, but left out of the share, so they can't inflate it (Jacob's reading; stricter than counting them as agreement).
  - **Settings (5):** R × f at the calibrated 200° with **R = 25, 150 and 200 Hz** (the Step 3 range; low R near threshold is the most fragile), plus the two Step 2 comparisons at R = 150: **flat R at 1,082°** and **"every object looms"** at 200°.
  - **Fixed in advance:**
    - If rule 5 fails at some R, that R is **dropped from the Step 3 range** until fixed.
    - If a comparison fails, that comparison **runs on the whole brain** instead.
  - **Fly-driven closed loop** on the same levels (R × f, R = 150) is reported as a description, not judged.

## Open

Still open:

- Subcircuit rule: decided in D36 (recipe) and D37 (cascade trials left out, tuning-time limit). The interim neuron list is built in J5; the final one after T4.
- Brain time, input encoding, output rule and the cube dials: decided in T4 (D40–D43). Ship mode is decided in Step 5.
- The cube encoding's rates: R × f, adopted in D45 (D41's text is updated after the von Reyn et al. 2017 check). Calibrated on the whole brain: 200° (R × f) and 1,082° (flat R).
- The final subcircuit: built, rules 1–4, the calibration and speed pass (D46). Rule 5 is next.
- Closed-loop simulation: resolved for now by D17 (Brian2 runtime with `run_frames`). Our own reimplementation of the same equations (e.g. PyTorch, validated against Brian2) stays an option if subcircuit runs are still too slow, or for the GPU phase.
