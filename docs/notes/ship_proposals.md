# Ship interface (Step 5): neuroscience proposals

*Shannyn, 2026-11-10. Draft for discussion with Jacob. Nothing here is decided until it's logged in `docs/decisions.md`. Answers Q1–Q5 of `docs/notes/ship_brief.md`, using the reading and connectome checks in `docs/notes/ship_reading.md`.*

*Updated 2026-11-10 with Jacob's answers. Items marked **Agreed (2026-11-10)** are settled between us, and get logged in one D entry with the rest of the ship design once Q1 is chosen. Superseded: an earlier rule of "hold while DNp22 spiked within w ms" (positive feedback: climbing → downward image motion → DNp22 → hold → faster climbing) and a fixed scenery distance of 825 units (edge geometry gives real distances, §1b).*

As for the cube (`docs/notes/t4_proposals.md`), every choice here is **our code, not the fly**. The aim is that each one is either fixed by geometry or biology, or an explicit dial.

## Summary

| Question | Proposal |
|---|---|
| Question | Proposal | Status |
|---|---|---|
| Q1. What the fly sees | **Image motion from geometry:** how fast the scene moves up or down across the eye in fixed viewing directions, computed from the level, as θ is for the cube | Encoder details agreed; the choice of full geometry vs. self-motion only waits for the ideal ships (§1d) |
| Q2. Output rule | **DNp22** (≈ DNOVS2), both sides. Any spike in a frame means **release** on the next tick; otherwise **hold** | **Agreed (2026-11-10)** |
| Q3. Input neurons | **T4d/T5d** for downward image motion and **T4c/T5c** for upward, **both eyes** (left–right asymmetry stated), all neurons of each type driven together | **Agreed (2026-11-10)**, with a left-eye-only test before the baseline |
| Q4. Anchor and dials | Full drive at **30°/s** (T4/T5 peak, Maisak et al. 2013), fixed. One dial, **R_ship**, the peak rate; untuned baseline 150 Hz | Proposed |
| Q5. Network | **Whole brain** for the ship, so no new subcircuit checks | **Agreed (2026-11-10)** |

## 1. Q1: what the fly sees

### 1a. Why image motion

- Our ship pathway (T4/T5 → VS → DNp22) is a **motion** pathway, so its honest input is the image motion the eye would see. Feeding it the opening's position (brief option b) would make motion detectors carry a signal they don't carry in the fly.
- This parallels the cube: there, our code computes angular size from geometry and drives looming detectors; here, it computes angular velocity from geometry and drives motion detectors.
- Real flies control altitude with three visual reflexes (Straw et al. 2010): **edge tracking**, **wide-field stabilization** and **expansion avoidance**. VS cells encode wide-field vertical motion, the input to stabilization.

### 1b. Geometry

- **The eye** sits at the ship's front face, at its centre height (as for the cube).
- **What it sees:** the edges of every visual cell ahead (blocks and spikes, as 30 × 30 cells clipped at the ground, D47), plus the floor and ceiling of the ship area.
- **Each edge's elevation** seen from the eye: φ = atan(Δy / *d*), with Δy the edge's height above the eye and *d* its distance ahead.
- **Its image motion** follows from the ship's velocity (vx forward, vy up):

  dφ/dt = (vx · Δy − vy · *d*) / (*d*² + Δy²)

  - The **vy term** is the ship's own climb or fall: climbing moves every edge down across the eye.
  - The **vx term** comes from flying forward: edges above the eye move up, edges below move down, faster when closer. Example: an edge 150 units below and 150 ahead moves down at ~60°/s from forward flight alone.
- **Pooling over viewing directions. Agreed (2026-11-10), Jacob's proposal:**
  - The eye looks in **fixed directions every 5° of elevation**, from straight down to straight up. In each direction, the nearest surface is what it sees, and its image motion is dφ/dt above.
  - **Why directions, not edges:** VS cells integrate motion over the area of the visual field, not over objects. A plain mean over edges would let a row of small spikes outweigh one long wall.
  - **Why 5°:** close to the angle between neighbouring facets (ommatidia) of the *Drosophila* eye, so each direction stands for roughly one point of the fly's view.
  - The pooled signal is the **mean over all directions**. Downward means drive the "down" input and upward means drive the "up" input (§3).
- **Field of view. Agreed (2026-11-10):** **600 units ahead** (20 blocks, ~2 s of flight) and the **full height** of the ship area, floor and ceiling included. Farther edges barely move.
  - **A direction that sees nothing within range counts as zero motion,** and stays in the mean, so empty directions can't silently change the average.
- These are choices of ours, stated and logged with the design.

### 1c. What this lets us claim, and what it doesn't

