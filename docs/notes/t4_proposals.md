# Interface decisions (T4): neuroscience proposals for the cube

*Shannyn, 2026-10-30. Draft for discussion with Jacob. Nothing here is decided until it's logged in `docs/decisions.md`.*

T4 covers four open decisions (`docs/decisions.md`, "Open"): brain time per game step, the input encoding, the output rule, and the dials with their ranges. This note proposes all four for **cube mode** (Step 2), from the pathway results (`docs/pathway_results.md`) and von Reyn et al. 2014. Ship mode (Step 5) gets constraints only, at the end.

Every choice here is **our code, not the fly** (PROJECT_BRIEF §2). The aim is to make each one either fixed by geometry or biology, or an explicit dial, so nothing gets tuned by accident.

## 1. Brain time per game step

**Proposal:** brain time runs at **real game time**, and the brain is consulted **every physics tick** (240 Hz, one 4.17 ms frame per tick).

- **Why real time:** the timings that matter are physiological. One synaptic step takes 1.8 ms, and LC4/LPLC2 → Giant Fiber onset is 8–13 ms (E2). Running the brain faster or slower than the game would rescale them for no biological reason.
- **Why every tick, not every 60 fps frame:** a 16.7 ms frame is longer than the Giant Fiber's whole onset latency, so frame-level steps would blur the timing we just measured. With `run_frames` the cost depends on simulated time, not on how often we talk to the brain (FEASIBILITY, Benchmarks).
- **Order within a tick:**
  1. game state at tick *i* sets the input rates for brain frame *i*;
  2. the brain runs frame *i*;
  3. its Giant Fiber spikes set `held` for game tick *i* + 1.

  This adds one tick (4.2 ms) of delay, the same for every press.
- **Rounding:** the stepper rounds a 4.1667 ms tick to 42 steps of 0.1 ms (4.2 ms), so brain time runs 0.8% slower than game time (0.24 s over a 30 s level).
  - Option: alternate 42, 42, 41 steps, which averages exactly 4.1667 ms.
  - **Question for Jacob:** is that easy in `run_frames`? If not, accept the 0.8% and state it.
- **Dials:** none.

## 2. Input encoding (looming → LC4 / LPLC2)

**Proposal:** compute how large the nearest approaching object appears to the fly, and drive a **growing patch** of LC4 and LPLC2 neurons whose size tracks it.

### 2a. How big the obstacle looks

- **The eye** sits at the cube's front face (x + 15), at the cube's centre height, looking along the direction of travel.
- **Which objects loom:** every gameplay object (solid or hazard) ahead of the eye whose vertical extent overlaps the cube's (30 units), i.e. objects on a collision course.
  - The fly can't tell hazards from solids, so neither can the encoding. A block the cube must jump onto looms just like a spike.
  - Objects that don't overlap the cube vertically (a ceiling overhead) don't loom, because they aren't on a collision course. **This is a geometric choice that happens to help the cube run under ceilings. It must be stated as ours** (PROJECT_BRIEF caveat 4).
- **The object's size** is its visual grid cell (30 units), not its hitbox. A spike looks like a 30-unit object even though its hitbox is 6 × 12.
- **Angular size:** θ = 2·atan(15 / *d*), where *d* is the gap from the eye to the object's near face.
- **Several objects:** use the nearest one (the largest θ).

At 311.58 units/s (`docs/game_physics.md` §2), this gives:

| Gap *d* (units) | θ | Time to contact | θ / 180° |
|---|---|---|---|
| 300 | 5.7° | 963 ms | 3% |
| 150 | 11.4° | 481 ms | 6% |
| 100 | 17.1° | 321 ms | 10% |
| **73** | **23.2°** | **234 ms** | **13%** |
| 50 | 33.4° | 160 ms | 19% |
| 30 | 53.1° | 96 ms | 30% |
| 15 | 90.0° | 48 ms | 50% |

