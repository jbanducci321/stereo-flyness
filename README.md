# stereo-flyness

A simulated fruit fly brain, built from the real wiring diagram of the *Drosophila* brain (the FlyWire connectome), playing a minimal Geometry Dash-style game. The final test is a recreation of the first level, Stereo Madness.

**Status:** Step 0, setup and feasibility. Nothing plays yet.

## What this is (and isn't)

This is a **wiring-diagram simulation**, not an uploaded fly. Each neuron is a simple leaky integrate-and-fire unit (the Shiu et al. 2024 model). Connection strengths come from real synapse counts, and excitatory/inhibitory signs come from predicted neurotransmitter types. Those weights stay **frozen**: we never train them.

### The fly vs our code

| Comes from the connectome | Comes from our code |
|---|---|
| Which neurons connect, how strongly, and with what sign | **What the fly sees:** the angular size of the nearest obstacle on a collision course, turned into a growing patch of driven looming-detector neurons (LC4, LPLC2). As the patch grows, each driven neuron also fires faster (rate × patch fraction) |
| How activity spreads from those neurons through the brain | **What counts as a jump:** any spike from either Giant Fiber (DNp01) becomes a one-tick button press |
| Whether, and when, the Giant Fiber fires in response | **How much input:** one tuned dial for the cube, the peak input rate. The patch size is calibrated once, on the whole brain, so the Giant Fiber first fires at the real fly's escape threshold (~39°, von Reyn et al. 2014); it is never tuned on the game |
| | **Timing and modes:** the brain runs at real game time, one frame per 240 Hz physics tick; which readout is used in cube vs ship mode |

All of our design choices live in `src/stereo_flyness/interface/` and are logged, with their reasons, in [docs/decisions.md](docs/decisions.md) (cube interface: D40–D45).

### Choices we made that happen to help the fly

These are ours, not the fly's, and every result should be read with them in mind:

- **Only objects on a collision course loom.** Ceilings overhead don't, so the cube isn't pushed to jump into them.
- **"Collision course" uses the cube's current height,** so an obstacle stops looming once the cube is above it.
  The same rule works against the cube for a raised platform it has to jump onto: from the ground the platform doesn't loom, so only what's under it can cue the jump (D47).
- **Objects the cube lands onto are invisible to the encoding.** The Giant Fiber escape is a takeoff response to things approaching head-on or from the side; landing on something is a different behaviour. So a spike right after an obstacle can't be anticipated. This causes about a third of the deaths of a fly that jumps exactly at the real threshold (D44, D47).
- **The fly can't tell hazards from blocks:** both loom the same way. Obstacles are seen as their full 30 × 30 grid cells, not their smaller hitboxes, clipped at the floor: the eye can't see underground (D47).
- **Which neurons an obstacle drives is approximated.** We don't have visual-field positions for LC4/LPLC2, so the growing patch is built from neurons that share inputs.
- **Our code, not the fly, decides when the game switches between cube and ship.**

### Limits of the model

- **Brain only.** The data has no ventral nerve cord, so the step from Giant Fiber to jump muscle (via the TTM motor neuron) is outside it. "The Giant Fiber spiked" stands in for "the fly jumped".
- **Only the fast escape is modelled.** Real flies also escape through slower pathways that don't need the Giant Fiber.
- **No electrical synapses (gap junctions),** which the real escape and steering circuits use.
- **Excitatory/inhibitory signs are machine-learning predictions** (Eckstein et al. 2024), so some are wrong. We found one clear case (motion-detector neurons T4/T5) and test the steering pathway with and without correcting it; the uncorrected connectome is the main result.
- **Our input builds in what the eye computes.** We stimulate looming and motion detectors directly, so looming detection and direction selectivity come from our code, not from the fly's visual system.
- **Firing rates are unrealistic.** The model's Giant Fiber fires at 100–200 Hz while driven; a real one fires once or twice per approaching object. The jump rule only uses the first spike.
- **The model sometimes gets stuck.** About 0.2% of the time per simulated second, activity locks into a self-sustaining state centred on the mushroom body and never stops. We treat this as a property of the model, not of the fly; our untested guess is that it comes from the model having no adaptation and no noise. Stuck runs are flagged and counted as they happen, not re-run.
- **Tuning uses a subcircuit,** about a quarter of the brain (~33k neurons), checked against the whole brain on held-out tests. The whole brain is compared at the end.
- **The ship pathway is the weaker claim.** The steering neurons we read out (DNp20) mainly move the head in the real fly.

