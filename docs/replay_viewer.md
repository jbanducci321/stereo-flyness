# Replay viewer (Step 1.3, D25)

`src/stereo_flyness/viewer/` draws and plays back recorded runs (`docs/game_engine.md` run logs). It depends on `game/`; `game/` never depends on it. It uses **pygame** for drawing and the **ffmpeg** program for video export.

## Usage

```bash
uv run python scripts/replay.py results/runs/bot_stereo_madness              # play in a window
uv run python scripts/replay.py results/runs/bot_stereo_madness --still 30   # picture at 30 s
uv run python scripts/replay.py results/runs/bot_stereo_madness --export     # MP4 video
#   --audio FILE  mix in a local audio file    --no-overlay  hide the text overlay
#   --level PATH  level JSON (otherwise found from the run's summary)    --out PATH  output file
```

**Window controls:**

| Key | Action |
|---|---|
| Space | Pause / play |
| ← / → | ∓1 s |
| , / . | One frame back / forward |
| − / + | Speed 0.25×–2× |
| R | Restart |
| Esc | Quit |

Outputs go to `results/replays/` (git-ignored). Replays of Stereo Madness show RobTop's level design, so they stay local (D9).

## Pieces

| File | What it does |
|---|---|
| `timeline.py` | Run log + level → per-tick view data. It rebuilds the ship floor/ceiling from portal events (logs don't store them). |
| `render.py` | Draws one moment. Objects are drawn **as their real hitboxes** (what you see is what the engine collides with): blocks and slabs grey, hazards red, portals outlined (magenta ship, green cube), ship bounds blue, cube cyan, ship orange with a nose, a red ✕ at death. GD-style follow camera: the player sits 30% across; the ground sits low in cube mode; the ship area is centred in ship mode. |
| `playback.py` | 60 fps window, playback clock, controls, overlay (progress bar, time/progress/mode, a button-held indicator, event flashes). The logic is testable without a window. |
| `export.py` | Renders every 4th physics tick (60 fps) headlessly and pipes the frames to ffmpeg (H.264 MP4), holding the last frame for 1 s. `event_cues()` lists every event's time. |

**Speed:** exporting the 84.6 s Stereo Madness run takes about 2 minutes on Jacob's laptop (5,135 frames, 4.8 MB).

## Hooks for the final showcase
The polished final video of the fly's winning run is the last thing built (D19). This viewer is its base:
- **Brain panel:** `brain_panel.py` (R2, 2026-11-06) draws a 200 px strip under the game for every brain run (`--no-brain` leaves it out). It shows only what `brain.parquet` logged, unaltered. Left, in blue: **our input** for the mode shown (θ, f and R × f for the cube; whatever the ship's controller logs). Right, in yellow: **the fly's spikes**, one lane per watched group over the last second, the press each frame decided, how many neurons fired, and the stuck flag. It works for cube, ship and mixed runs. **The layout is provisional and says so on screen:** which neurons to show, with what labels, colours and visual-field layout, is Shannyn's design (R3).
- **Music:** `--audio FILE` mixes a local audio file into the export, aligned to the run's start.
- **Sound effects:** `event_cues()` gives the exact time of every `jump`, `death`, `portal_*` and `finish`, ready to place sounds.
- **Nicer graphics:** sprites in place of hitbox rectangles. Keep a "hitbox view" option for debugging and honesty.

**Copyright:** the Stereo Madness song (ForeverBound) and the game's sound effects and level design belong to their owners. Locally, the viewer only ever loads them from the user's own files; nothing is committed. **Publishing** a video with them needs permission, or a royalty-free or commissioned track instead.