**The game's single-spike press window** (gap 1–73 units, `docs/game_physics.md` §3) **is exactly "press once the obstacle exceeds ~23°".** So a fly that escapes at a fixed angular size, as von Reyn et al. 2014 found, could clear spikes if its threshold lands between ~23° and roughly 90°, allowing for its ~10 ms latency.

The object's size-to-speed ratio is r/v = 15 / 311.58 = **48 ms**. That's inside the range von Reyn et al. used (8–140 ms), and close to their 40 ms condition. So the game's looms are in the range real flies were tested on.

### 2b. Which neurons are driven

- **Patch size:** on each side, a fraction **f = min(1, θ / θ_full)** of the LC4 neurons and the same fraction of the LPLC2 neurons are driven.
  - Default **θ_full = 180°**, i.e. an object filling the frontal half of the visual field drives the whole population. This is a simple geometric assumption, not a measured receptive-field layout.
  - **Both sides** are driven equally, because obstacles approach head-on.
- **Patch shape:** neurons are added in a fixed order that grows a contiguous patch. We don't have visual-field positions for LC4/LPLC2 in our data, so neighbours are approximated by **shared input partners**: start from a seed neuron, then add neurons in order of input overlap, separately for LC4 and LPLC2. This is the same construction as probe P5.
  - **The seed is fixed by rule** (chosen once with a fixed random seed and logged), never tuned. Location matters (Dombrovski et al. 2023 found LPLC2 → Giant Fiber synapse strength varies with visual-field position), so a tuned seed would be a hidden dial.
  - **Later refinement:** replace the input-overlap order with real positions (e.g. synapse coordinates from FlyWire/Codex).
- **Rate:** every driven neuron fires at the same Poisson rate **R**. Undriven neurons get 0 Hz.
- **Logged every tick** (hard rule 10): θ, f, R, and which neurons are driven, kept separate from the fly's spikes.

**Alternative, kept for later:** split the features. LC4 tracks how *fast* the object expands and LPLC2 how *big* it is (von Reyn et al. 2017; Ache et al. 2019). So LC4's rate could follow dθ/dt and LPLC2's patch could follow θ. That's closer to the biology but adds mapping constants, so it's better as a Step 3+ refinement once the simple version works.

### 2c. What to expect from the untuned version (Step 2 baseline)

A rough prediction from E3 (LC4 alone at 150 Hz: 5 neurons fired the Giant Fiber in half the trials; 12 neurons in all, with a 23 ms first spike):
- With θ_full = 180°, about 10% of LC4 (5 per side) is reached at θ ≈ 17°, a gap of ~100 units, **~320 ms before contact**. Adding LPLC2 and both sides probably lowers the threshold further.
- **So the untuned baseline will probably jump too early**, before the ~23° window opens, and land on the spike.
- This is a prediction to record before Step 2, not a reason to change the defaults. The baseline is meant to be untuned.

## 3. Output rule (Giant Fiber → jump)

**Proposal:** `held` is true on a tick **if either Giant Fiber spiked in the previous brain frame**, false otherwise. No spike count, no threshold, no refractory window.

- **Why one spike:**
  - A single Giant Fiber spike drives the jump and wing-depressor muscles. In tethered flies, leg extension followed each spike by 0.9 ms and flight initiation by 2.0 ms.
  - Real looms caused one or two spikes (von Reyn et al. 2014).
  - "Jump on any spike" is the closest match, and it needs no dial.
- **Why either Giant Fiber:** there's one cube and two Giant Fibers, and either one's spike triggers a jump.
- **Why no refractory window is needed:**
  - The cube only jumps when it's on the ground (`docs/game_physics.md` §3), so spikes in mid-air do nothing.
  - Each press lasts one tick, so holding never re-jumps by itself.
  - The firing that continues after a loom ends (up to ~13 ms at 25 Hz input, ~30 ms at 150 Hz; E2) is over long before a 429 ms jump lands.
  - A jump on landing only happens if the Giant Fiber is firing *then*, i.e. if the next obstacle is already looming. That's the fly's response, not a rule artefact.
