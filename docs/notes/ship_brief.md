# Ship mode (Step 5): engineering brief for the design

*Jacob, 2026-11-05. Facts and open questions for Shannyn's ship design (she leads Step 5). Nothing here is a decision: the options in section 4 are there to show the trade-offs, not to pick one. Sources are linked so every number can be checked.*

**Agreed so far:** ship mode stays in the project whatever happens in Stereo Madness (Jacob, 2026-11-05; to be logged with Shannyn at the start of Step 5). Whether to tune the ship, or keep it untuned with its baseline and key controls only, is decided after the ship baseline.

## 1. What the game needs from the fly

**The input is one bit per tick: hold or release** (`game.tick(held)`), exactly as for the cube. In ship mode (`docs/game_physics.md` §4):
- **Holding** pushes the ship up: `vy += 0.9582 × 0.225 × k` per tick, with k = 0.5 while falling and 0.4 while rising.
- **Releasing** lets it fall: `vy −= 0.9582 × 0.225 × 0.4 × m`, with m = 1.2 while rising and 0.8 while falling.
- **Speed limits:** −6.4 ≤ vy ≤ +8.0 units per frame.
  - From rest, holding reaches full climb in 93 ticks (0.39 s).
  - From full climb, releasing reaches full fall in 170 ticks (0.71 s).
- **The play area is 300 units high** (10 blocks). The floor and ceiling don't kill: the ship slides along them.
  - Hitting a block's underside bumps the ship down without killing it.
  - Hazards (spikes) and block faces kill.
- **So the ship needs graded, sustained control, not a single event.** A cube press is one tick. A ship needs the button held for tens to hundreds of ticks at a time, and to alternate. That's the main difference from the cube's output rule (D42: any Giant Fiber spike means a one-tick press).

## 2. What's on screen (the levels)

**Generated ship levels** (`docs/level_generators.md`):
- **Count:** 50 training levels (easy 20, medium 20, hard 10) and 20 held-out (8 / 8 / 4). All are bot-validated.
- **Layout:** a ground-level area, floor at 0 and ceiling at 300.
- **Chunks:**
  - floor pits plus hanging spikes (`spiked_corridor`);
  - an opening that drifts up or down (`tunnel`);
  - columns from the floor or ceiling (`pillar`).
- **Difficulty:**
  - the opening is 5 rows (150 units) on easy, 4 on medium, 3 (90 units) on hard;
  - the gap between chunks is 1.0–1.5 s on easy and 0.5–0.8 s on hard.
- **Mixed levels** (for Step 6) alternate cube and ship sections of 6–9 s each, with 1 s of clear travel around each portal.

**Stereo Madness** (`docs/game_physics.md` §10):
- **Two reachable ship sections,** one from 25.5 s to 40.2 s and one from 73.4 s to the end. The third ship portal can't be reached.
- **The first ~25 s is cube.** On held-out cube levels the untuned fly completes only easy levels, so in many runs it may never reach the first ship portal. That's why the ship is judged mainly on the generated ship levels.

## 3. What the brain gave us (pathway tests, whole brain, original signs)
From `docs/pathway_results.md` (S1–S3) and `docs/FEASIBILITY.md`:
- **"Down" motion** (T4d + T5d, right eye) drives the right VS cells (113–241 Hz) and DNp20 (73–140 Hz) in 10/10 trials at every rate (25–200 Hz). It also drives DNp22 (101–150 Hz). The left VS cells stay at 0.
- **"Up" motion** (T4c + T5c) gives exactly 0 in VS and DNp20, because it reaches them only through inhibitory LPi neurons. Added to "down", it suppresses it strongly (S2: at "down" 50 Hz, adding "up" 200 Hz takes DNp20 from 104 to 18 Hz). LPi09 rises at the same time (63 → 188 Hz).
- **Horizontal motion also drives the pathway:** at 50 Hz, VS reaches 65 Hz and DNp20 64 Hz, against 104 Hz for "down" (S3). It still passes D31 rule 3.
  - **T4 constraint:** if scrolling is encoded at all, it should be front-to-back motion on both eyes (T4a/T5a only), as for a fly moving forward. Any ship encoding must account for this drive (`docs/notes/t4_proposals.md` §5).
- **Output candidates:**
  - **DNp20 (DNOVS1):** the strongest VS-driven descending neuron, with 82 / 182 synapses from 6 / 8 VS cells.
  - **DNp22 (DNOVS2 or 3):** weaker, 42 / 35 synapses from 2 VS cells per side.
