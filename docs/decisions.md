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

## Open

These are to be decided after Step 0:

- Subcircuit rule: which neurons are in (core types plus N hops, with a minimum synapse count).
- Brain time per game step (e.g. ~16.7 ms; GD 2.2 physics may run at 240 Hz).
- Input encoding: looming → LC4/LPLC2 stimulation rate, and which neurons receive it.
- Output rule: what Giant Fiber activity counts as a jump.
- The dials and their allowed ranges.
- Closed-loop simulation: resolved for now by D17 (Brian2 runtime with `run_frames`). Our own reimplementation of the same equations (e.g. PyTorch, validated against Brian2) stays an option if subcircuit runs are still too slow, or for the GPU phase.
