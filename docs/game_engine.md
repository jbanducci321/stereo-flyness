# Game engine (Step 1.1, D23)

The engine plays our levels (`docs/level_format.md`) with Geometry Dash 2.2 physics (`docs/game_physics.md`, the source of truth for every number and rule).

| File | What it holds |
|---|---|
| `src/stereo_flyness/game/physics.py` | Constants, each citing its physics-doc section |
| `src/stereo_flyness/game/player.py` | Player state |
| `src/stereo_flyness/game/engine.py` | `Game` |
| `src/stereo_flyness/game/recorder.py` | Run logs |

The `game/` package never imports `brain/` or `interface/` (enforced by a test).

## Interface (D23)

```python
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level
from stereo_flyness.game.recorder import RunLog, play

game = Game(Level.load(path))
game.tick(held=True)      # advance one 240 Hz tick; the ONLY input is "button held?"
game.player               # x, y (hitbox centre, level units), vy, mode, on_ground, alive
game.events               # what happened in the last tick, e.g. ["jump"], ["land"], ["portal_ship"], ["death"], ["finish"]
game.over, game.finished, game.death, game.progress, game.time, game.bounds

log = play(Game(level), policy=lambda g: should_press(g))   # run to the end, logging every tick
log.summary               # completed, progress, ticks, seconds, jumps, death kind/id/x/y
log.save(folder); RunLog.load(folder)
```

- **One input, every tick:** button held or not.
  - The bot and test scripts call `tick` directly or use `play`.
  - The brain interface will call `tick` from its frame callback (`BrainStepper.run_frames`).
- **Ticks and frames:** physics runs at **240 ticks/s**. One 60 fps game frame is 4 ticks.
  - How often the brain is consulted (every tick, every frame, …) and how its spikes become button presses are interface decisions (T4), not engine ones.
- **Deterministic:** no randomness and 64-bit floats. The same inputs always give the same run, so replaying a log's `held` column reproduces it exactly (tested).

## Per-tick order (`docs/game_physics.md` §2)
1. **Velocity.**
   - Cube: jump if on the ground and held, then gravity (also on the jump tick, §3), and a −15 fall cap.
   - Ship: direction-dependent hold/release acceleration, then the +8 / −6.4 limits.
2. **Move:** x += 1.29825 (311.58 units/s); y += vy × 0.225.
3. **Collisions.**
   - **The ground (cube) or the ship's floor/ceiling (ship).** The ship slides along these and never dies on them.
   - **Solids:**
     - land on top within 10 units (cube) or 6 (ship);
     - the ship bumps along undersides;
     - otherwise death only if the solid touches the 9 × 9 inner hitbox.
     - Cube landings apply stair snapping.
   - **Hazards:** death on touching the 30 × 30 hitbox.
   - **Portals:** switch mode on touching one, once each. A ship portal sets the ship area from its height.
4. **End:** reaching the level's `length` finishes the run.

## Run logs (R1, D19)
- **`ticks.parquet`:** one row per tick: `tick, time, x, y, vy, mode, held, on_ground, events` (events `;`-joined).
- **`summary.json`:** the `RunSummary`.
- **Where they go:** `results/` (git-ignored). Logs from Stereo Madness are RobTop-derived content, so they also stay local.
- **Who uses them:** the replay viewer (R2/R3), metrics (progress, deaths by obstacle type) and sound-effect cues (`jump`, `death`, …).

## Speed
- Plain Python. A full Stereo Madness run (~20,000 ticks) takes well under a second; trivial inputs die within milliseconds.
- Optimise only if the bot's search needs it.

## Known assumptions
All of these are listed with how to check them in `docs/game_physics.md` §8:
- gravity on the jump tick;
- stair snapping applies to blocks;
- speed carries through portals;
- the ship's "falling" means vy < 0;
- no downward bump under blocks;
- solids are resolved before hazards.

**The bot beating Stereo Madness (Step 1.2) is the test of all of them.**
