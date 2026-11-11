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

## Jacob's answers (2026-11-06), and version 1 as built

Version 1 is built to this design (`src/stereo_flyness/viewer/brain_panel.py`, `docs/replay_viewer.md`). The answers below are what it does; any of them can change.

1. **Placement:** a strip below the game, 230 px, so the game keeps its full 1280 × 720 and the export is 1280 × 950.
2. **Binning:** yes. The "now" numbers (Giant Fiber counts, active neurons) sum every tick since the previous drawn frame: 4 ticks in video, labelled "spikes in the last 4 ticks (1/60 s)". The live window does the same for whatever it skipped. The rasters and the active-neuron trace draw every tick, so nothing is binned there.
3. **Driven neurons:** reconstructed, not logged. Driven neurons fill the patch order from its start (D41), so dot *k* of a row is lit if *k* < that row's logged driven count. That is exact, and the dots never need the IDs. The IDs, if needed, come from `loom_patches` with the same seed.
4. **Raster lengths:** 1 s for the Giant Fibers and 2 s for active neurons, as you proposed. They read well at 1× in the training replays.
5. **Order:** version 1 now; version 2 (the Giant Fiber's input partners) for the showcase (R4).

**Two additions, for your review:**
- **Stimulated neurons, for the active-neuron count:** runs now save the IDs we drive in `spikes.npz`. Older cube runs drive exactly LC4 + LPLC2, so the panel uses the v783 list (`configs/target_neurons_783.csv`). It checks that against the count the run recorded, and labels the count "raw" if they disagree.
- **Ship mode:** column 1 lists the ship's logged inputs as text, and column 2 adds a raster for any other watched group (e.g. the ship's output neurons), until your ship design says how to show them.

## Ship mode (D53): draft, 2026-11-11

*Shannyn. For Jacob to build once B is registered. Same three columns, same rules (recorded activity unaltered, our input separate and labelled, artefacts labelled). Only what changes in ship mode is listed.*

```
+---------------------------------------------------------------------------+
|                GAME   [ ] <- target opening (our code), outlined          |
|   SIMULATION REPLAY: the ship is controlled by the fly brain model        |
+------------------------+--------------------------+-----------------------+
| WHAT WE SHOW THE FLY   | THE FLY'S FLIGHT NEURONS | THE REST OF THE BRAIN |
| (our input, D53)  [B]  | (the model's activity)   | (unchanged)           |
|                        |                          |                       |
|  OUR STEERING          |  DNp22 left  DNp22 right |  active neurons ~~~~  |
|  target  Δy +42        |     (o)         (o)      |  stuck-state  [ 2%]   |
|  speed: vy | v_req ◇   |  |  | || |    | |||  |   |                       |
|                        |  release ▼ ▼   hold ════ |                       |
|  MOTION WE DRIVE       |  VS1-8 L ▪▪▪▪▪▪▪▪        |                       |
|        left   right    |  VS1-8 R ▪▪▪▪▪▪▪▪        |                       |
|  down  [███]  [███]    |  DNp20 (recorded only)   |                       |
|  up    [   ]  [   ]    |                          |                       |
|  ω ↓ 18°/s  f 60% 90 Hz|                          |                       |
+------------------------+--------------------------+-----------------------+
```

### On the game: the target (our code)

- **An outlined white bracket on the target opening,** with a thin line from the ship's eye to its centre. Labelled "target (our code)".
- It is **our input, not something the fly computes**, so it uses the input style (white, outlined), never amber.
- It moves to the next column only when the ship's back has cleared the current one (D53), so viewers can see when the target changes.
- **Not shown for self-motion only** (no target); shown for B and C.

### Column 1: "What we show the fly" (ship)

**Variant tag** in the header: B, C, self-motion only, 90°/s or corrected signs (from `run.json`), so a replay can't be mistaken for another condition.

**Our steering** (top):
- **Δy** to the target centre, and the distance to its column (dx).
- **A small vertical speed gauge:** the ship's vertical speed vy (solid white tick) and **v_req** (hollow diamond). **The gap between them is what B drives.** In C the vy tick is greyed and labelled "not used in C".

**Motion we drive** (bottom):
- **Two eyes × two groups:** "down" (T4d + T5d) and "up" (T4c + T5c), as **one bar each** rather than a dot per neuron. Every neuron in a group is driven at the same rate (D53), so one bar shows it exactly; a dot per neuron (~1,500 per bar) would add nothing. Brightness = the rate we send; the bar's label gives the neuron count (e.g. "down, right: 1,504").
- Only one group is ever lit (the sign of ω), on both eyes together.
- **Readouts:** ω (°/s, with ↓ or ↑), f, and the rate per neuron. A gauge marks ω_full (30°/s, or 90°/s in that variant), where f reaches 100%.
- **Honesty line:** "Image motion computed from the level's geometry and our target speed, not from pixels."

### Column 2: "The fly's flight neurons" (the model's activity)

- **DNp22, left and right** (the readout), as the Giant Fibers are for the cube: large amber markers that flash on every spike, with the spike count, and a 1 s raster each.
- **Release and hold** on the same time axis: ▼ a **release**, one tick after a DNp22 spike (D53); a thin white bar for **held** ticks, since silence holds. White, because they're game events.
- **VS cells:** a row of 8 small amber squares per side (VS1–VS8), each flashing on its spikes. They're the pathway between our input and DNp22, so viewers can see the signal travel. Short label: "VS cells: wide-field motion neurons that stabilise flight. The model's VS cells spike; real ones mostly signal with graded voltage."
- **DNp20:** two small grey-outlined markers flashing amber on spikes, labelled "DNp20: recorded, not read by the game".

### Column 3

Unchanged. The active-neuron count excludes the neurons we stimulate, which in ship mode are the T4/T5 groups we drive (~6,000 neurons, both eyes), as `spikes.npz` records.

### Mixed levels and Stereo Madness

- Columns 1 and 2 switch with the mode on the tick the portal changes it.
- **Every raster and trace gets a vertical line at a mode change,** labelled "→ ship" or "→ cube", so a raster that spans both modes reads correctly.

### One-line labels (ship)

- "T4/T5: motion-detector neurons in the fly's optic lobe. Here we drive the 'down' or 'up' set from image motion our code computes."
- "Target (our code): the next opening, and the vertical speed that reaches it. Real flies set altitude by tracking edges through a circuit nobody has found; this stands in for it."
- "DNp22 (≈ DNOVS2): a descending neuron driven by VS cells. Here any spike releases the button; silence holds it."

### What the ship column needs from the run files

| Needed | Where |
|---|---|
| Δy, dx, v_req, vy, ω, ω_self(vy), ω_self(v_req), f, rate, driven group | `brain.parquet`, per frame (D53 says these are logged every tick) |
| Target opening (column x, bottom, top) | **Not logged yet:** log it per frame, or recompute it from the level with the opening finder? |
| DNp22 spikes, releases | `brain.parquet` (`spikes_DNp22_*`, `fly_press`) |
| VS1–VS8 and DNp20 spikes | `spikes.npz` (every neuron), or log them as watched groups? |
| Variant | `run.json` |

### Questions for Jacob

1. **The target bracket on the game:** OK to draw on the game area, as long as it's outlined, white and labelled? If you'd rather keep the game untouched, it can go in column 1 as a small side view instead.
2. **Target opening:** log it per frame, or recompute it from the level? Logging is safer: the replay then shows what the run actually used.
3. **VS and DNp20:** from `spikes.npz`, or add them as watched groups in `brain.parquet`?
4. **Space:** column 1 now holds two blocks. Does it fit in the 230 px strip, or does the speed gauge need to go beside the bars?
