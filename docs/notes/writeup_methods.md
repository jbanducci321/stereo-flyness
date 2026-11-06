# Write-up: methods (draft, Steps 0–3)

*Jacob, 2026-11-06. A first draft for Step 8, written early from settled decisions only. No result here is new: every number is copied from the decision log or the notes it cites, with its source. Shannyn leads methods in the write-up (PROJECT_BRIEF §8), so this is for her to rewrite, cut or reorder. Sections marked **[Shannyn]** are outlines where the biology framing is hers to write. Steps 4–7 and the ship are added once their results are in.*

## 1. The brain model

**Connectome and model.** We use the FlyWire FAFB v783 connectome (138,639 neurons, 15.1M connections, 54.5M synapses) and the leaky integrate-and-fire model of Shiu et al. 2024 (D2, D3). The model's code is vendored unchanged (D14), with its default parameters:

| Parameter | Value |
|---|---|
| Resting and reset potential | −52 mV |
| Threshold | −45 mV |
| Membrane time constant | 20 ms |
| Synaptic time constant | 5 ms |
| Refractory period | 2.2 ms |
| Synaptic delay | 1.8 ms |
| Weight per synapse | 0.275 mV |
| Poisson input weight factor | 250 |

- **Weights** come from synapse counts and **signs** from machine-learning neurotransmitter predictions (Eckstein et al. 2024). Both are frozen for the whole project (D5). We tune at most 2–3 interface dials, and so far tuned one (§5).
- **Reproduced first** (`docs/FEASIBILITY.md`): sugar GRN stimulation drives MN9 at 67.7 ± 5.2 Hz at 100 Hz input (Shiu's reference 67.0 Hz), with ~400 active neurons. One sugar GRN ID was re-segmented in v783 and replaced (D15); every ID we use is checked against v783.
- **Not in the data, and so not in the model** (D39): the ventral nerve cord (so the Giant Fiber → jump muscle step is outside it), gap junctions, adaptation and noise.

**Stepping the model frame by frame** (D16, D17, D40). Shiu's Poisson input fixes its rate when the network is built, but the game needs it to change every frame.
- Each stimulated neuron gets its own Poisson source with the same event probability, weight, target and timing as Shiu's input, but with a rate that can change at any time. On the whole brain it matches the original (MN9 67.8 vs 67.7 Hz) and follows on/off switching within ~2 frames (D16).
- All frames run inside one Brian2 run, with a callback at each frame boundary that reads spikes and sets the next frame's rates (D17).
- **Brain time equals game time:** one brain frame per 240 Hz game tick, exactly 1000/240 ms (Brian2 alternates 42, 42 and 41 steps of 0.1 ms, with no drift) (D40).

**[Shannyn] The two pathways and why we used them:** LC4/LPLC2 → Giant Fiber (DNp01) for the cube's jump; T4/T5 → VS cells → DNp20/DNp22 for the ship. Cell counts and synapses are in `docs/FEASIBILITY.md` (target-neuron table).

## 2. Pathway tests (Step 0)

Before any game, we tested whether the model carries the signals the game needs, with every rule written before the results (D28–D35; design in `docs/pathway_tests.md`).
- **Escape (E1–E5):** Poisson stimulation of LC4 and/or LPLC2 at 0, 25, 50, 100, 150 and 200 Hz, 10 trials each, watching both Giant Fibers. Judged by D29's four go/no-go rules (it responds, rises with input, the stimulated side dominates, and its latency is fast and consistent enough for the game). Controls: no input must give exactly 0 spikes (D30); LC10a and sugar input as specificity controls.
- **Steering (S1–S3):** "down" (T4d/T5d), "up" (T4c/T5c) and horizontal motion, judged by D31's rules. Every steering test ran on both the original signs and a copy with every T4/T5 connection set to excitatory, because the predicted signs mark ~13% of T4d/T5d inhibitory, against known cholinergic biology (D27). **The original is the main version** (D28).
- **Recording:** every neuron that fires, frame by frame, stored sparsely (D34).
- **Data rules** (D33): no analysis before a round finishes, frozen code during a round, every file records its git commit.

**[Shannyn]** One paragraph on what GO does and doesn't mean (D39: the model can carry the signals; not yet evidence the fly can play).

## 3. The subcircuit

The whole brain runs ~16–26× slower than real time on a laptop, too slow to tune. So the cube's runs use a subcircuit, built by a rule fixed before it was validated (D36, D37, D46).
- **Rule:** every neuron that fires in whole-brain runs of the game's inputs; plus every neuron with a connection of ≥ 30 synapses onto one of them; plus every neuron the tests stimulate or watch. All connections between kept neurons are kept, with unchanged weights.
- **Runaway-cascade trials are left out of the build** (D37). The model can enter a self-sustaining state (~8,300 neurons, centred on the mushroom body). We treat it as a property of the model, not the fly (§7).
- **The final subcircuit** adds 70 whole-brain, bot-driven runs of the real game encoding (D43, D46): **33,486 neurons and 3,392,494 connections** (24.2% / 22.5% of the brain).
- **Validated against the whole brain** by D36's five rules, agreed before validation, on held-out probes and levels it wasn't built from:
  1. the same go/no-go verdicts;
  2. key-group rates within 10% (or 1 Hz);
  3. Giant Fiber first spikes within one frame in ≥ 95% of events;
  4. ≥ 90% of active neurons kept;
  5. in the game, the same first press per obstacle approach within ±1 frame in ≥ 95% of approaches.

  It passed all five, with rule 5 judged on bot-driven runs, so both networks see the same input (D46).
- **Step 7 compares the two networks again in fly-driven play** (`docs/notes/step7_proposal.md`).

## 4. The game

**Our own minimal Geometry Dash** (D6, D8, D20): cube and ship modes only, the only modes Stereo Madness uses. Physics follow Geometry Dash 2.2 exactly for everything that affects play, in native units:
- 240 Hz ticks;
- 311.58 units/s forward speed (1 block = 30 units);
- jump velocity 11.18;
- gravity 0.958 per frame²;
- the ship's hold and release accelerations.

Every value is cited in `docs/game_physics.md`, and no code is copied from the reverse-engineered references (D8, D20).
- **One input:** the button is held or not, each tick (D23). The engine is deterministic, and replaying a run's logged inputs reproduces it exactly.
- **Levels are hitboxes** in JSON (D22). A search bot validates them: it must beat a level before we use it (D24).
- **Practice levels** (D26): seeded, generated from a physics-based chunk library, in easy, medium and hard tiers. Difficulty is measured in reaction time and press windows, never taken from Stereo Madness's layout (D7).
  - **Suites:** training, 50 cube, 50 ship and 50 mixed levels; held out, 20 of each from a separate seed range, never used for tuning.
  - Tuning levels are 30 s long (D37).
- **Stereo Madness** is converted from the official main-level data and cross-checked against an archived server copy (all 1,399 gameplay objects identical, D21). The bot beats it (D24). **It is the held-out final test: never tuned on, run once with everything frozen** (D7). The level data stays local (D9).

## 5. The cube interface

**[Shannyn]** The biological rationale for each choice below (the Giant Fiber's takeoff response, the angular-size threshold, LC4/LPLC2 tuning).

**Input: what the fly sees** (D41, D45, D47).
- **The eye** sits at the cube's front face, at its centre height.
- **Objects are seen as visual cells,** not hitboxes. Each fills a 30 × 30 cell, clipped at the ground (D47). Touching cells in a column merge into one object.
- **Only objects on a collision course loom:** those ahead that overlap the cube's current height. θ is the nearest such object's angular size, from geometry.
- **On each eye,** the fraction f = min(1, θ / θ_full) of the LC4 neurons and the same fraction of the LPLC2 neurons are driven. Neurons are added in a fixed patch order grown by shared input partners.
  - Each driven neuron fires as a Poisson source at **R × f** (D45). R is the peak rate near contact.
- **Choices we state as ours** (D41): objects off the collision course don't loom, and objects the cube lands onto are invisible to the encoding.

**Output: from spikes to presses** (D42). If either Giant Fiber spikes in brain frame *i*, the button is held on game tick *i* + 1; otherwise it isn't. There is no threshold, count or refractory window. The cube only jumps from the ground, so mid-air presses do nothing.

**Order within a tick** (D40): the game state at tick *i* sets the input for brain frame *i*. The brain runs frame *i*, and its spikes set the button for tick *i* + 1. That's one tick of delay, the same for every press.

**One calibrated number, one dial** (D43, D45).
- **θ_full is calibrated to the fly, not tuned:**
  - the target is the mean angular-size threshold of Giant Fiber-driven takeoffs in von Reyn et al. 2014 (Fig. 5b, r/v = 40 ms), **39° (s.d. 14°)**;
  - on the whole brain, open loop, at R = 150 Hz, from the training levels' median run-up (245 units), the Giant Fiber first spikes at 39° when **θ_full = 200°** (model s.d. 8.5°).
- **R is the only dial,** within 25–200 Hz. Brain time, the output rule, what looms and the patch order are all fixed, not dials (D43).

**References each result is read against** (D44, D48). None needs a brain.
- **The ideal 39° fly:** presses one tick after the looming object reaches 39°.
- **Never press:** the floor.
- **Random presses:** chance, at the fly's own press rate per level.
- **Always press:** added for Step 4.

## 6. Runs and analysis

**Every closed-loop run is recorded and replayable** (D19, D34, D38). Each run logs, per frame:
- our input (θ, f, rate, driven counts), kept separate from the fly's spikes;
- the watched spike counts;
- the press;
- every neuron that fired;
- the stuck-state flags.

Each run also records its seed, settings and git commit. A run is checked by replaying its logged presses, which must rebuild it exactly.

**Rules fixed before the results** (D33, D48, D49).
- Every analysis plan was agreed in writing before the runs it judges, and held-out results stayed unseen until both of us opened them together.
- Held-out runs print only progress and stuck flags while they run.
- Analysis code is checked on training runs that don't count.

**Measures** (D48).
- **Results:** runs completed and mean progress, by difficulty.
- **Death classes:** each death gets exactly one class, decided by replaying from the last approach where the cube could still act, with the ideal fly taking over. The classes are (s) stuck, (a) invisible, (c) short run-up, (b) the encoding's limit, (d) the fly's timing (d1 earlier, d2 later, d3 no jump), and (u) unclassified.
- **Per obstacle approach:** θ at the first Giant Fiber spike, and press timing.

**Statistics** (D48, D49).
- **Seeds:** the input is Poisson, so each setting runs at three fixed seeds.
- **Comparing two settings:** per level, each setting's median run across the seeds. "Equal" means both completed, or both died on the same object; otherwise the one that got further is better. Then a two-sided sign test across levels, with "better" or "worse" only at p < 0.05.
- **Noise line:** seed against seed, reported as context.
- **Step 3 tuning** (D49): R from 25, 50, 75, 100, 150 and 200 Hz on the 50 training levels at seed 0, scored by mean progress. The tie margin is measured from seed-to-seed noise, and ties break toward the open-loop threshold closest to 39°. The pick is checked once on the held-out levels at three seeds.

**Which R goes forward** (D50): 150 Hz, calibrated to the fly, is the fly of record. 50 Hz (Step 3's pick) runs beside it on Stereo Madness as a labelled variant, always reported second. Both were fixed before any Stereo Madness run.

## 7. Model properties we report, not fix

**[Shannyn]** Short framing for each:
- **The stuck state** (D37, D38): flagged when ≥ 50% of the 8,189 stuck-state neurons fire over ~100 ms. Stuck runs are kept and counted, and also reported with them left out, with no reruns.
- **Unrealistic rates:** the model's Giant Fiber fires at 100–200 Hz while driven, against one or two spikes per loom in the fly (D42).
- **Carry-over:** with no adaptation, ~15–20% of approaches start while the Giant Fiber is still firing from the previous object (D48).
- **The model is less variable than the fly:** first-spike s.d. 8.5° against 14° (D46).
- **Our input builds in the eye's processing:** looming and direction selectivity are given, not computed by the fly's earlier visual system (D39).

## Still to add
- **Step 4** controls and lesions (D51), after the joint opening.
- **Step 5** ship interface, after Shannyn's design.
- **Step 6** Stereo Madness: N, seeds and the showcase replay rule.
- **Step 7** whole brain against the subcircuit (D52, once logged).
- **The replay viewer and brain panel** (D19, D25, R3).
- **Reproducibility:** the uv lockfile, data checksums, run commits, and the exact commands.