- **What it gives up:** the model's Giant Fiber fires at 100–200 Hz while driven, against one or two spikes per loom in a real fly. The rule takes the first spike and makes the rest irrelevant. The README must still say the model's rates are unrealistic.
- **Stuck runs (D37):** a run that enters the stuck mushroom-body state is flagged. If its Giant Fibers stay silent (`docs/cascades.md`), the cube just stops jumping, and the run is counted as it is.
- **Alternatives considered:**
  - N spikes within a window: adds a dial, and real flies jump on one spike.
  - Press while firing, plus a refractory window: needed only if presses lasted longer than one tick.

## 4. Dials and ranges

D5 allows at most 2–3 dials. Proposal for the cube:

| Dial | Default (Step 2 baseline) | Range for tuning (Step 3) | Why this range |
|---|---|---|---|
| **R**, the stimulation rate of driven neurons | 150 Hz (Shiu's default) | 25–200 Hz | The range tested in E1 and E3; everything in it drives the Giant Fiber reliably |
| **θ_full**, the angular size at which the whole population is driven | 180° | 90–720° | Sets the angular size at which the Giant Fiber first fires. 720° puts 10% of LC4 at ~70°, inside the press window |

Not dials: brain time (fixed, real time), the output rule (one spike), which objects loom (geometry), object size (grid cell), patch order and seed (fixed by rule).

**The third dial is kept for ship mode.**

**A biology-based alternative to tuning θ_full:** fix it so the model's Giant Fiber first fires at the real Giant Fiber's angular threshold. von Reyn et al. 2014 plot that threshold in their Fig. 5b (to read off). It would then be calibrated to the fly, not tuned to the game, and leave only R as a cube dial. **Worth deciding before Step 3.**

## 5. Ship mode (Step 5): constraints only

- **Horizontal motion drives the steering output:** T4a/b + T5a/b at 50 Hz drove VS cells to 65 Hz and DNp20 to 64 Hz (S3), against 104 Hz for downward motion. Any ship encoding that drives horizontal-motion neurons, for example to represent the scrolling level, must account for this.
- **If scrolling is encoded at all,** it should be front-to-back motion on both eyes (T4a/T5a only), as for a fly moving forward. Not T4a/b together, which isn't a real motion.
- The ship's output rule (DNp20 → hold/release) and encoding are a Step 5 decision.

## Questions for Jacob

1. Can `run_frames` alternate 42/42/41 steps per frame, or do we accept the 0.8% drift?
2. Can the engine give the interface the objects ahead with their vertical extent? Or should the interface read them from the level file and use `game.player`?
3. Are θ_full and R the right two dials, or would you rather calibrate θ_full to the real angular threshold and keep a dial in reserve?
4. Should the Step 2 baseline also record runs with the opposite looming choice (every object ahead looms, not just ones on a collision course), so we can show how much that geometric choice helps?

## Sources

- `docs/pathway_results.md` (E1–E3, E2 offsets, S3); `docs/game_physics.md` §2–3; `docs/game_engine.md`; D23, D27, D36, D37.
- von Reyn CR et al. (2014). A spike-timing mechanism for action selection. *Nat Neurosci* 17:962–970.
- von Reyn CR et al. (2017). Feature integration drives probabilistic behavior in the *Drosophila* escape response. *Neuron* 94:1190–1204. (Not yet read; cited for LC4's role; check citation details.)
- Ache JM et al. (2019). Neural basis for looming size and velocity encoding in the *Drosophila* giant fiber escape pathway. *Curr Biol* 29:1073–1081. (Not yet read; cited for LPLC2's role; check citation details.)
- Dombrovski M et al. (2023). Synaptic gradients transform object location to action. *Nature* 613:534–542. (Not yet read; cited for position-dependent synapse strength; check citation details.)
