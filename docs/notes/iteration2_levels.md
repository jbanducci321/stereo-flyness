# Iteration 2: the new levels' ranges

*Jacob, 2026-11-14; **Shannyn's answers folded in 2026-11-15** (end). The ranges are agreed, to be logged with D55; nothing is built yet.*

*Shannyn's rule (b) for iteration 2 (`docs/notes/iteration2_proposal.md`): the new levels' ranges are fixed **before** we study Stereo Madness further, and not centred on its spacings. So this note uses only the game's physics, our existing generator and our existing suites. **No Stereo Madness data was read for it.** It sets the ranges for the two features iteration 2 needs, and the suites built from them.*

## What the game's geometry allows (measured, not fly results)

**Label wherever this is shown (agreed): "game geometry, scripted cube, our encoding's θ; not a fly result".**

Measured in our engine on hand-made obstacles, with the cube driven by a script (no brain). θ is the looming angle of the first obstacle at take-off, as the encoding computes it (eye at the cube's front face and centre height, obstacle cell 30 units tall).

**One jump:** it carries the cube **134 units (4.5 cells)**, lasts **425 ms** and peaks **64 units** up.

**Walking off a raised platform without jumping:** the cube's **back edge** lands **~45 units** past the edge from a 1-block platform and **~64 units** from a 2-block one; its centre ~60 and ~79, its front ~75 and ~94. *(Corrected 2026-11-15: the first draft didn't say which part of the cube, and read as the front.)* So pits starting up to 2 cells past either edge catch a cube that just walks off (measured in the v4 chunks: k = 0–2 are fix cases from both heights, k = 3 a control).

**When one jump at take-off angle θ clears a group of spikes:**

| Group | One jump clears it if θ is | Notes |
|---|---|---|
| 1 spike | 23°–178° | almost any timing |
| 2 adjacent spikes | **38°**–178° | earlier than 38° lands on the second |
| spike, 1 empty cell, spike | **94°**–178° | a ~45 ms window, very late |
| 3 adjacent spikes | **97°**–178° | very late |
| spike, 2 or more empty cells, spike | never | needs two jumps: land between, jump again |

**Context for fix 2, not its test.** The real fly's threshold is ~39° (the record fly first-spikes at ~37°). So one fixed threshold near the real fly's clears single and adjacent double spikes only barely, and wider groups not at all. Clearing triple spikes or close pairs with one jump needs θ ≥ ~95°, far outside the range measured in real flies. That fits Shannyn's "limit of a one-shot escape reflex". **The formal check is still the ideal fly across thresholds on the new levels** (D55 draft), since real levels mix these groups with everything else.

## What the generator makes now (v3, D26)

**Cube chunks:**
- spikes in groups of 1–3 (adjacent only);
- a single block;
- stairs;
- a raised 1-block platform 4–8 long, sometimes with a spike on top;
- slab bridges and slab hops over ground pits.

**What it can't make, and iteration 2 needs:**
1. **A raised platform followed by pits.** On a platform, pits at ground level never loom, which is fix 1's case. Today, pits only appear *under* slabs, and every platform ends on plain ground.
2. **Spikes with empty cells between them.** Groups are always adjacent, so the "two separate jumps" and "one very late jump" cases never occur.

## Proposed new chunks and their ranges

### `platform_drop`: a raised platform, then pits
- **Platform height:** 1 or 2 blocks (easy: 1 only).
- **Platform length:** 4–8 cells, as the existing platform.
- **Ground between the platform's end and the pits:** k = 0, 1, 2 or 3 cells.
- **Fix case or control, computed per level, not by k alone** (Shannyn, 2026-11-15). Each drop is simulated with a cube that walks off the edge without pressing:
  - **fix case:** the walk-off cube lands in the pits (from on top they never loom today);
  - **control:** it lands on the ground first, so the pits loom as they do now.
  - Why not k alone: where a walk-off lands depends on the platform's height (and on the pits' hitboxes), so the label comes from simulating it. In the v4 chunks this gives k = 0–2 as fix cases and k = 3 as a control, from either height.
  - The label is stored with each level, so results are always split by it.
- **Pit strip width:** 2–5 cells (easy 2–3, medium 2–4, hard 2–5).
- **After the pits:** plain ground, or a platform of the same height (50/50).
- Every level stays bot-checked (D24): a combination the bot can't beat is re-rolled, as now.

### `platform_step_down`: a raised platform ending on plain ground (no-harm control)
- The same platform, no pits.
- **A no-harm condition** (Shannyn, 2026-11-15): the fixed fly jumps at these plain edges **no more often than the unfixed fly**. With gravity in the collision course, the cube falls onto empty ground, so nothing should loom.

