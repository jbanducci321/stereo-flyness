# Step 2 report: the untuned fly on the held-out cube levels

*Jacob and Shannyn, 2026-11-03. Analysis as fixed in D48 (with its amendments, all made before the held-out results were opened). Results opened together on 2026-11-03. Full tables: `results/step2/final_held_out.md` (git-ignored), made by `scripts/step2_report.py`.*

**Setup.** The FlyWire v783 model (Shiu et al. 2024), frozen weights, on the final subcircuit (D46), plays 20 held-out cube levels it has never seen (easy 8, medium 8, hard 4). Baseline of record: R × f encoding, θ_full = 200°, collision-course looming, R = 150 Hz (D43, D45, D47), at seeds 0, 1 and 2: 60 runs. Two comparisons at seed 0, and three no-brain references: the ideal 39° fly, never press, and random presses at the fly's own press rate.

## Checks (all passed before any result was read)
- 100 fly runs read, all from commit `5d9de12`, every one replayed exactly from its logged presses.
- Run files unmodified since the batch finished (2026-11-02 20:59). References complete: 20 never press, 200 random, 20 + 20 ideal fly.
- 0 unclassified deaths, 0 stuck runs.

## Against the prediction (recorded before the runs; hit/miss defined before opening)
- **Ideal fly: 8/20 completed, all easy. Predicted ~8–9, nearly all easy: hit.**
- **Baseline, seed 0: 1/20 completed (easy). Predicted at or below the ideal fly's 8, nearly all easy: hit.**
- **What the hit leaves out:** both are hits by the rule fixed before opening, but "most easy levels completed" did not happen: the fly completes 1–3 of 8 easy levels per seed, against the ideal fly's 8.