- **The known risk (D39):** in the real fly, DNp20 and the DNOVS neurons mainly move the head, so the ship is the more fragile claim. The model fires VS cells at high rates under direct drive, while real VS cells signal mostly with graded potentials.
- **The subcircuit:**
  - It keeps ~99–100% of the VS cells' input and 91–97% of DNp20/22's (`docs/FEASIBILITY.md`). Its steering key-group rates passed D36's tolerance on the held-out probes, worst 7.1% (DNp20 left, 2.8 → 3.0 Hz).
  - **But:** its closed-loop check (rule 5) and the recruitment runs that built it were all **cube**. Any new input population (e.g. T4c/T5c, or the left eye) needs checking before ship runs on it (§5).

## 4. Design questions (for Shannyn), with the options as I see them

**Q1. What does the fly see in ship mode?** This decides what the claim can be, like D41 did for the cube.
- **(a) Its own vertical motion (self-motion optic flow).**
  - Climbing makes the scene move down past the eye; falling makes it move up. Drive "down" T4d/T5d by vy when climbing, and "up" T4c/T5c when falling.
  - **For:** close to what VS cells do in the fly (they signal self-rotation), and nothing about the obstacles is precomputed.
  - **Against:** it's a stabiliser. It holds a level course but knows nothing about where the opening is, so it would mainly pass easy levels by luck.
- **(b) Where the opening is (an error signal).**
  - Our code finds the next gap and drives "down" when the gap is below the ship and "up" when it's above.
  - **For:** it can actually fly the levels.
  - **Against:** like looming, the answer is built into our input, so the fly is close to a relay plus a sign. We'd have to say so, as we do for the cube (caveat 1).
- **(c) Obstacle edges as local motion** (closer to real optic flow): the scene's edges move across the eye as the ship moves.
  - **For:** the most biological option.
  - **Against:** the most work, and the hardest to calibrate.
- **Any mix**, and whether scrolling is encoded at all (front-to-back on both eyes only, per T4).

**Q2. How do spikes become hold and release?** The output rule, as D42 was for the cube.
- **Which neuron:** DNp20 alone, DNp20 + DNp22, one side or both.
- **Which spikes mean which action:**
  - "hold while DNp20 fires within the last *w* ms" (*w* is a window, possibly a dial);
  - "release while it fires";
  - or an opponent pair, e.g. right "down" pathway against left, or DNp20 against an "up" readout (LPi09).
- **The default with no spikes:** with "hold while firing", silence means falling; with "release while firing", silence means climbing. That changes what a silent control network does (cf. the cube's never press / always press).

**Q3. Which population and how many neurons:** T4d/T5d and T4c/T5c, right eye only (as in the tests) or both eyes, and a patch-size scaling like R × f (D45) or a flat rate.

**Q4. Dials and calibration:**
- **The dials:** at most 2–3 overall (D5). The cube uses one (R) and kept two spare for the ship (T4 §4).
- **A real-fly anchor to calibrate to,** as θ_full was calibrated to 39° (D43). For example, a VS or DNOVS response to a known motion speed from the literature.
  - This is the hardest open question: without an anchor, the "untuned" ship settings have no biological footing.

**Q5. Which subcircuit checks (§5) are needed, or should the ship run on the whole brain?**

## 5. Engineering consequences (my side, whatever the design)

**Built and reusable as they are:**
- the engine's ship physics;
- the ship bot (it beats Stereo Madness's ship sections);
- the recorder and replays;
- the death classes' framework (D48), though the ship needs its own classes;
- the step-by-step analysis, as in Steps 2–4.

**To build, with rough times:**

| Piece | Time |
|---|---|
| Ship no-brain references: never hold, always hold, random holds; and an ideal-ship reference if the design has a natural one, like D44's ideal 39° fly | ~0.5–1 h, buildable now |
| A closed loop that works in any mode: a per-mode encoder and output rule, switching at portals. Today's loop is cube-only: in a mixed level it would treat a Giant Fiber spike as "hold" in ship mode. | ~3–4 h |
| The ship encoder and output rule, once designed | ~0.5–1 day |
| Calibration of the ship dial(s) against the chosen anchor | ~0.5 day + runs |
| **The subcircuit for ship:** pathway tests and recruitment with the ship encoding, then a rule-5-style closed-loop check. Or run the ship on the whole brain: ~3× slower, but no check needed. | ~1 day + runs, or 0 |
| Ship death classes and the Step 2-style analysis | ~0.5 day |

**Run time:** a ship level plays its full 30 s more often than a cube level. Expect a held-out batch (20 levels × 3 seeds) of ~1–2 h on the subcircuit, or ~3–6 h on the whole brain.

## 6. What's needed from Shannyn to start
1. Answers to Q1–Q4 (Q5 can follow), as a draft like `docs/notes/t4_proposals.md`.
2. The real-fly anchor for calibration (Q4), with its source.
3. Whether a ship tuning step happens is decided after the ship baseline, as agreed.
