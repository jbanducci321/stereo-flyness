# T4: engineering answers to Shannyn's cube draft

**Status:** Jacob (with Claude), 2026-10-30. These answer the four questions in Shannyn's draft (`docs/notes/t4_proposals.md` on `sc-interface-t4`). Nothing is decided: the decisions get logged in `docs/decisions.md` at T4. No code has changed yet.

## 1. Can brain time match game time exactly (42/42/41 steps)?

**Yes, and it's easy.** Recommendation: **do it**, since it costs nothing.

- `BrainStepper.run_frames` currently rounds the frame to a whole number of 0.1 ms steps: 42 steps, so 4.2 ms.
- Brian2 can instead call the frame callback on the exact 1000/240 ms interval. Tested on a small network: the callback then fires after **42, 42, 41, 42, 42, 41, …** steps by itself. Every 3 frames is exactly 12.5 ms, and every tick lines up with game time.
- **The change:** in our own `stepper.py` (not Shiu's files), stop rounding the frame length, and add a test that 240 frames take exactly 1 s.
  - Frames then last 4.2 or 4.1 ms.
  - Per-frame spike counts aren't all the same length, which doesn't matter for "did the Giant Fiber spike?".
  - The pathway tests used 4.2 ms frames and stay as they are.
- **What the 0.8% would have meant:** the brain and game are step-locked (one brain frame per tick), so the drift is not a growing desync. It would only make the fly's clock run 0.8% slow relative to the world: a 10 ms latency becomes ~9.9 ms of game time. That's negligible, but exact costs nothing, so there's nothing to disclose.

## 2. How does the interface find the objects ahead?

**From what the engine already exposes. No engine change is needed**, so `game/` stays independent of the brain (D23, enforced by a test).

- `game.level.boxes` holds every gameplay object, sorted by `x0`. `game.player` gives the cube's hitbox centre `x, y` every tick.
- **Visual cell from hitbox:** every box is built centred on its object (`objects.hitbox()`, used by both the Stereo Madness converter and the generators). So an object's 30 × 30 visual cell, which Shannyn's draft uses for its size, is its hitbox centre ± 15. For example, a 6 × 12 spike gets its full 30-unit cell.
- **Per tick, in the interface:**
  1. find the boxes whose cell starts ahead of the eye (x + 15), with a binary search on a sorted list;
  2. keep the ones whose cell overlaps the cube's 30 units vertically (the collision course);
  3. the gap is the nearest cell's front edge − (x + 15), and θ = 2·atan(15 / gap).

  That's cheap in Python, a tiny fraction of the brain's cost per tick.
- **Note:** "on a collision course" uses the cube's *current* height. While the cube is in the air, an obstacle below it stops looming. That follows from the geometry rule as written. It's worth stating in the README with the other geometric choices.
- **Input groups:** the stepper already accepts one rate per neuron. So the growing patch can be a single input group, "loom", of all LC4 + LPLC2 neurons, with each tick setting driven neurons to R and the rest to 0.
  - This keeps the Poisson input structure fixed for the whole run.
  - It also logs cleanly: θ, f, R and the driven IDs every tick (hard rule 10).

## 3. Two dials (R, θ_full), or calibrate θ_full and keep one in reserve?

**Engineering view: both cost the same to build. Calibrating θ_full is cleaner if the threshold can be read reliably.** It's mostly Shannyn's call (biology).

- **Building:** the encoding takes θ_full as a parameter either way.
- **Calibration** adds one open-loop script: present loom approaches at the game's speed (r/v = 48 ms) for a range of θ_full at the default R. Find the θ_full where the Giant Fiber's first spike lands at the real threshold angle.
  - On the subcircuit, a 1 s approach takes seconds, so a sweep of ~10 values × 10 trials is minutes.
- **Why calibrating appeals:**
  - It's tied to the fly, not tuned to the game.
  - It leaves R as the only cube dial, keeps a spare under D5, and leaves less room for accidental fitting.
- **Two cautions:**
  - The calibration depends on R, so calibrate at the default R (150 Hz). If R is later tuned, θ_full stays fixed.
  - The calibration must happen **before** the Step 2 baseline, because the baseline must be untuned. Calibrating is not tuning, but it has to be fixed before any game run.
- **One thing to settle:** if von Reyn et al.'s threshold is a distribution, which value we use (median?) should be fixed in advance.

## 4. Also record "every object ahead looms" baseline runs?

**Yes: it's cheap, and it shows how much the collision-course choice helps.**

- **Cost:** practice levels are already ~30 s (`configs/level_suites.toml`). On the interim subcircuit, a 30 s level takes ~8.6 min per run with 4 at once.
  - The held-out cube suite is 20 levels, about **45 min**. The variant roughly doubles that, to about 1.5 h.
  - The 50 training cube levels would take ~1.8 h per variant.
- **Building it:** one setting in the encoding, "which objects loom": `collision` (default) or `all`. With `all`, the nearest object ahead looms whatever its height, so ceilings loom too.
- **Labelling:** the variant is a comparison, not a dial. It's reported next to the baseline, never tuned. It needs logging as such so it can't become a hidden fourth option.

## Two small notes on the draft

- **§3, stuck runs:**
  - The draft says a stuck run's Giant Fibers stay silent, so the cube just stops jumping.
  - Follow-up (a) (`docs/cascades.md`, PR #13) found that in a larger stuck state the right Giant Fiber **still fires on a loom, but ~25 ms later and 40% weaker**. The natural stuck state is untested.
  - So stuck runs may jump *late* rather than not at all. Step 2 should compare jump timing in stuck vs normal runs.
  - The stuck-run counting rule is D38, not D37.
- **§2b, patch seed:** "fixed by rule, logged, never tuned" fits the P5 construction (`loom_patches`, seeded per side). Reusing that code keeps probes and the game encoding consistent.
