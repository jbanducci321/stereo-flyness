# Ship interface (Step 5): neuroscience proposals

*Shannyn, 2026-11-10. Draft for discussion with Jacob. Nothing here is decided until it's logged in `docs/decisions.md`. Answers Q1–Q5 of `docs/notes/ship_brief.md`, using the reading and connectome checks in `docs/notes/ship_reading.md`.*

As for the cube (`docs/notes/t4_proposals.md`), every choice here is **our code, not the fly**. The aim is that each one is either fixed by geometry or biology, or an explicit dial.

## Summary

| Question | Proposal |
|---|---|
| Q1. What the fly sees | **Image motion from geometry:** how fast the edges of the scene move up or down across the eye, computed from the level, as θ is for the cube. Checked first with a no-brain "ideal ship" (§1d) |
| Q2. Output rule | **DNp22** (≈ DNOVS2), both sides. Any spike in a frame means **release** on the next tick; otherwise **hold** |
| Q3. Input neurons | **T4d/T5d** for downward image motion and **T4c/T5c** for upward, both eyes, all neurons of each type driven together |
| Q4. Anchor and dials | Full drive at **30°/s** (T4/T5 peak, Maisak et al. 2013), fixed. One dial, **R_ship**, the peak rate; untuned baseline 150 Hz |
| Q5. Network | **Whole brain** for the ship, so no new subcircuit checks |

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
- **Pooling:** VS cells integrate motion over large parts of the visual field. Proposal: the signed mean of dφ/dt over the edges in view. Downward means drive the "down" input and upward means drive the "up" input (§3).
- **Choices of ours, to state and log:** the field of view (how far ahead, how far above and below), and pooling by a plain mean.

### 1c. What this lets us claim, and what it doesn't

- **The stabilising part** (countering the ship's own climb and fall) matches a known fly reflex, wide-field stabilization (Straw et al. 2010), and what VS cells encode.
- **Any steering toward openings is our test, not a known fly behaviour.** In Straw's experiments, flies set their altitude from the *position* of horizontal edges, through a circuit nobody has identified. Here, steering can only come from the motion pathway.

### 1d. A problem to check before fixing this: the forward-flight term

The output rule (§2) makes the ship follow the scene's motion: downward motion → release → descend. That's the stabilising direction for the ship's own movement. But the **vx term** means:
- edges below move down, so the ship is pushed **down**, and more strongly the closer they are;
- edges above move up, so the ship is pushed **up** toward them.

So **the ship may be pulled toward whichever surface is nearest**, the opposite of keeping clear. Insects that balance optic flow (e.g. bees centring in a corridor) move *away* from the faster side. This may make (c) unstable, and nobody's brain can fix an encoding that doesn't work.

**Proposal: before any decision, build two no-brain "ideal ships"** (like D44's ideal 39° fly), each using our encoding and output rule with a fixed threshold instead of a brain, on the training ship levels only:
1. **Full geometry** (vx and vy terms).
2. **Self-motion only** (vy term only): a pure stabiliser, brief option (a).

| Ideal-ship result | Then |
|---|---|
| Full geometry flies the easy levels | Adopt (c) as above |
| Only self-motion flies them | The forward-flight term is the problem; rethink before choosing (e.g. option a, or a stated change to the pooling) |
| Neither flies them | The motion encoding can't fly these levels; we discuss before any brain runs |

Whatever is chosen, **the self-motion-only ship stays as a control:** the difference between the two measures what edges ahead add.

## 2. Q2: output rule

**Proposal:** if **either DNp22 spikes** in brain frame *i*, the button is **released** on tick *i* + 1; otherwise it is **held**.

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
- **Both eyes, equally:** in the 2D game the scene is the same on both sides. The pathway tests drove the right eye only, so the left eye is new (§5).
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

**Proposal: run the ship on the whole brain.**
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

## Open questions for Jacob

1. Engineering cost of §1b's encoder and the two ideal ships.
2. Whole brain for the ship (§5): does the run time fit?
3. Does the closed loop already allow "hold unless released" as the default (§2)?
4. Any objection to moving the steering readout from DNp20 to DNp22?
