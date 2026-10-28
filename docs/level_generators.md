# Practice-level generators (Step 1.4, D26)

The fly trains and is tested on procedurally generated levels. Stereo Madness is held out for the final test (D7).

| File | What it holds |
|---|---|
| `src/stereo_flyness/game/generator.py` | Chunks, tiers, `generate()` |
| `src/stereo_flyness/game/difficulty.py` | Difficulty measurements |
| `src/stereo_flyness/game/suites.py` | Suites and caching |
| `configs/level_suites.toml` | The suites' seeds |
| `scripts/generate_levels.py` | Builds the suites |

## Rules
- **Seeded and deterministic:** `generate(kind, seed, difficulty)` always gives the same level for the same generator version (currently **v3**).
- **Physics-based difficulty, never Stereo Madness's layout** (D7). Only Stereo Madness's object kinds are used (D6).
- **Always beatable:** every level is beaten by the search bot (D24). An unbeatable candidate is re-rolled (attempt 1, 2, …), so each seed still maps to exactly one final level. In sampling, every level so far has been beatable on the first try.
- **Grid-aligned:** everything sits on the 30-unit grid. Levels are ~30 s long, with ~2 s of clear runway at the start and end.

## Building blocks

**Cube chunks:**

| Chunk | Description |
|---|---|
| `spike1` / `spike2` / `spike3` | Single, double, triple spikes |
| `block` | One block to jump onto or over |
| `stairs` | 2–3 rising steps, `stair_width` columns wide, 3 empty columns apart |
| `platform` | A raised 4–8 block run; a spike on top if the tier allows |
| `slab_bridge` | Ground pits with a slab walkway above |
| `slab_hops` | Pits with separate slab platforms |

**Ship chunks** (ground-level area, floor 0, ceiling 300):

| Chunk | Description |
|---|---|
| `gap_wall` | A wall with one opening |
| `zigzag` | Walls with alternating low/high openings |
| `spiked_corridor` | Floor pits plus hanging spikes |
| `tunnel` | An opening that drifts up or down |
| `pillar` | A column from the floor or ceiling |

**Mixed levels:** cube and ship sections (6–9 s each) alternate, starting and ending as the cube.
- **Into the ship:** a ground-level portal with **1 s of clear travel** on each side.
- **Back to the cube:** the cube portal sits in a **funnel wall** whose opening lies entirely within the portal's reach, so it can't be missed (unlike Stereo Madness's unreachable portal, D24).

## Difficulty tiers

| | Easy | Medium | Hard |
|---|---|---|---|
| Gap between cube chunks | 0.9–1.4 s | 0.6–1.0 s | 0.4–0.7 s |
| Cube chunk mix | spikes 1–2, block, platform (no spike) | + triple spikes, stairs (2-wide), platform spikes, slab bridges | heavier triples, stairs (1-wide pillars), slab bridges and hops |
| Gap between ship chunks | 1.0–1.5 s | 0.7–1.1 s | 0.5–0.8 s |
| Ship opening height | 5 rows (150) | 4 rows (120) | 3 rows (90) |

## Measuring difficulty (`difficulty.py`)
- **Reaction gaps:** obstacles are grouped into clusters; the flat travel between clusters is measured in seconds.
- **Press windows (cube):** for each press in the bot's winning run, the range of start times (tick by tick) that still survive until the next press. This is directly comparable to the Giant Fiber's ~35–50 ms response in the model.
  - Single spike: **238 ms**. Double spike: **142 ms**. Triple spike: **46 ms** (matches direct engine measurements).
  - Windows describe the slack along the bot's route, not every possible route.
- **Ship openings:** the smallest passable vertical space, column by column.

**Measurements changed the design.** At first, even easy levels had ~17 ms press moments:
- **The cause:** staircases (the jump must start from the very end of a step) and spikes on platforms.
- **The fix:** step width now scales by tier, and easy omits both.
- **Typical result** (median over levels):

| | Easy | Medium | Hard |
|---|---|---|---|
| Tightest press window | **~142 ms** | ~17 ms | ~17 ms |
| Presses under 50 ms | **0%** | ~15–20% | ~27–33% |

**For the fly:**
- Easy levels are a fair first test of a ~40 ms reflex.
- Medium and hard deliberately include moments faster than the Giant Fiber can react: triple spikes, narrow stair steps, tight sequences. That shows *where* the wiring sets a limit.

## Suites (`configs/level_suites.toml`)

| Suite | Cube | Ship | Mixed | Seeds | Used for |
|---|---|---|---|---|---|
| `training` | 50 | 50 | 50 | from 0 | Tuning the dials (Step 3) and everything before Stereo Madness |
| `held_out` | 20 | 20 | 20 | from 1,000,000 | Reporting generalisation only; **never used for tuning** |

Each kind is split easy/medium/hard 20/20/10 (training) and 8/8/4 (held-out).
- **Only seeds are committed.** `scripts/generate_levels.py` builds the levels into git-ignored `results/levels/<suite>/`:
  - each level, the bot's winning inputs, and a meta file with its statistics;
  - a `manifest.csv` per suite;
  - optional `gallery/` images (`--gallery`) showing the whole level with the bot's path.
- **Built once:** already-built levels are skipped. Ship and mixed levels take ~10–45 s each to validate, so jobs run in parallel (`--jobs`, default 4).
- **Changing the generator:** bump `GENERATOR_VERSION` and the config's `generator_version`. That deliberately invalidates the cache and the meaning of every seed.

```bash
uv run python scripts/generate_levels.py                              # both suites
uv run python scripts/generate_levels.py --suite training --limit 2 --gallery   # quick look
uv run python scripts/replay.py ...                                    # watch any run (docs/replay_viewer.md)
```
