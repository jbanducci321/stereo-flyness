# Iteration 2, fix 2: close obstacles (the double spike), a design note for discussion

*Jacob, 2026-11-15. A draft for Shannyn; **nothing here is decided or run.** Under D55, fix 2 starts with a no-brain check: the ideal fly across thresholds on the new levels. That check is a run, so this note, with Shannyn's argument and predictions, comes first, as fix 1's did. Shannyn's sections are marked **[Shannyn]**. Nothing in it uses Stereo Madness beyond what D54 records.*

## What we already know (no new runs)

**Game geometry** (`iteration2_levels.md`; "game geometry, scripted cube, our encoding's θ; not a fly result"): one jump clears

| Group | if the take-off θ is |
|---|---|
| 1 spike | 23°–178° |
| 2 adjacent spikes | **38°**–178° |
| spike, 1 empty cell, spike | **94°**–178° |
| 3 adjacent spikes | **97°**–178° |
| spike, 2+ empty cells, spike | never in one jump: land between, jump again |

**The ideal fly on the iteration-1 training levels** (`ideal_fly.py --by-obstacle`, collision course, #60):
- At 39°, it clears **every double spike it reaches (127 of 127)** and every single spike, and **no triple spike (0 of 10)**.
- Alone after a full run-up, a double spike is cleared at any threshold from 39° up; a triple spike only from ~90°.

**The fly itself** (R2, D46): closed loop, its first Giant Fiber spike comes at **37.1 ± 7.3°**. Its mean sits just under the double spike's 38° edge, so roughly **half its approaches start too early** (about 55%, if the spread were normal). That fits R2 (deaths mostly early jumps, "d1") and D54 (7 of 10 record runs died at Stereo Madness's double spike, the Giant Fiber firing at ~36–38°).

**So the double spike isn't a wrong threshold.** A fly firing at exactly 39° clears it. The problem is that the fly's natural spread straddles the edge. Triple spikes and spike pairs one cell apart are different: they need θ ≥ ~94°, far outside anything measured in real flies (39 ± 14°, von Reyn et al. 2014), so no threshold near the biology clears them in one jump.

## What could change, and what each costs

The rules (D55): interface only, at most 2–3 new dials across iteration 2, each set on training levels, and a biology argument written first.

| | What changes | Cost under the rules | Biology |
|---|---|---|---|
| **(a) Report it as a limit** (default) | Nothing | None | A one-shot escape reflex fires at a size threshold with a natural spread; it doesn't aim a jump. D55's stated default. |
| **(b) Move the calibration target** | θ_full re-calibrated so the mean first spike sits later than 39°, but **inside the real fly's measured range** (39 ± 14°) | One dial, set on iteration-2 training levels. Changes the fly of record's calibration. | Arguable only within the measured spread; "the mean fly" is the principled choice, so any other target is tuning. |
| **(c) Tune R again** | The rate dial, as in iteration 1's Step 3 | One dial. Already tried: 50 Hz fires at ~84° (outside the real range), helped on held-out cube levels (not significantly) and did worse on Stereo Madness (D49, D50, D54) | Leaves the real fly's range |
| **(d) A release rule** | When a Giant Fiber spike becomes a press (e.g. only once θ has also stopped growing slowly) | A new output rule and at least one dial; needs its own argument | Speculative; there's no measured "release" step after the Giant Fiber in a short-mode escape |

**My lean:** (a) as the default, with (b) as the only option worth testing, and only if the check below shows a window inside the real fly's range that clears double spikes **without** costing other features. (c) repeats iteration 1. (d) invents a mechanism, which Shannyn has already argued against.

## The check (step 1), fixed before it runs

**The ideal fly across thresholds on the frozen iteration-2 training levels** (50 levels, `ideal_fly.py --sweep 10 175 5 --by-obstacle`, collision course, both with and without fix 1's (ii) once fix 1 is settled). No brain.

Reported, per threshold:
- **per obstacle type:** spike1/2/3, spaced pairs **by gap** (1, 2, 3; a 4-cell gap counts as two single spikes), drops (fix case and control), stairs, slabs;
- **whole levels completed**;
- **the window:** the thresholds at which every double spike is cleared in isolation, and how many levels each threshold completes.

**Read against the fly's spread** (37.1 ± 7.3° closed loop; 39 ± 14° in real flies):
- **If a window lies inside the real range and costs nothing elsewhere:** (b) is worth a design of its own, written before it's set.
- **Otherwise:** report the double spike, the triple spike and the 1-cell spaced pair as the limit of a one-shot escape reflex, with the geometry table as context.

**Spaced pairs with 2–4 empty cells** need two jumps: land between, jump again. After landing, the second spike is close and often already past 39° (a short run-up, D45's class (c)). The ideal fly presses on the next tick; the real fly has a response delay. The check reports how often the ideal fly clears them; a real-fly comparison needs fly runs, which come later.

## [Shannyn] Biology argument

*To fill in: whether a one-shot escape reflex can be expected to clear close obstacles; whether any calibration other than the mean real-fly threshold (39°) is defensible; and the open question of the Giant Fiber–independent long-mode take-off (von Reyn et al. 2014) as a route for later, slower take-offs, or whether that's future work.*

## [Shannyn] Predictions (written before step 1 runs)

| | Prediction | Why | Confidence |
|---|---|---|---|
| Ideal fly, double spikes in iteration-2 levels: cleared at 39°? | | | |
| Is there a threshold window inside 25–53° (39 ± 14°) that clears every double spike? | | | |
| Triple spikes and 1-cell spaced pairs: cleared at any threshold below 90°? | | | |
| Spaced pairs with 2–4 empty cells (two jumps): cleared by the ideal 39° fly? | | | |
| Does any single threshold complete more iteration-2 training levels than 39°? By how many? | | | |
| Outcome: (a) report as a limit, or (b) worth designing? | | | |

## Questions for Shannyn

1. Is (a), reporting the limit, the right default, with (b) tested only if a window shows up inside the real range?
2. Is moving the calibration target (b) defensible at all, given the fly of record is calibrated to the mean real-fly threshold?
3. The long-mode take-off: a later, slower take-off without the Giant Fiber. Future work, or worth a look now?
4. Anything to add to the check?