### `step_down_pits`: a step down onto lower raised ground, then pits (Shannyn: yes)
- A 2-block run, then a 1-block run, each 2–4 cells long, then pits as in `platform_drop` (k = 0–3, the same widths per tier). *This exact shape is Jacob's proposal (2026-11-15) for Shannyn to confirm; she agreed the idea.*
- Unlike `platform_drop`, the cube reaches the lower level by walking off the higher one, so the no-press path crosses two drops.
- Fix case or control is computed per level, as above.

### `spaced_pair`: two spikes with empty cells between them
- **Gap:** 1–4 empty cells (easy 2–4, medium 1–4, hard 1–4). A gap of 0 is the existing `spike2`.
- **Second obstacle:** a spike, or a block (1 in 3), so it isn't always the same pattern.

**Tier weights** follow the existing pattern. Each new chunk appears at about the frequency of the existing platform chunk, and every iteration-2 level is guaranteed at least one `platform_drop` (or `step_down_pits`) and one `spaced_pair`, so each level tests both fixes.

## The suites

| Suite | Levels | Seeds | Use |
|---|---|---|---|
| **Iteration-2 training** | 50 cube (20 easy, 20 medium, 10 hard) | from 500,000 | designing and setting fixes, the ideal-fly check |
| **Iteration-2 held-out** | **40 cube** (16 easy, 16 medium, 8 hard) | from 2,000,000 | opened **once, at the end** (rule a) |
| Iteration-1 held-out cube | 20 (unchanged) | from 1,000,000 | "no worse on the old ones" (rule c) |

- **40 held-out levels, not 20,** so the "better at p < 0.05" bar can detect a real fix: a fix only changes levels where the fly would die at that feature, and our 20-level suites had many ties.
- Iteration-2 levels are 30 s long, like the others.
- **The suites are frozen before any run** (Shannyn, 2026-11-15): seeds, counts and generator version in the config, and every level's hash recorded and tested, as for the v3 levels.
- **Ship and mixed suites** for fix 3 come later, in fix 3's own note.

## How v4 builds them (2026-11-15; all five choices confirmed by Shannyn the same day)

Built in `generator.py` as version 4, used only by `configs/iteration2/level_suites.toml`. The v3 levels rebuild unchanged (freeze test). Choices the note didn't fix, for Shannyn to confirm:
1. **`step_down_pits` shape:** a 2-block run then a 1-block run, each 2–4 cells; medium and hard only (easy has 1-block drops only).
2. **The landing platform after pits** (the 50/50 "same-height platform" case): 3–5 cells long.
3. **The guarantee:** each level's guaranteed drop (`platform_drop` or `step_down_pits`, 50/50 where both exist) and spaced pair are placed among its first 6 chunks; all later chunks are random.
4. **A spaced pair with a 4-cell gap** reads as two single spikes in the per-obstacle results, since chunks in hard levels can be just 4 cells apart and the shapes are then identical.
5. **Easy levels are harder than v3's easy levels:** their tightest press windows drop to 8–21 ms (v3 easy kept out anything under ~50 ms). That's the new features doing their job, but it means "easy" isn't comparable across iterations. **For the write-up (Shannyn):** say that iteration-2 "easy" isn't comparable with iteration 1's.

**The 50 training levels are built** (results/iteration2/levels/training, not committed; 6 min). Hard levels needed 4 attempts on average (bot re-rolls). They contain 114 fix-case drops and 45 controls, with pit widths covering every tier's range (including 4–5-cell strips in medium and hard), spaced pairs in every tier, and 2-high plain step-downs in medium and hard. **Both suites are frozen** (2026-11-15, before any run): the 40 held-out levels were built without being opened (only a count was printed), and every level's hash in both suites is recorded in `tests/data/v4_level_hashes.json` and checked by `tests/test_generator_freeze.py`. A checksum file of the held-out level files sits next to them (`results/iteration2/levels/held_out_sha256.txt`, not committed), as for iteration 1.

## Engineering constraint

**Iteration 1's levels must rebuild exactly as they were.** The generator seeds every level with its version number, so simply bumping it to v4 would change every old level. The new chunks go behind a new version used only by the iteration-2 suites. A test checks that v3 levels are unchanged, tick for tick, for both old suites.

## Shannyn's answers (2026-11-15)

1. **Ranges:** right, with one change: fix case vs control is decided per level by whether a walk-off cube lands in the pits, not by k alone (now in `platform_drop`).
2. **The plain-edge control is a no-harm condition:** the fixed fly jumps at plain edges no more often than the unfixed one.
3. **The geometry table:** yes, as context, labelled "game geometry, scripted cube, our encoding's θ; not a fly result".
4. **Step-down with pits:** yes (now `step_down_pits`). **Freeze the suites before any run.**
