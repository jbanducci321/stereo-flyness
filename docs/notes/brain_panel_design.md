# Brain panel design (R3): first draft

*Shannyn, 2026-11-01. Draft for discussion with Jacob. The brain panel is the part of the replay viewer (R2, D25) that shows the fly's brain beside the game. This note proposes what it shows and how; Jacob builds it into `src/stereo_flyness/viewer/`.*

## Rules the panel must follow (D19, hard rule 10)

1. **It shows recorded activity, unaltered.** No smoothing, no interpolation, no "nicer" spike trains. Every number and flash on screen comes straight from the run's files (`brain.parquet`, `spikes.npz`).
2. **Our input is visibly separate from the fly's activity:** different panel regions, a different visual style, and its own label.
3. **It says what it is.** "Simulation replay" and who drove the cube (fly or bot) are already drawn on every frame (`render.draw_driver_label`). The panel keeps that.
4. **Known model artefacts are labelled when they happen,** not hidden. That means the stuck state (D38).

### One consequence: frames at 60 fps

The brain runs one frame per 240 Hz tick (D40), but video export draws every 4th tick (60 fps, `viewer/export.py`). A panel that only showed the drawn tick's spikes would silently drop three ticks out of four.

**Proposal:** each displayed frame shows **all spikes since the previous displayed frame**, i.e. the sum over its 4 ticks. That's binning, not smoothing: no spike is lost, moved or invented. The panel states it in small print: "spikes per 1/60 s". The live window (any speed) does the same for the ticks between two drawn frames.

## Layout

A strip **below the game**, the full width of the window, in three columns read left to right, in the order the signal flows: what we show the fly → what its escape circuit does → the rest of the brain.

```
+---------------------------------------------------------------------------+
|                               GAME (unchanged)                            |
|   SIMULATION REPLAY: the cube is controlled by the fly brain model        |
+------------------------+--------------------------+-----------------------+
| WHAT WE SHOW THE FLY   | THE FLY'S ESCAPE NEURONS | THE REST OF THE BRAIN |
| (our input, D41)       | (the model's activity)   | (the model's activity)|
|                        |                          |                       |
|  left eye   right eye  |   GF left    GF right    |  active neurons ~~~~  |
|  LC4   ....  ....      |     (o)        (o)       |  stuck-state  [ 2%]   |
|  LPLC2 .... ....       |  |  | || |    | |||  |   |                       |
|  θ 39°  f 20%  29 Hz   |  press ▲  ▲   jump ✓     |                       |
+------------------------+--------------------------+-----------------------+
```

### Column 1: "What we show the fly" (our input)

- **Two eyes, side by side** (left, right). In each, two rows of dots: **LC4** (50 / 54 neurons) and **LPLC2** (102 / 108).
- **A dot is lit when we drive that neuron.** Dots fill in patch order (D41), so the lit region grows as the obstacle looms.
  - Brightness shows the rate we send (R × f, D45).
  - These are **driven/not driven** states from our encoding, *not* the neurons' spikes. A driven neuron spikes because we make it spike, so showing its spikes would present our input as the fly's activity.