### How we keep it honest

- Weights are never changed. At most 2–3 interface dials are tuned; the cube uses one.
- The rules for judging each experiment are written down **before** its results are seen ([docs/decisions.md](docs/decisions.md)).
- Stereo Madness is held out: nothing is tuned on it, and it's played once at the end.
- Replays show the recorded activity unaltered, say they are replays of a simulation, and show our input separately from the fly's own spikes.

## Plan

0. Setup: environment, data, reproduce a Shiu et al. result, find the target neurons, benchmark.
1. Game: cube (blocks, spikes) and ship physics, plus generated training levels.
2. Cube baseline: the escape pathway (LC4/LPLC2 → Giant Fiber) with default, untuned values.
3. Tune at most 2–3 dials on generated levels, then evaluate on held-out levels.
4. Controls and lesions: shuffled connectome, random network, silenced neurons.
5. Ship pathway: motion-sensing → steering neurons.
6. Mixed levels, then Stereo Madness as the held-out final test. We never tune on it.
7. The whole brain on a GPU, compared to the subcircuit.

**End goal:** watch the fly play Stereo Madness, with its brain activity shown alongside the game. Looming neurons light up as obstacles approach, and the Giant Fiber fires as the cube jumps. Runs are recorded frame by frame and replayed at real speed, since the simulation itself runs slower than real time.

## Setup (Windows)

You need:

- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs Python 3.12 for this project automatically
- [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/): in the installer, check **Desktop development with C++** (MSVC and the Windows SDK). Brian2 needs this to run in its fast compiled mode.

Then:

```bash
git clone https://github.com/jbanducci321/stereo-flyness.git
cd stereo-flyness
uv sync
uv run pytest
uv run python scripts/download_data.py
```

`uv sync` creates `.venv/` with the exact package versions in `uv.lock`. The last command downloads the connectome (about 104 MB) into `data/`. See [data/README.md](data/README.md).

If Brian2 reports "Microsoft Visual C++ 14.0 or greater is required" even though Build Tools is installed, open the **Visual Studio Installer** and choose **Repair** on Build Tools. An incomplete install hides the compiler from Python.

To check that the model works, reproduce the Shiu et al. sugar → MN9 result (takes several minutes):

```bash
uv run python scripts/reproduce_sugar.py --n-run 5 --n-proc 4
```

## Layout

```
src/stereo_flyness/
  brain/       connectome loading + simulation (frozen weights)
  game/        game physics and levels (no knowledge of the brain)
  interface/   everything that connects them: our choices, not the fly's
configs/       experiment settings
scripts/       runnable entry points
tests/         tests
docs/          decisions log, feasibility report
data/          downloaded data (not committed)
results/       experiment outputs (not committed)
```

## Credits

- Model: Shiu, P. K. et al. (2024). A *Drosophila* computational brain model reveals sensorimotor processing. *Nature* 634, 210–219. [Code (MIT)](https://github.com/philshiu/Drosophila_brain_model)
- Connectome: FlyWire Consortium, Dorkenwald, S. et al. (2024). Neuronal wiring diagram of an adult brain. *Nature* 634, 124–138.
- Cell types: Schlegel, P. et al. (2024). Whole-brain annotation and multi-connectome cell typing of *Drosophila*. *Nature* 634, 139–152.
- Neurotransmitter predictions: Eckstein, N. et al. (2024). Neurotransmitter classification from electron microscopy images at synaptic sites in *Drosophila melanogaster*. *Cell* 187, 2574–2594.
- Giant Fiber escape threshold: von Reyn, C. R. et al. (2014). A spike-timing mechanism for action selection. *Nature Neuroscience* 17, 962–970.

Geometry Dash and Stereo Madness belong to RobTop Games. This project uses no original game assets and is not affiliated with RobTop.
