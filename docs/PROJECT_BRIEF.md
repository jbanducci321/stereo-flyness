# stereo-flyness: Project Brief for Claude Code Sessions

**Purpose of this document:** bring any Claude Code session (especially Shannyn's) fully up to speed on what this project is, what has been decided, what has been built, and how to work in this repo without contradicting earlier decisions.

**Last updated:** 2026-10-22. Written by Jacob's Claude Code session, which did the planning and setup with Jacob.

**Status at time of writing:** Step 0 (feasibility) is underway. Setup is done; the frame-stepping brain runner is built and is being validated on branch `jb-frame-stepping`.

> **To the Claude session reading this:** treat everything under "Decisions" and "Hard rules" as settled. Don't re-litigate, override or "improve" them without the human explicitly asking. If a task seems to need a change to a decision, stop and ask your human first. Shannyn and Jacob decide together, and every change gets logged in `docs/decisions.md`.

---

## 1. The project in one paragraph

**stereo-flyness** drives a minimal Geometry Dash–style game with a simulated fruit fly brain built from the real *Drosophila* connectome. The connectome is the FlyWire wiring diagram of every neuron and synapse in the adult fly brain. The simulation is the leaky integrate-and-fire whole-brain model from **Shiu et al. 2024 (*Nature*)**.

The fly brain's connection weights stay **frozen**: they come from real synapse counts, and their signs from predicted neurotransmitters. We only tune 2–3 interface "dials". The final test is a faithful recreation of the first Geometry Dash level, **Stereo Madness**, which is held out and never tuned on.

**End goal (D19):** a **replay viewer** where you watch the fly play Stereo Madness at real speed, with its brain activity beside the game. Looming neurons light up as obstacles approach, the Giant Fiber flashes, and the cube jumps. Runs are recorded frame by frame and played back, because the simulation runs slower than real time.

It's a two-person portfolio and research project. **Jacob Banducci** (GitHub `jbanducci321`, final-semester CS/data science, psychology background) leads engineering. **Shannyn** (GitHub `shancabi`, heading toward biomedical/neuroscience) leads the neuroscience side.

## 2. The core scientific principle (never violate)

- **Connectome weights stay frozen.** They come from FlyWire v783 synapse counts, with excitatory/inhibitory signs from predicted neurotransmitters. Nothing ever trains or edits them.
- **The only exception is lesion experiments,** where silencing neurons is an experiment, not tuning.
- **We tune at most 2–3 interface dials,** such as input stimulation strength, a firing threshold for "jump", and possibly timing. Fewer dials means more credit goes to the fly's own wiring.
- **Every design choice must make clear what the fly's circuitry does versus what our code does.** All of "our code's" choices live in `src/stereo_flyness/interface/` and get logged in `docs/decisions.md`.
- **This is a wiring-diagram simulation, not an uploaded fly.** The README and every claim must stay honest about that.

| Comes from the connectome | Comes from our code |
|---|---|
| Which neurons connect, how strongly, with what sign | How game state becomes stimulation (e.g. looming → LC4/LPLC2 input) |
| How activity spreads from sensory neurons to output neurons | How output spikes become actions (e.g. Giant Fiber spikes → jump) |
| | Which readout is used in each mode (cube vs. ship) |
| | The 2–3 tuned dials |

## 3. The biology we're targeting

### 3.1 Cube sections → looming-escape pathway (primary, most promising)
- **The pathway:** an approaching obstacle produces a looming (expanding) image. Looming-detector neurons **LC4** and **LPLC2** respond to it, and both synapse onto the **Giant Fiber (DNp01)**, a descending neuron that triggers the fly's fast escape takeoff. **A Giant Fiber spike means "jump".**
- **Caveat 1, the pathway is short.** LC4 and LPLC2 synapse directly onto the Giant Fiber, so the "fly's contribution" in cube mode is close to a one-hop relay plus a threshold. That's why the controls and lesions (Step 4) are essential to the scientific claim.
- **Caveat 2, the real jump happens outside our data.** The Giant Fiber drives the jump through the TTM motor neuron in the ventral nerve cord, partly via electrical synapses (gap junctions). FAFB/FlyWire is brain-only, and the Shiu model has no gap junctions. So "Giant Fiber spikes" stands in for a jump, and the README must say so.
- **Caveat 3:** many real escapes are slower "long-mode" takeoffs that don't depend on the Giant Fiber.
- **Caveat 4:** a pure looming reflex can't handle "don't jump" situations (low ceilings, timing jumps onto blocks). We expect deaths to cluster by obstacle type. That's a valid result, not a bug.

### 3.2 Ship sections → visual motion / flight steering (speculative)
- **Candidate pathway:** scene motion activates the **T4/T5** motion detectors (vertical-motion subtypes, likely T4c/d and T5c/d), which feed the **lobula plate VS cells**, then candidate steering descending neurons (e.g. **DNOVS1/2**). The readout is hold or release.
- **Caveat:** VS cells mainly encode rotational optic flow from the fly's own movement (pitch/roll), not "there's an obstacle above or below me". DNOVS neurons mostly control the neck. A better biological framing may be **optic-flow balancing** (flies stay centered in tunnels by balancing the motion they see on each side).
- Whether this pathway works at all is **part of the experiment.** A clear failure is a valid, reportable result.

### 3.3 Other modeling caveats to keep in mind
- Neurotransmitter signs are **ML predictions** (Eckstein et al. 2024), not measurements, so some are wrong.
- Cutting out a subcircuit removes inputs at its boundary, which changes its dynamics. The rule for cutting it (which neurons are "in") is effectively a hidden dial and must be decided explicitly and logged.
- How much brain time passes per game frame is also a hidden dial. Fix it from biology up front, or count it as one of the 2–3 dials.
- **FlyWire neuron IDs change between releases** when neurons are re-proofread. Any ID from a paper, notebook or older dataset (e.g. v630) **must be checked against v783** before use. We already hit this once (see D15).

## 4. Decisions made so far (settled)

The canonical, up-to-date log is **`docs/decisions.md`**. Read it first. Summary:

| ID | Decision |
|---|---|
| D1 | Project name **stereo-flyness**. The old working name "fly-dash" is retired. |
| D2 | Connectome: **FlyWire FAFB v783** for the whole project. MaleCNS (with the ventral nerve cord) is possibly later, not v1. |
| D3 | Simulation base: **Shiu et al. 2024 Brian2 model** (MIT). eonsystemspbc/fly-brain is GPL-2.0+ (copying its code would make our repo GPL) and is Linux/WSL-focused, so it's a **reference only** (e.g. for the GPU phase). |
| D4 | **Python 3.12 + uv**, with a committed lockfile (`uv.lock`). Brian2 requires Python ≥ 3.12. |
| D5 | **Connectome weights frozen**, at most 2–3 tuned dials. Lesions are the only exception. |
| D6 | Game scope: **cube (blocks, spikes) and ship only.** Stereo Madness has **no jump pads and no orbs**, so we don't build them. |
| D7 | **Stereo Madness is the held-out final test.** We tune only on procedurally generated levels (cube-only, ship-only, mixed). Generator difficulty comes from the physics (jump reach, reaction room), **not** from Stereo Madness's layout. |
| D8 | Game physics: **our own Python implementation**, using camila314/gdp (2.2 branch, no license) as a **read-only reference. Copy no code.** A search-based bot must be able to beat each level. |
| D9 | **Geometry Dash level data stays local** and is never committed (the design belongs to RobTop Games). Only the fetch-and-convert script is committed. |
| D10 | v1 input comes from **game state, not pixels**: obstacle distance, size and expansion rate. A pixel "compound eye" may come later. |
| D11 | **Mode switching is an interface choice** made by our code (jump neurons in cube mode, steering neurons in ship mode). The fly doesn't decide it. |
| D12 | Workflow: Step 0 setup was done on main. **All work now goes through branches and pull requests.** |
| D13 | **Public repo, no data ever committed.** The FlyWire connectivity release is CC BY 4.0, and Shiu's code is MIT. A code LICENSE (likely MIT) is pending. |
| D14 | Shiu's `model.py`/`utils.py` are **vendored byte-for-byte unchanged** (commit `91bdd1e`) as `brain/shiu_model.py` and `brain/shiu_utils.py`, with only a docstring added. **Never edit them.** Our changes go in separate modules. |
| D15 | Sugar GRN v630 ID `720575940620900446` → v783 ID `720575940639259967`. We verified that 95% of its downstream partners are shared with the other sugar GRNs. Lesson: always check IDs against v783. |
| D16 | Frame-stepping input: Shiu's `PoissonInput` (fixed rate) is replaced by a `PoissonGroup` + one-to-one `Synapses` with changeable rates. Validated as equivalent on the whole brain; see §6.3. |
| D17 | Closed-loop runs use `BrainStepper.run_frames()` (one Brian2 run, callback per frame), not one `step()` per frame. This avoids ~100–250 ms of overhead per call, and the results are identical. |
| D18 (provisional) | Subcircuit size target: up to ~20k neurons / ~3M connections, from benchmarks. The extraction rule itself is still open (S5). |
| D20 | Game physics: GD **2.2** (240 Hz tick), exact gameplay, native units (1 block = 30), 64-bit floats with the game's update order. Facts only from camila314/gdp and OpenGD; every constant is cited in `docs/game_physics.md`. The song and SFX come from the user's local files and are never committed. |
| D21 | Stereo Madness layout: the official main-level data (OpenGD `mainLevels.json`, pinned), identical to server copy 77236587 on all 1,399 gameplay objects. Level 94729537 was rejected (a different level). `scripts/fetch_stereo_madness.py` writes it to git-ignored `data/gd/`. |
| D22 | Level format: one JSON file per level, GD units with the ground at y = 0, gameplay objects as ready-made hitboxes (`kind` + corners), portals with x/y/mode. The engine derives ship bounds with `ship_bounds()`. Spec: `docs/level_format.md`; code: `game/level.py`, `game/objects.py`. |
| D19 | End deliverable: a **record-and-replay viewer**. Closed-loop runs log every frame (game state, inputs, watched spikes) from the `run_frames` callback, and a viewer replays at real 60 fps with a brain-activity panel. It must visibly separate our input encoding from the fly's spikes, say it's a replay of a simulation, and never smooth or alter recorded activity. Live mode is optional, for small subcircuits only. |

### Open decisions (not yet made; don't decide these unilaterally)
- **Subcircuit rule:** which neurons to keep (core cell types + N hops, minimum synapse count). **Shannyn proposes** (task S5).
- **Brain time per game step:** e.g. ~16.7 ms at 60 fps. Geometry Dash 2.2 physics may run at 240 Hz (4.17 ms ticks).
- **Input encoding:** how looming becomes the LC4/LPLC2 stimulation rate, and which neurons receive it. LC4 neurons tile the visual field, so obstacle position could map to specific neurons.
- **Output rule:** what Giant Fiber activity counts as "jump" (one spike? N spikes in a window?).
- **The dials and their allowed ranges.**
- **Closed-loop simulation approach:** resolved for now by D17 (Brian2 with `run_frames`). Our own reimplementation (e.g. PyTorch, validated against Brian2) stays an option for speed or for the GPU phase.
- **Code LICENSE.**

## 5. Repository, environment and workflow

### 5.1 Repo
- **GitHub:** `https://github.com/jbanducci321/stereo-flyness` (public).
- **`main` is protected** by a ruleset named `protect-main`:
  - a pull request with **1 approval** is required;
  - stale approvals are dismissed when new commits are pushed;
  - force pushes and deletion are blocked;
  - the repo admin (Jacob) can bypass the review only when merging a PR, never by pushing directly.
- **Never commit directly to `main`.** Work on a branch and open a PR; the other person reviews.
- **Branch naming:** prefix by area, e.g. `neuro/cell-types`, `brain/...`, `game/...`. Jacob's current branch is `jb-frame-stepping`.
- **Co-author credit:** when work is joint, add a `Co-authored-by:` trailer (GitHub Desktop has a co-author button). Jacob commits through GitHub Desktop himself.

### 5.2 Layout
```
src/stereo_flyness/
  brain/        connectome loading + simulation (frozen weights)
    shiu_model.py, shiu_utils.py, SHIU_LICENSE.txt   # vendored, never edit
    stepper.py                                       # BrainStepper (frame-by-frame runner)
  game/         game physics + levels (must never import brain/ or interface/)
  interface/    everything that connects brain and game (our choices, not the fly's)
configs/        experiment settings
scripts/        runnable entry points (download_data.py, reproduce_sugar.py, validate_stepping.py)
tests/          pytest tests
docs/           decisions.md, FEASIBILITY.md, PROJECT_BRIEF.md (this file)
data/           downloaded data (git-ignored except data/README.md)
results/        experiment outputs (git-ignored)
```

### 5.3 Environment (both team members are on Windows)
**Install:**
- Git
- **uv**, which installs Python 3.12 for the project; system Python versions don't matter.
- **Microsoft C++ Build Tools** with "Desktop development with C++" (MSVC + Windows SDK).

**Locked versions** (from `uv.lock`): Python 3.12.14, brian2 2.10.1, numpy 2.5.4, pandas 3.0.6, pyarrow 26.0.0, joblib 1.6.0, pytest 9.1.1.

**Commands:**
```bash
uv sync                                    # create .venv with exact locked versions
uv run pytest                              # all tests (first run ~5 min while Brian2 compiles; later ~20 s)
uv run python scripts/download_data.py     # ~104 MB connectome into data/, checksum-verified
uv run python scripts/reproduce_sugar.py --n-run 5 --n-proc 4   # optional model sanity check
```

**Gotcha seen on Jacob's machine:** if Brian2 says *"Microsoft Visual C++ 14.0 or greater is required"* even though Build Tools is installed, the install is incomplete. Open **Visual Studio Installer**: if it says "Setup paused", click **Resume**; otherwise use **More → Repair**. Brian2 falls back to a much slower mode without the compiler.

**Resources:** a whole-brain model instance uses several GB of RAM. Use `--n-proc 4` (4 parallel workers) or fewer on a laptop.

### 5.4 Data (FlyWire v783, via Shiu's repo pinned to commit `91bdd1e`)
- **`data/Completeness_783.csv`:** 138,639 neurons, indexed by FlyWire root ID. **The row order defines the model's neuron index.**
- **`data/Connectivity_783.parquet`:** 15,091,983 connected pairs, 54,492,922 synapses. Columns:
  - `Presynaptic_ID`, `Postsynaptic_ID`: FlyWire root IDs;
  - `Presynaptic_Index`, `Postsynaptic_Index`: model indices;
  - `Connectivity`: synapse count;
  - `Excitatory`: +1 or −1;
  - `Excitatory x Connectivity`: the signed weight.
- **Cell-type labels are not downloaded yet.** Sources: Codex (`codex.flywire.ai`, requires each person's own sign-in) or the `flyconnectome/flywire_annotations` GitHub repo (must be confirmed to match v783).
- **Licenses:** FlyWire connectivity is CC BY 4.0 (Zenodo record 10676866); Shiu's code is MIT; the Codex label download has its own citation requirements (task S6). Citations are listed in `data/README.md`.

## 6. What has been built and verified

### 6.1 Shiu model parameters (unchanged, from `shiu_model.default_params`)

| Parameter | Value |
|---|---|
| Resting potential `v_0` | −52 mV |
| Reset potential `v_rst` | −52 mV |
| Spike threshold `v_th` | −45 mV |
| Membrane time constant `t_mbr` | 20 ms |
| Synaptic time constant `tau` | 5 ms |
| Refractory period `t_rfc` | 2.2 ms |
| Synaptic delay `t_dly` | 1.8 ms |
| Weight per synapse `w_syn` | 0.275 mV |
| Poisson input weight factor `f_poi` | 250 |
| Default Poisson input rate `r_poi` | 150 Hz |
| Simulation time step `dt` | 0.1 ms (Brian2 default) |

Each stimulated neuron gets no refractory period, matching Shiu's code.

### 6.2 Sugar → MN9 reproduction (setup check): passed
- **The test:** stimulate the 21 right-hemisphere labellar sugar-sensing GRNs (IDs in `scripts/reproduce_sugar.py`) across the whole brain, then measure MN9, the proboscis motor neuron (ID `720575940660219265`, unchanged in v783).
- **Results, 10 trials of 1 s each:**

| Sugar rate | MN9 rate | Shiu's reference (v630) | Active neurons |
|---|---|---|---|
| 100 Hz | **67.7 ± 5.2 Hz** | 67.0 Hz | 398 |
| 150 Hz | 84.4 ± 5.0 Hz | 93.3 Hz* | 396 |

  \* This reference is ambiguous: Shiu's notebook text says that run used 200 Hz.
- **Speed:** about 2.5 min per 1 s whole-brain trial on one core, mostly spent rebuilding the network each trial.

### 6.3 Frame-stepping brain runner (`src/stereo_flyness/brain/stepper.py`)
**Why it exists:** Shiu's code builds the network, runs once with fixed input, and discards it. The game needs the brain built **once**, advanced a frame at a time, with **input changing between frames** and spikes read back after each frame.

**API:**
```python
from brian2 import Hz, ms
from stereo_flyness.brain.stepper import BrainStepper

stepper = BrainStepper(path_comp, path_con,
                       inputs={"sugar": [...flywire ids...]},   # groups we can stimulate
                       watch={"mn9": [...flywire ids...]},      # groups whose spikes we read
                       seed=1)
stepper.set_rate("sugar", 100 * Hz)        # one rate for the group, or an array (one per neuron)
counts = stepper.step(1000 / 60 * ms)      # advance one 60 fps frame; returns {"mn9": array_of_counts}
stepper.t                                  # total simulated time

# Fast closed-loop path (use this for the game; D17): one Brian2 run, callback per frame
def on_frame(i, counts):                   # counts = this frame's watched spikes
    stepper.set_rate("sugar", 0 * Hz if i > 30 else 100 * Hz)   # change input for the next frame
stepper.run_frames(60, 1000 / 60 * ms, on_frame)
```
Each `step()` call costs ~100–250 ms of Brian2 overhead regardless of network size. `run_frames()` pays it once and is tested to give identical results.

**Implementation:**
- The network comes from Shiu's `create_model`, unchanged.
- **Input** is a `PoissonGroup` (one source per stimulated neuron) connected one-to-one with `v += w_syn * f_poi`. That's the same event probability per step (`rate * dt`), weight, target variable and time slot as Shiu's `PoissonInput(N=1)`, but with changeable rates.
- **Spike counts** come from a `SpikeMonitor(record=False)`, so memory stays constant.
- Neuron IDs are validated before the slow build.

**Tests (`tests/test_stepper.py`, tiny 4-neuron connectome), all passing:**
- 10 short steps give exactly the same spikes as one long run;
- rate changes take effect;
- state carries over between steps;
- the input matches Shiu's own `PoissonInput` side by side;
- unknown IDs raise an error.

**Validated on the whole brain (`scripts/validate_stepping.py`):**
- **Stepped sugar test:** 60 × 16.7 ms frames give MN9 = 67.8 ± 3.9 Hz, against 67.7 ± 5.2 Hz unstepped (Welch t = 0.03).
- **On/off switching:** MN9 is 61 Hz on, 7.5 Hz off (residual spikes only in the first frame), and 66 Hz on again. It starts ~2 frames after input turns on.
**Benchmark (`scripts/benchmark_stepping.py`, one worker, using `run_frames`):**

| Network | Speed vs real time | One 90 s level |
|---|---|---|
| 1k neurons | ~real time | ~0.3–3 min |
| 5k–20k neurons | ~1–5× slower | ~2–8 min |
| 50k neurons | ~5–9× slower | ~8–13 min |
| Whole brain (138,639) | ~16–26× slower | ~25–40 min |

- **240 Hz is affordable:** the cost tracks simulated time, not how often the game talks to the brain.
- **Provisional subcircuit size target (D18): up to ~20k neurons / ~3M connections.** That puts a tuning grid at an overnight run on the laptop.

## 7. The game (Step 1, not started)
- **Minimal headless Python clone:** plain shapes only, no RobTop art/music/assets, deterministic with seeds, plus a viewer. The viewer should render from **recorded run logs** (not only live play), so it can grow into the replay viewer (D19).
- **Mechanics:**
  - cube: blocks, spikes, floor;
  - ship: hold to rise, release to fall, avoid spikes, floor and ceiling.
- **Physics spec: `docs/game_physics.md`** is the source of truth for the engine: units, tick, cube and ship constants, hitboxes, collision and death rules, and open questions.
- **Physics reference:** `github.com/camila314/gdp`, branch 2.2. These are decompilations of PlayerObject, GJBaseGameLayer, PlayLayer and GameObject.
  - The repo has **no license**: read it for constants and logic only, and write our own code.
  - Flag 2.1 vs 2.2 differences. 2.2 likely uses a fixed **240 Hz** physics tick.
  - `camila314/pathfinder` (full support only up to GD 1.7, not licensed for redistribution) is a weak, optional cross-check.
- **Stereo Madness layout:**
  - **Done (D21):** `uv run python scripts/fetch_stereo_madness.py [--cross-check]` downloads the official main-level data and decodes it with the standard library. No gd.py or gdparse is needed.
  - It writes `data/gd/stereo_madness_objects.csv`: 2,291 objects, 1,399 of them gameplay; no pads or orbs.
  - The format, coordinates (world y = level y + 90), ID categories and portal timings are in `docs/game_physics.md` §10.
  - **Converted (D22):** `uv run python scripts/convert_stereo_madness.py` writes `data/gd/stereo_madness.json` in our level format (`docs/level_format.md`): 1,396 hitboxes + 4 portals. The ship-bounds rule is validated on all 3 ship sections (`docs/game_physics.md` §10).
- **Validation:** a search-based bot must be able to beat every level, including converted Stereo Madness. If it can't, our physics or conversion is wrong.
- **Ownership of the held-out test:** Shannyn runs the converter, checks total length and the cube/ship section boundaries against a playthrough video, and keeps it sealed. Jacob, who tunes, never tunes on it.

## 8. Full plan and task list

### Steps
| Step | What |
|---|---|
| 0 | Feasibility (current) |
| 1 | Build the game, including a viewer that can replay a recorded run log |
| 2 | Cube baseline with **default, untuned** values. Record this before any tuning; it's a key result. Closed-loop runs log every frame from here on (R1), and the first brain panel appears in the viewer (R2). |
| 3 | Tune at most 2–3 dials on generated levels, evaluate on held-out generated levels |
| 4 | Controls and lesions: degree-preserving shuffled connectome; random network of the same size; LC4/LPLC2 silenced; Giant Fiber silenced. Does performance depend on the real wiring? |
| 5 | Ship pathway: repeat Steps 2–4 |
| 6 | Mixed levels, then Stereo Madness **once**, with everything frozen. That run is recorded and becomes the showcase replay. |
| 7 | Whole brain on a free GPU (Kaggle or Lightning AI), compared with the subcircuit |
| 8 | Write-up: honest README, figures, reproducibility, and the replay viewer showcase (Stereo Madness replay plus an exported video) |

**Stretch:** evolutionary search over the dials, or mushroom-body dopamine-gated learning (only KC→MBON synapses plastic).

**Metrics:** % of level completed, deaths by obstacle type, training vs held-out performance. Results are logged to CSV with config, seed and git commit.

### Step 0 tasks

**Shannyn (neuroscience track):**
- **S1, setup** (no blockers): install, `uv sync`, `uv run pytest` passes, data download.
- **S2, find our neurons in FlyWire v783** (no blockers; **highest priority, it unblocks the most work**):
  - Escape: LC4, LPLC2, Giant Fiber (DNp01).
  - Steering: vertical T4/T5 (T4c/d, T5c/d), VS cells, DNOVS1/2 candidates.
  - For each: count, side, FlyWire IDs, and connectivity (e.g. LC4→GF synapse counts).
  - **Make sure Codex is set to v783.**
  - Output: fill the "Target cell types" table in `docs/FEASIBILITY.md`, and put the IDs in `configs/target_neurons_783.csv` with columns `cell_type, side, flywire_id, source, notes`. This is a proposed convention; confirm with Jacob.
- **S3, background reading** (no blockers): Shiu et al. methods; Giant Fiber escape; what LC4/LPLC2 and VS cells encode; optic-flow centering. Short notes go in `docs/notes/`.
- **S4, design the pathway tests** (needs S2): what to stimulate, at what rates, and what counts as "it works" for escape and for steering.
- **S5, propose the subcircuit rule** (needs S2), with the biological reasoning, in `docs/decisions.md` under "Open".
- **S6, license/citation check for the cell-type labels** (no blockers); update `data/README.md`.

**Jacob (engineering track):**
- **J2, frame-by-frame runner + benchmark** (in progress on `jb-frame-stepping`).
- **J3, game physics research** (no blockers).
- **J4, run the pathway tests** (needs S2 + S4), including silencing LC4/LPLC2 to check the Giant Fiber goes quiet.
- **J5, extract and benchmark the subcircuit** (needs S5 + J2).

**Together:**
- **T1:** review each other's PRs.
- **T2:** interpret the pathway results.
- **T3:** go/no-go in `docs/FEASIBILITY.md`, which closes Step 0.
- **T4:** interface decisions: brain time per frame, input encoding, output rule, dials and ranges, level seeds.

**Dependencies:** S2 → S4, S5 · S4 → J4 · S5 + J2 → J5 · J4 + J5 → T3 → T4 → Step 2 · J3 → Step 1.

### Replay viewer tasks (D19), built alongside Steps 1–8

| Task | Owner | When | What |
|---|---|---|---|
| **R1. Run recorder** | Jacob | Step 2 (with the closed loop) | Every closed-loop run writes a per-frame log from the `run_frames` callback: frame index, game state (player position, mode, alive/dead, obstacles in view), input rates per group, and watched spike counts per neuron. Saved alongside the run's config, seed and git commit. It feeds both the metrics and the viewer. |
| **R2. Replay viewer engine** | Jacob | Steps 1–2 | Plays a recorded log at real 60 fps, with pause, scrub and slow motion: the game panel plus a brain panel. Exports to video. The library (likely pygame) is chosen when built, with approval. |
| **R3. Brain panel design** | **Shannyn** | Steps 2–5 | Which neuron groups to show and how: LC4/LPLC2 laid out by visual-field position, the Giant Fiber, VS cells, the steering neurons. Plus biologically accurate labels and colours, and short explanations. It must visibly separate our computed input (the looming signal) from the fly's spikes. |
| **R4. Showcase replay** | Both | Step 6 | Record the single frozen Stereo Madness run and produce the showcase replay and video. |
| R5. Live mode (optional) | Jacob | After Step 3 | Run a small subcircuit (~1k–5k neurons, near real time) live in the viewer. |
| R6. 3D neurons (stretch) | Shannyn + Jacob | After Step 6 | Render real FlyWire neuron positions/morphologies lighting up in the brain panel. Check the mesh licence and citation first. |

### Later steps: who leads
| Step | Shannyn | Jacob |
|---|---|---|
| 1 | Owns the sealed Stereo Madness level; drafts the README "fly vs our code" section | Physics, level format, converter, bot, generators, replay-capable viewer (R2) |
| 2 | Checks encodings; spike-timing analysis; deaths by obstacle type; starts the brain panel design (R3) | Interface code, closed loop, run recorder (R1) |
| 3 | Biological plausibility of the tuned values | Grid search, held-out evaluation |
| 4 | **Leads** lesion design and interpretation | Shuffled and random networks, runs |
| 5 | **Leads** ship design (encoding, readout, hold/release rule) | Pipeline reuse |
| 6 | Run Stereo Madness once, together; showcase replay (R4) | Mode switching, mixed levels |
| 7 | Subcircuit vs whole-brain comparison | GPU runs |
| 8 | Biology, methods, limitations | Engineering, reproducibility |

## 9. Hard rules for any Claude session in this repo
1. **Never modify connectome weights**, and never edit `brain/shiu_model.py`, `brain/shiu_utils.py` or `SHIU_LICENSE.txt`.
2. **Never commit data:** nothing under `data/` (except `data/README.md`) or `results/`, and no Geometry Dash level data.
3. **Never commit to `main`** or push to it. Use a branch and a PR. Don't merge PRs on the human's behalf unless asked.
4. **Check every FlyWire ID against v783** (`data/Completeness_783.csv`) before using it, and record its source.
5. **Don't tune on Stereo Madness,** and don't use its layout to shape the training-level generators.
6. **Our design choices go in `interface/`** and get logged in `docs/decisions.md`: what, alternatives, why, date.
7. **Don't copy code from unlicensed or GPL sources** (camila314/gdp, pathfinder, eonsystemspbc/fly-brain). Read them for facts only.
8. **Ask the human before** big or irreversible choices: new major dependencies, dataset changes, licensing, changing any decision in §4, or anything touching the other person's task area.
9. **Be scientifically honest:** if something is wrong or infeasible, say so directly and propose an alternative. Don't overclaim.
10. **Coordinate on shared files.** `docs/FEASIBILITY.md` and `docs/decisions.md` are edited by both people. Edit only your own sections to keep merge conflicts small (Shannyn: the cell-type table and neuroscience notes; Jacob: the environment and benchmark sections).
11. **Tests must pass** (`uv run pytest`) before opening a PR.
12. Refer to team members by name, and to Shannyn as "she".
13. **Closed-loop runs must log every frame** (R1, D19). Don't add code paths that skip the recorder. Replays must show recorded activity exactly as simulated, and label our input encoding separately from the fly's spikes.

## 10. How Shannyn should start her Claude session
1. Clone the repo (or pull `main`), then run `uv sync`, `uv run pytest` and `uv run python scripts/download_data.py`.
2. Tell Claude: *"Read `docs/PROJECT_BRIEF.md` and `docs/decisions.md` first. I'm Shannyn, the neuroscience lead. Start on task S2."*
3. Create a branch such as `neuro/cell-types` before making changes.
4. When done: run the tests, commit, push the branch, open a PR, and ask Jacob to review.
