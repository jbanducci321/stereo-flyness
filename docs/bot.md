# Search bot (Step 1.2, D24)

`src/stereo_flyness/game/bot.py` finds a button sequence that beats a level, or reports where it can't. It plays through the same `Game.tick(held)` interface as everything else (D23), so its runs are ordinary run logs.

## How it works
- **Decisions:** once per frame (4 ticks), hold or release for the next frame. It tries **release first**, so the winning run only presses when needed.
- **Depth-first with rewinding:** when both choices from a state lead only to death, it rewinds (`Game.snapshot`/`restore`, ~5 µs) and tries the other branch further back.
- **Failed-state memory:** states already fully explored and failed are skipped, so each distinct state is expanded once.
  - **Cube states:** merged only when identical. Holding vs releasing in mid-air often leads to the same state, which keeps the search tiny.
  - **Ship states:** merged when within a height step and a vertical-speed step (`MERGE_STEPS`, coarse to fine). Merging is an approximation, and too coarse a step gives **false "impossible" verdicts** (tested). So `solve()` only reports failure after re-checking at the finest step.
- **On failure:** the result gives the farthest x any branch reached and what killed the branches there (kind, GD ID, x). That's the diagnosis tool for levels or physics.
- **Budget:** `max_nodes` caps the search. *Proving* impossibility is expensive for the ship, since it means trying every trajectory before the obstacle; finding a winning path is usually fast.

```python
from stereo_flyness.game.bot import solve, replay
result = solve(level)          # BotResult: success, frame_inputs, nodes, farthest_x, stuck, merge_steps
log = replay(level, result)    # RunLog of the winning run (docs/game_engine.md)
```

## Results

| Level | Result |
|---|---|
| Hand-made tests (`tests/test_bot_cube.py`, `tests/test_bot_ship.py`) | Beats spikes, triple spikes, staircases, slab bridges, ship zigzags, narrow gaps, spiked corridors and mixed cube/ship levels. Pinpoints impossible walls and spike runs. |
| **Stereo Madness** (`scripts/bot_stereo_madness.py`) | **Beaten** in ~5 s (71,942 states): 84.6 s run, 77 jumps. Portals at 25.5 s, 40.2 s and 73.4 s match the data and the video. |

**What beating Stereo Madness does and doesn't show** (`docs/game_physics.md` §11):
- **It shows the conversion is correct and the physics is roughly right.** Only gross errors (e.g. +25% gravity) make it unbeatable.
- **It doesn't confirm fine details.** The level is still beatable with no jump-tick gravity, no stair snapping, no 0.9 scaling, a 10% weaker jump, or a 25% weaker ship climb.

## Uses
1. **Validating levels:** every generated practice level must be beaten by the bot (Step 1.4).
2. **The perfect-player benchmark:** compare the fly's runs with the bot's (Steps 2–6).
3. **Watchable runs:** the winning Stereo Madness run (`results/runs/bot_stereo_madness/`, local only) is the first run for the replay viewer (Step 1.3).

Running the bot on Stereo Madness validates the game, not the fly, so the held-out rule (D7) is untouched.
