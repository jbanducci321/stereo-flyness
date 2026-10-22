# stereo-flyness

A simulated fruit fly brain, built from the real wiring diagram of the *Drosophila* brain (the FlyWire connectome), playing a minimal Geometry Dash-style game. The final test is a recreation of the first level, Stereo Madness.

**Status:** Step 0, setup and feasibility. Nothing plays yet.

## What this is (and isn't)

This is a **wiring-diagram simulation**, not an uploaded fly. Each neuron is a simple leaky integrate-and-fire unit (the Shiu et al. 2024 model). Connection strengths come from real synapse counts, and excitatory/inhibitory signs come from predicted neurotransmitter types. Those weights stay **frozen**: we never train them.

To keep credit honest, the code separates what the fly's circuitry does from what our code does:

| Comes from the connectome | Comes from our code |
|---|---|
| Which neurons connect, how strongly, and with what sign | How game state becomes stimulation (e.g. obstacle looming → LC4/LPLC2 input) |
| How activity spreads from sensory neurons to output neurons | How output spikes become actions (e.g. Giant Fiber spikes → jump) |
| | Which readout is used in each mode (cube vs. ship) |
| | The 2–3 tuned "dials" (e.g. input strength, firing threshold) |

All of our design choices live in `src/stereo_flyness/interface/` and are logged in [docs/decisions.md](docs/decisions.md).

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

Geometry Dash and Stereo Madness belong to RobTop Games. This project uses no original game assets and is not affiliated with RobTop.