- **The stabilising part** (countering the ship's own climb and fall) matches a known fly reflex, wide-field stabilization (Straw et al. 2010), and what VS cells encode.
- **Any steering toward openings is our test, not a known fly behaviour.** In Straw's experiments, flies set their altitude from the *position* of horizontal edges, through a circuit nobody has identified. Here, steering can only come from the motion pathway.

### 1d. A problem to check before fixing this: the forward-flight term

The output rule (§2) makes the ship follow the scene's motion: downward motion → release → descend. That's the stabilising direction for the ship's own movement. But the **vx term** means:
- edges below move down, so the ship is pushed **down**, and more strongly the closer they are;
- edges above move up, so the ship is pushed **up** toward them.

So **the ship may be pulled toward whichever surface is nearest**, the opposite of keeping clear. Insects that balance optic flow (e.g. bees centring in a corridor) move *away* from the faster side. This may make (c) unstable, and nobody's brain can fix an encoding that doesn't work.

**Before any decision, build two no-brain "ideal ships"** (like D44's ideal 39° fly), each using our encoding and output rule with a fixed threshold instead of a brain, on the training ship levels only:
1. **Full geometry** (vx and vy terms).
2. **Self-motion only** (vy term only): a pure stabiliser, brief option (a).

**Fixed before they run. Agreed (2026-11-10):**
- **Threshold: sign only.** Release on the next tick whenever the pooled motion is downward (any amount); hold otherwise. No new number, and the same direction as the brain's output rule. It's on/off, while the brain's firing rate gives graded control.
- **The bar for "flies the easy levels":** completes **≥ 50% of the easy ship training levels.**
- **Reported:** both ships next to never hold and always hold, with completion and mean progress per difficulty (easy, medium, hard).
- **Directions:** 37, every 5° from −90° (straight down) to +90° (straight up), both ends included. Each sees the nearest surface along its line of sight and counts if that surface is within 600 units ahead horizontally, so straight down and up always see the floor and ceiling.
- **Prediction, recorded before they run (Jacob, agreed by Shannyn 2026-11-10):** near ±90° the floor and ceiling are very close, so the forward-flight term there is huge: looking straight down from 30 units above the floor, dφ/dt = −vx / 30 ≈ −10.4 rad/s ≈ −600°/s. **We expect it to dominate the full-geometry mean**, pulling the ship toward whichever of floor or ceiling is nearer (the worry above). The self-motion-only ship has no forward-flight term, so it won't have this.
- Jacob builds and runs them (~2–3 h to build, minutes to run). The result comes back to both of us for the Q1 decision.

| Ideal-ship result | Then |
|---|---|
| Full geometry flies the easy levels | Adopt (c) as above |
| Only self-motion flies them | The forward-flight term is the problem; rethink before choosing (e.g. option a, or a stated change to the pooling) |
| Neither flies them | The motion encoding can't fly these levels; we discuss before any brain runs |

Whatever is chosen, **the self-motion-only ship stays as a control:** the difference between the two measures what edges ahead add.

## 2. Q2: output rule

**Agreed (2026-11-10):** if **either DNp22 spikes** in brain frame *i*, the button is **released** on tick *i* + 1; otherwise it is **held**. Jacob: the output rule returns hold/release directly; logs and the viewer say "hold", not "press", in ship mode. DNp20 stays recorded and shown.

- **Why DNp22, not DNp20** (`ship_reading.md`):
  - DNp22's numbered VS inputs are VS2 and VS3 only, exactly DNOVS2's dye-coupled partners (Suver et al. 2016).
  - DNOVS2 spikes and reaches the wing motor region. DNOVS1 (≈ DNp20) doesn't spike, and targets neck motor neurons.
  - Front-to-back motion barely reaches DNp22's inputs (T4a/T5a → VS2: 0 synapses), so forward flight's front-to-back flow, if ever encoded, wouldn't drive it.
- **This departs from D31, which uses DNp20 for the steering go/no-go rules.** D31 judged whether the pathway carries a signal, not the ship's output rule, so it stays as it is; the change is logged with the ship design. DNp20 is still recorded and shown in the brain panel.
- **Why release on a spike:** the model's VS pathway only produces output for **downward** motion ("up" gives 0 in VS and DNp20, via inhibitory LPi neurons). Following the scene's motion, as flies do, means downward motion → descend → release.
- **Why one tick per spike, no window:**
  - The same as the cube's D42, with no new dial.
  - A driven DNp22 fires at ~100–150 Hz in the model (one spike every ~2 ticks), so the share of released ticks tracks its firing rate. That gives graded control from a rate signal, which is how DNOVS2 signals (its rate rises roughly linearly with its voltage).
- **Silence means hold,** so a silent network climbs to the ceiling and slides along it (the ceiling doesn't kill). The "always hold" reference is what a silent control looks like.

## 3. Q3: input neurons

- **Downward image motion** drives T4d and T5d; **upward** drives T4c and T5c.
- **Both eyes, equally. Agreed (2026-11-10):** in the 2D game the scene is the same on both sides, so driving one eye would be an arbitrary choice. The pathway tests drove the right eye only, so the left eye is new.
  - **Every ship input ID is in v783 and the model,** both eyes (Jacob, `docs/notes/ship_neuron_check.md`).
  - **Left–right asymmetry, to state:** in v783 the left VS cells get much less "down" input than the right: 59% (Jacob's count) or 65% for VS1–VS8 (T4d + T5d: 14,886 vs. 22,889 synapses; Shannyn's count), while the two eyes have nearly the same number of T4d/T5d neurons (796/740 left, 777/727 right). VS → DNp22 is equal on both sides (240/242). Most likely a reconstruction difference, not biology. With both eyes driven equally, the right side will probably set most releases.
  - **Before the baseline:** a short open-loop left-eye-only test, to show whether the left side reaches DNp22.
- **All neurons of a type are driven together** (no growing patch): VS cells integrate wide-field motion, and we pool over the whole view (§1b).
- **Upward motion is still shown.** It drives nothing at the output directly, but it inhibits the "down" pathway through LPi neurons (S2: DNp20 104 → 18 Hz), so the fly's own circuit decides what up-and-down mixtures do.

## 4. Q4: anchor and dials

- **Rate:** each driven neuron fires at R_ship × f, with f = min(1, |ω| / ω_full) and ω the pooled image motion in °/s (as R × f for the cube, D45).
- **ω_full = 30°/s, fixed:** the speed at which T4 responds most (1 Hz for a 30° grating; Maisak et al. 2013). It's set from the anchor directly, with no calibration run.
  - Assumption to state: we use the grating's peak speed in °/s for moving edges.
  - The 30°/s comes from resting flies; active states shift tuning toward faster motion (Strother et al. 2018). Proposal: 30°/s of record, with the active-state mismatch stated. Optionally ~3–10× faster as a labelled variant, fixed before any ship run (as D50 did for R).
  - A saturating ramp is our simplification: real T4 tuning falls again above its peak.
- **The one dial: R_ship**, within 25–200 Hz as for the cube. Baseline **150 Hz**, the cube's value of record. Total dials: R (cube) + R_ship = 2 of the 3 allowed (D5).
- **Whether to tune R_ship** is decided after the baseline, as agreed.
- **No output-side anchor yet.** Suver et al. 2016 report DNOVS2 rates at 22.5°/s rotation, but only in a figure. A possible later check, not a calibration.

## 5. Q5: whole brain or subcircuit

**Agreed (2026-11-10): run the ship on the whole brain.** Jacob: ~3–6 h per held-out batch, so overnight.
- The subcircuit was built and checked on cube inputs only. The ship adds new inputs (left-eye T4/T5, T4c/T5c), so it would need new pathway tests, recruitment and a rule-5 check (~1 day plus runs).
- The whole brain needs none of that, at ~3× the run time (~3–6 h per held-out batch, `ship_brief.md` §5). Jacob's call on whether that fits.

## 6. References for the ship (with no brain)

- **Never hold** and **always hold** (built).
- **Random holds** at the fly's own hold rate (D48 style).
- **The two ideal ships** (§1d): full geometry and self-motion only.

## 7. Model limits to state

- **No gap junctions:** VS–DNOVS coupling and DNOVS1–neck motor coupling are electrical in the fly.
- **No ocellar input:** ocellar neurons are the largest input to both DNp20 and DNp22, and are never driven.
- **The model's VS cells spike;** real VS cells mostly signal with graded voltage.
- **DNOVS neurons encode body rotation;** the ship climbs and falls (translation). Using their pathway for altitude is our mapping.
- **The model has no behavioural state** (no octopamine), so it is neither "resting" nor "flying".

## Jacob's answers (2026-11-10)

1. **Cost:** encoder ~0.5–1 day; the two ideal ships ~2–3 h to build and minutes to run; ~30 min to check the left-eye and T4c/T5c IDs against v783 (done: all correct).
2. **Whole brain:** fits, overnight per held-out batch.
3. **Hold unless released:** one line in the output rule.
4. **DNp22:** no objection; DNp20 stays recorded and shown.

## Next

1. Jacob builds the encoder and both ideal ships, and runs them on the training ship levels (§1d).
2. Together: choose Q1 from the ideal-ship table.
3. The left-eye-only test (§3).
4. Log the whole ship design as one D entry, noting it departs from D31's use of DNp20.
5. Ship baseline on the held-out levels, whole brain, R_ship = 150 Hz.