- **Readouts under the eyes:** θ (the obstacle's angular size), f (the share of each population driven) and the rate per driven neuron.
  - A small gauge marks **39°**, the calibrated threshold (D43), so viewers can see when the fly "should" react.
- **Honesty line:** "Dots are in our patch order, not the eye's real layout." The patch is built from shared input partners, not visual-field positions (D41).
- **Style:** outlined, neutral colour (white/grey), so it reads as an instrument, not as brain activity.

### Column 2: "The fly's escape neurons" (the model's activity)

- **The two Giant Fibers (DNp01)**, left and right, as large markers that **flash on every spike**. The number of spikes in the frame is shown, not just "on".
- **A scrolling spike raster** for each Giant Fiber over the last ~1 s: one tick mark per spike, at its exact frame. This is the most direct "unaltered" view, because every spike is visible at its real time.
- **Press and jump markers** on the same time axis:
  - ▲ a **press**: a Giant Fiber spiked, so the next tick is a press (D42). It sits one tick after the spike, which shows the brain → game delay.
  - ✓ **jump** if the press happened on the ground; a grey ▲ if it happened in mid-air and did nothing.
- **Style:** filled, warm colour (amber), used **only** for the model's own spikes.

### Column 3: "The rest of the brain" (the model's activity)

- **Active neurons:** a scrolling trace of how many neurons fired per frame, **not counting the neurons we stimulate** (as the backup flag counts them, D38), over the last ~2 s. A normal loom peaks at a few hundred.
- **Stuck-state share:** a small bar showing the share of the stuck-state neurons firing in the last ~100 ms, with the 50% line marked.
- **When the stuck flag is on** (D38), a banner across the panel: "Model artefact: self-sustaining activity (not fly behaviour, see README)". It stays from the frame the flag starts.
- **Backup flag:** it's computed after the run (it needs the run's median), so it's shown as a marker on the progress bar, not live.

### Version 2 (later, optional)

- **The Giant Fiber's main input partners:** excitatory (e.g. DNp70, PVLP151) and inhibitory (e.g. CB3707, PVLP010), each as a small labelled dot that flashes on spikes. This would show the feed-forward inhibition and the cross-midline route from `docs/pathway_results.md` happening during play. All the data is already in `spikes.npz`.
- **Real neuron shapes in 3D** is a separate stretch task (R6), after Step 6.

## Colours and labels

| What | Style | Why |
|---|---|---|
| Our input (driven LC4/LPLC2, θ, rate) | white/grey, outlined | Reads as an instrument, not activity |
| The model's spikes (Giant Fibers, other neurons) | amber, filled | One colour means "the model fired" everywhere |
| Presses and jumps | white ▲, ✓ | Game events, not neurons |
| Model artefacts (stuck state) | striped banner with text | Can't be mistaken for normal activity |

- **Colour-blind safe:** amber vs white/grey, and fill vs outline, so the meaning never depends on red vs green alone.
- **Short labels, one line each:**
  - "LC4, LPLC2: looming-detector neurons in the fly's optic lobe. Here we drive them from the obstacle's size."
  - "Giant Fiber (DNp01): the descending neuron that triggers a fly's fastest escape jump. Here each spike is a button press."
  - "Active neurons: every other neuron in the simulated circuit that fired."

## What the panel needs from the run files

Almost everything is already recorded (`interface/fly_log.py`):

| Needed | Where |
|---|---|
| θ, gap, f, rate, driven counts per side and type | `brain.parquet`, per frame |
| Giant Fiber spikes per frame | `brain.parquet` (`spikes_GF_R`, `spikes_GF_L`) |
| Press per frame | `brain.parquet` (`fly_press`); `held` in `ticks.parquet` |
| On ground (did a press jump?) | `ticks.parquet` |
| Active-neuron counts, stuck share, flags | `brain.parquet`, `run.json` |
| Every neuron's spikes (version 2) | `spikes.npz` |
| **Which** neurons are driven | Not logged directly: the driven counts plus the fixed patch order (`loom_patches`, seeded per side) give it exactly. **Question for Jacob:** reconstruct it, or log the IDs? |

## Questions for Jacob

1. **Placement and size:** does a strip below the game fit the export resolution, or should the panel go beside the game?
2. **Binning:** OK to show spikes per 1/60 s in the export (the sum of 4 ticks), labelled as such?
3. **Driven neurons:** reconstruct them from counts + patch order, or log the IDs per frame?
4. **Raster length:** ~1 s for the Giant Fibers and ~2 s for active neurons are guesses. What reads well at playback speed?
5. **Order of work:** build version 1 for the Step 2 baseline replays, and leave version 2 for the showcase (R4)?