## Main result
- **The untuned fly completes 6 of 60 runs, all on easy levels.** By seed: 1, 2 and 3 of 20. Mean progress **29%**.
- **One level is completed every time** (cube-easy-1000004, 3/3), one 2/3 (cube-easy-1000001) and one 1/3 (cube-easy-1000007). No medium or hard level is completed by any seed.
- **Against the floor and chance** (described only; no test was fixed): never press reaches 6%, random presses 8% (0 of 200 draws complete a level). The fly gets further than random on **18 of 20 levels**, measured against the mean progress of the 10 random draws on each level (seed 0; the same with each level's median over the three seeds). Against every one of the 10 draws, it gets further on 15 of 20. On the other 2 (cube-hard-1000003, cube-medium-1000003) it dies at the first object, a raised slab, as do never press, random presses and the ideal fly.
- **Against the ideal fly:** the ideal fly completes all 8 easy levels; the fly completes 1–3 of them per seed. Over all 20 levels, the ideal fly's mean progress is 59%, against the fly's 29%. Every completion the fly misses is on an easy level; on medium and hard levels the ideal fly completes nothing either, though it often gets further (e.g. cube-medium-1000006: 90% against 7–28%).

## Why it dies
54 baseline deaths:

| Class | Deaths | What it means |
|---|---|---|
| **(d1) jumped too early** | **33 (61%)** | The ideal 39° fly would have survived; the fly jumped earlier, at θ 19–37° |
| (b) the encoding's limit, object loomed | 14 (26%) | The ideal fly dies there too. 9 of them are raised slabs (y 38–68), which don't loom from the ground (D47) |
| (a) the encoding's limit, object never loomed | 5 (9%) | The ideal fly dies there too, on something that never loomed |
| (d2) jumped later | 2 (4%) | – |
| (s), (c), (d3), (u) | 0 | – |

- **(d1) dominates, as on training.** The typical (d1) death: on a row of spikes, the fly jumps a little early off the first one and lands on the second, which the first hides (D48 amendment). The ideal fly, jumping at 39°, clears both.
- **The rest are mostly the encoding:** raised slabs (D47) and tall blocks that a 39° jump can't clear either.

## Timing
- **The Giant Fiber's first spike, without bursts carried over from the previous object, comes at 37.1 ± 7.3°** (389 approaches), matching the open-loop calibration (38.0 ± 6.3° at 150 Hz) and well inside the real fly's 39 ± 14°.
- **Carry-over (split defined on training runs, applied unchanged):** 15% of approaches (67 of 456) start while the Giant Fiber is still firing from the previous object; their "first spike" comes within a couple of ticks, at a small θ. With them, the mean is 35.7°. No graded effect beyond 150 ms (rank correlation +0.08). Training gave 20% and 37.2°, so the pattern holds on held-out levels. **This is a property of the model** (it has no adaptation).
- **The 75 presses with nothing looming** (where D48 expected ~0) are all carry-over: every one came while the cube was in the air, within 150 ms of a Giant Fiber spike, and none started a jump. They have no effect on the game. D48 expected ~0 because no input should give no spikes; that missed because the Giant Fiber keeps firing briefly after its input stops. This is the same carry-over, and a property of the model.
- **Lone spikes:** the fly's jump falls inside the single-spike press window on 158 of 162 (98%).
- **So the fly isn't badly timed on average; its spread kills it.** The normal spread around ~37° (s.d. ~7°) puts more than half its first spikes before 39°, and rows of spikes punish early jumps. The ideal fly has no spread.

## Comparisons (paired by level against the baseline, seed 0)

| Against the baseline, seed 0 | Better | Worse | Equal | Sign test p | Reading |
|---|---|---|---|---|---|
| **Comparison 1: pre-D45 flat R** (θ_full 1,082°) | 3 | 15 | 2 | **0.008** | **worse** |
| Comparison 2: every object looms | 1 | 0 | 19 | 1.000 | no clear difference |
| *Noise line: baseline seed 1* | *9* | *3* | *8* | *0.146* | *reported only* |
| *Noise line: baseline seed 2* | *8* | *5* | *7* | *0.581* | *reported only* |

*D48 tests the two comparisons with no correction for testing two. Comparison 1's p = 0.008 would still be significant with the threshold halved for two comparisons (p < 0.025).*

- **Rate scaling matters (comparison 1).** Without it, the fly fires much earlier (first-spike θ median 26° against 36°), only 11 of 22 lone-spike jumps fall in the press window, it completes nothing, and 16 of its 20 deaths are (d1). The difference (15 levels worse) is well beyond what a change of seed does by itself (3–5 worse).
- **Making every object loom (comparison 2) changes almost nothing:** 19 of 20 levels end on the same object. Where an object now looms that didn't (cube-hard-1000001: (a) becomes (b)), the ideal fly can't clear it either, so the fly doesn't get further. Only 20 levels, so a small effect wouldn't show: "no clear difference", not "no difference".
- **Seed matters too:** seed 0 is the weakest of the three (1 completion against 2 and 3), and seeds 1 and 2 are better than seed 0 on 9 and 8 levels. That's the noise line; it doesn't change any reading, but it's why Step 3 uses three held-out seeds.

## Replays for the write-up (picked by rule)
Completed: cube-easy-1000004, seed 0. (a): cube-hard-1000001, seed 0. (b): cube-hard-1000000, seed 0. (d1): cube-easy-1000000, seed 0. (d2): cube-medium-1000000, seed 1.

## What it means
- **The untuned connectome model does play the game:** it gets further than random pressing (the mean of 10 draws) on 18 of 20 unseen levels and completes 6 of 60 runs, all on easy levels, as predicted.
- **Its Giant Fiber fires where the calibration says** (~37–38°), so the fly behaves in closed loop as it did open loop.
- **Most deaths are early jumps from the normal spread of that threshold,** on rows of spikes. Most of the rest are limits of the encoding (raised slabs, tall blocks) that a perfectly timed fly can't beat either.
- **Interpretation (ours, not a tested result): the levels punish early jumps far more than late ones.** 33 (d1) deaths against 2 (d2) fits the ideal fly doing best at a later threshold (45–50°, D47). So "the spread kills it" is partly about the game, not only the fly. And since the model's spread (~7°) is half the real fly's (14°), a real fly would probably do worse here, not better.
- **Two model properties to say plainly:** Giant Fiber bursts carry over from one object to the next (no adaptation), and the model's spread (s.d. ~7°) is smaller than the real fly's (14°).
- **Step 3 is unchanged** (D49, fixed before these results). Nothing here was used to choose anything.
