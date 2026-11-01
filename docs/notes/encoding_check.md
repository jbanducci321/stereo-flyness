# Encoding check (Step 2.2): does the cube encoding behave as designed?

*Shannyn, 2026-11-01. Step 2.2 review of the cube input encoding (D41, with R × f from D45 and θ_full = 200° from D43).*

## What was run

No brain, nothing simulated: the bot plays each level, and the encoding records, tick by tick, what the fly would see (`scripts/inspect_encoding.py`, Jacob's tool from PR #19). Training levels only; the held-out suite stays unseen until the baseline (D44).

```
uv run python scripts/generate_levels.py --suite training --limit 2
uv run python scripts/inspect_encoding.py cube-easy-0 cube-medium-0 cube-hard-0 --theta-full 200
```

- Code: `main` after PR #20 (merged into `sc-reading-notes` at `9f43524`). That encoder still defaulted to flat R; rate scaling (R × f) doesn't change anything checked here, which is geometry (θ, gap, f, patch size).
- Output: `results/encoding/200deg_collision/` (git-ignored): one CSV per level, plus `summary.md`.

## Results

| Check | Result | Evidence |
|---|---|---|
| θ matches the geometry for a single block | **Pass** | Tick 420 (hard-0): gap 39.7 → θ 41.4°; 2·atan(15/39.7) = 41.4°. Tick 2220: gap 41.9 → 39.4°, the calibration point |
| Taller columns look bigger | **Pass** | 60-unit wall at gap 24.6 → 92.8° (a single block there: ~63°). 90-unit wall at gap 60.3 → 65.2° (single: ~28°). Both match θ = atan((top − eye)/d) + atan((eye − bottom)/d) with the eye at y = 15 |
| Patch size f = θ / θ_full | **Pass** | At θ = 41.4°: f = 0.207, driving right LC4 10/50, right LPLC2 21/102, left LC4 11/54, left LPLC2 22/108 |
| f stays below 1 | As expected | Max θ ~180° gives f ~0.9; the whole population is never driven (0% of ticks) |
| Bot-driven label | **Pass** | In the summary header, and `driver = bot` on every row (hard rule 10) |
| Ideal 39° fly | Matches D44's classes | easy-0 completed; medium-0 dies at 30%, (b) a spike on a block (merged 60-unit column, jump at gap 82); hard-0 dies at 14%, (a) a spike landed onto from above |
| Ceilings don't loom | **Not checked** | None of these three levels had a clear case |

## Issue found: ground pit spikes look too big

**What:** several hard-0 presses read θ ≈ 52° at a gap of ~25, where a ground-level block would read ~60° and the visible part of the object should read much less. The tick files show the obstacle's visual cell is **−13 → 17**:

| | Ordinary spike (hard-0, tick 2460) | Pit spike (hard-0, tick 1308) |
|---|---|---|
| Gap | 30.3 | 25.9 |
| Visual cell (bottom → top) | 0 → 30 | **−13 → 17** |
| θ now | 52.7° | 51.7° |
| θ with the cell clipped at the ground | 52.7° (unchanged) | **~34.5°** |

**Why:** pit spikes straddle the ground line (`docs/game_physics.md` §5), so "visual cell = hitbox centre ± 15" (D41) puts 13 units of the cell below the floor. The formula counts that part, so pit spikes look ~50% bigger than anything a fly could see above the ground, and the fly would jump at them early.

**Proposed fix: clip every visual cell at the ground (y ≥ 0).**
- It's geometry: the floor is opaque. No dial, no new constant.
- Only objects that dip below the ground change.
- It corrects D41, a joint decision, so it's logged before the Step 2 baseline.
- **Recruitment probably doesn't need redoing:** a smaller θ means a smaller patch, i.e. a subset of the same neurons in the same order, at rates inside the covered range. The final subcircuit's rule 5 check (D46) should use the corrected encoding.
- **Still open:** the drawn pit spike is smaller than even its above-ground cell (its hitbox is ~9 × 10.8). Clipping at the ground is the minimal correction; matching drawn shapes isn't attempted, since the game's visuals aren't modelled (D20).

## Notes for the Step 2 analysis

- **The bot presses at the last moment:** θ ~150–180° at a gap of 0–5. A 39° fly presses ~125 ms earlier. Both are inside the single-spike window (gap 1–73), so the difference doesn't matter there.
- **Hard levels sometimes need early presses:** the bot pressed at θ 37–53° in tight sequences, where a 39° fly would press only 0–42 ms earlier, and press windows can be under 50 ms (`docs/level_generators.md`). Expect deaths there.
- **Some bot jumps happen with nothing looming:** θ 3.8° at gap 450 (easy-0) and 5.2° at gap 330 (medium-0). These are probably jumps up onto platforms. A fly can't be prompted to make them, so they belong with the "invisible to the encoding" deaths (D44 class a).
- **Short run-ups** (the 10th-percentile run-up is ~30 units) start with the obstacle already past 39°, so the fly's delay matters more there than its threshold.

## Still to check

- Ceilings not looming, on a level that has one.
- The pit-spike numbers again, once ground clipping is in.
- The encoding with R × f on (D45): the logged per-neuron rate should be R × f.
