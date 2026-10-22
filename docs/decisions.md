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

## Open

These are to be decided after Step 0:

- Subcircuit rule: which neurons are in (core types plus N hops, with a minimum synapse count).
- Brain time per game step (e.g. ~16.7 ms; GD 2.2 physics may run at 240 Hz).
- Input encoding: looming → LC4/LPLC2 stimulation rate, and which neurons receive it.
- Output rule: what Giant Fiber activity counts as a jump.
- The dials and their allowed ranges.
- Closed-loop simulation: Brian2 runtime mode with repeated short runs, or our own reimplementation of the same equations (validated against Brian2).
