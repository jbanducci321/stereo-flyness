# Iteration 2: the new levels' ranges, a proposal for discussion

*Jacob, 2026-11-14. A draft for Shannyn; **nothing here is decided or built.** Shannyn's rule (b) for iteration 2 (`docs/notes/iteration2_proposal.md`): the new levels' ranges are fixed **before** we study Stereo Madness further, and not centred on its spacings. So this note uses only the game's physics, our existing generator and our existing suites. **No Stereo Madness data was read for it.** It sets the ranges for the two features iteration 2 needs, and the suites built from them.*

## What the game's geometry allows (measured, not fly results)

Measured in our engine on hand-made obstacles, with the cube driven by a script (no brain). θ is the looming angle of the first obstacle at take-off, as the encoding computes it (eye at the cube's front face and centre height, obstacle cell 30 units tall).

**One jump:** it carries the cube **134 units (4.5 cells)**, lasts **425 ms** and peaks **64 units** up.

**Walking off a raised platform without jumping:** the cube lands **~45 units** past the edge from a 1-block platform and **~64 units** from a 2-block one. So pits within ~1.5 cells of a 1-block edge catch a cube that just walks off.

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
- **Ground between the platform's end and the pits:** k = 0, 1, 2 or 3 cells. This spans the case that matters:
  - k = 0–1: the pits catch a cube that walks off, and from on top they never loom (fix 1's case);
  - k = 2–3: the cube lands on the ground first, and the pits loom as they do now (a built-in control).
- **Pit strip width:** 2–5 cells (easy 2–3, medium 2–4, hard 2–5).
- **After the pits:** plain ground, or a platform of the same height (50/50).
- Every level stays bot-checked (D24): a combination the bot can't beat is re-rolled, as now.

### `platform_step_down`: a raised platform ending on plain ground (control)
- The same platform, no pits.
- Fix A must **not** make the fly jump here: with gravity in the collision course, the cube falls onto empty ground, so nothing should loom. If the fixed fly jumps at these edges, fix A is doing something it shouldn't.

### `spaced_pair`: two spikes with empty cells between them
- **Gap:** 1–4 empty cells (easy 2–4, medium 1–4, hard 1–4). A gap of 0 is the existing `spike2`.
- **Second obstacle:** a spike, or a block (1 in 3), so it isn't always the same pattern.

**Tier weights** follow the existing pattern. Each new chunk appears at about the frequency of the existing platform chunk, and every iteration-2 level is guaranteed at least one `platform_drop` and one `spaced_pair`, so each level tests both fixes.

## The suites

| Suite | Levels | Seeds | Use |
|---|---|---|---|
| **Iteration-2 training** | 50 cube (20 easy, 20 medium, 10 hard) | from 500,000 | designing and setting fixes, the ideal-fly check |
| **Iteration-2 held-out** | **40 cube** (16 easy, 16 medium, 8 hard) | from 2,000,000 | opened **once, at the end** (rule a) |
| Iteration-1 held-out cube | 20 (unchanged) | from 1,000,000 | "no worse on the old ones" (rule c) |

- **40 held-out levels, not 20,** so the "better at p < 0.05" bar can detect a real fix: a fix only changes levels where the fly would die at that feature, and our 20-level suites had many ties.
- Iteration-2 levels are 30 s long, like the others.
- **Ship and mixed suites** for fix 3 come later, in fix 3's own note.

## Engineering constraint

**Iteration 1's levels must rebuild exactly as they were.** The generator seeds every level with its version number, so simply bumping it to v4 would change every old level. The new chunks go behind a new version used only by the iteration-2 suites. A test checks that v3 levels are unchanged, tick for tick, for both old suites.

## Questions for Shannyn

1. Are the ranges right? In particular, pit widths 2–5, the k = 0–3 ground cells after the edge, and pair gaps 1–4.
2. Should the `platform_step_down` control count toward the "fix counts" bar ("the fly doesn't jump at plain edges"), or only be reported?
3. Is the geometry table fair to include in the write-up as context for fix 2, clearly labelled as not a fly result?
4. Anything you'd add, e.g. drops without platforms (a step down onto lower ground with pits)?
