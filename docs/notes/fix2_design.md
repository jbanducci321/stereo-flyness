# Iteration 2, fix 2: close obstacles (the double spike), a design note for discussion

*Jacob, 2026-11-15; **Shannyn's argument, predictions and answers added the same day** (end). The plan is agreed except the choosing rule for (b), marked below; **nothing is run.** Under D55, fix 2 starts with a no-brain check: the ideal fly across thresholds on the new levels. That check is a run, so this note, with Shannyn's argument and predictions, comes first, as fix 1's did. Shannyn's sections are marked **[Shannyn]**. Nothing in it uses Stereo Madness beyond what D54 records.*

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

**Agreed (Shannyn, 2026-11-15): (a) is the default.** (b) is tested only if the check shows a window, and then **only as a labelled variant, never as the fly of record**: one D55 dial, labelled "a late-threshold fly, inside the range measured in real flies", reported beside the record, chosen by a rule fixed before the sweep is read (below). (c) repeats iteration 1. (d) invents a mechanism. The long-mode take-off is future work: it needs a new readout and output rule.

## The check (step 1), fixed before it runs

**The ideal fly across thresholds on the frozen iteration-2 training levels** (50 levels, `ideal_fly.py --sweep 10 175 5 --by-obstacle`, collision course, both with and without fix 1's (ii) once fix 1 is settled). No brain.

**Two ideal flies, both without a brain:**
1. **Spread-aware (the main one; Shannyn, 2026-11-15):** each approach's threshold is drawn from the model fly's own first-spike distribution, normal with mean 37.1° and s.d. 7.3° (R2, closed loop), instead of fixed. A new approach starts whenever a different object becomes the nearest looming one (D45's rule: the next column of the same object isn't a new approach). Draws below 1° are set to 1°. 20 draws per level (seeds 0–19). It answers the real question: how often a fly with this spread clears each obstacle.
2. **Fixed thresholds (10–175° in 5° steps, plus 39°):** shows where each obstacle's edges are.

Reported, per threshold (fixed) and over the draws (spread-aware):
- **per obstacle type:** spike1/2/3, spaced pairs **by gap** (1, 2, 3; a 4-cell gap counts as two single spikes), drops (fix case and control), stairs, slabs;
- **whole levels completed**;
- **the window:** the thresholds at which every double spike is cleared in isolation, and how many levels each threshold completes.

**Read against the fly's spread** (37.1 ± 7.3° closed loop; 39 ± 14° in real flies):
- **If a window lies inside the real range and costs nothing elsewhere:** (b) is designed, as a labelled variant.
  - **The choosing rule, proposed for Shannyn to fix before the sweep is read:** run the spread-aware fly with its mean shifted, m = 38–53° in 1° steps, the spread kept at 7.3°. Pick the m that completes the most iteration-2 training levels (averaged over the 20 draws), ties to the lowest. (b) goes ahead only if that m beats m = 37.1° by at least **[Shannyn: N]** levels.
  - The variant keeps the fly's spread and moves only its mean, which is what re-calibrating θ_full would do.
- **Otherwise:** report the double spike, the triple spike and the 1-cell spaced pair as the limit of a one-shot escape reflex, with the geometry table as context.

**Spaced pairs with 2–4 empty cells** need two jumps: land between, jump again. After landing, the second spike is close and often already past 39° (a short run-up, D45's class (c)). The ideal fly presses on the next tick; the real fly has a response delay. The check reports how often the ideal fly clears them; a real-fly comparison needs fly runs, which come later.

## [Shannyn] Biology argument

*Shannyn, 2026-11-15.*

**What the Giant Fiber escape is for.** It launches the fly away from an approaching threat as fast as possible, triggered when the looming object reaches a size threshold (LPLC2 carrying angular size, LC4 angular velocity; Ache et al. 2019). It is a one-shot reflex: it decides *when* to go, not *where* to land, and nothing in it plans a trajectory over a second obstacle. So a close group of obstacles that needs a precisely aimed jump is outside what this reflex does, in a real fly as in ours.

**The double spike is about spread, not threshold.** The ideal fly at 39° clears every double spike it reaches; the model fly fails about half the time because its first spike varies (37.1 ± 7.3°) around the 38° edge. That variability is fly-like: real flies are *more* variable (39 ± 14°; von Reyn et al. 2014). A real fly with this reflex would fail this obstacle about as often or more. **That is a finding about putting an escape reflex into a timing game, and it's reported as such.**

**Moving the calibration (b) is defensible only as a labelled variant, never as the fly of record.** The fly of record is calibrated to the *mean* measured threshold, which is the one principled choice. The ±14° is variability between trials and flies, not a range of equally good means, so any other target is chosen for performance: tuning, even inside the measured range. Under D55 that's allowed as one dial set on training levels, if it's labelled "a late-threshold fly, inside the range measured in real flies", reported beside the record, and set by a rule fixed before the sweep is read. Iteration 1 already showed that later isn't simply better (50 Hz did worse on Stereo Madness, D54).

**The long-mode take-off: future work.** Real flies also take off through a slower, Giant Fiber–independent route, with the wings raised before the jump (von Reyn et al. 2014); slower looms favour it. Using it would need a new readout from descending neurons that aren't well mapped for this behaviour, and a new output rule: a new mechanism, not a fix to our interface. Worth naming as future work, not iteration 2.

**How the write-up words it:** "Close groups of obstacles need an aimed jump. The Giant Fiber escape fires at a size threshold with a natural spread and doesn't aim, so the fly clears a double spike only when its threshold falls on the late side of its spread, and can't clear triple spikes or close pairs at any threshold measured in real flies. We report this as a limit of a one-shot escape reflex in this game."

## [Shannyn] Predictions (written before step 1 runs)

*Shannyn, 2026-11-15, before step 1 runs. Scored hit or miss when the check is opened; confidence isn't part of the score.*

| | Prediction | Why | Confidence |
|---|---|---|---|
| Ideal fly, double spikes in iteration-2 levels: cleared at 39°? | **Yes, ≥ 90% of those it reaches** | 127/127 on iteration-1 training; the new levels add contexts (after drops, short run-ups) that may cost a few | Medium-high |
| Is there a threshold window inside 25–53° (39 ± 14°) that clears every double spike? | **Yes, from ~38–40° up to 53°** | In isolation any threshold from 38° up clears them | Medium-high |
| Triple spikes and 1-cell spaced pairs: cleared at any threshold below 90°? | **No** | They need θ ≥ ~94° (geometry table) | High |
| Spaced pairs with 2–4 empty cells (two jumps): cleared by the ideal 39° fly? | **Less often as the gap shrinks: 3-cell gaps mostly cleared, 2-cell gaps mostly not** | A jump from the 39° point lands ~4.5 cells on, close to where a second spike 2 cells past the first sits | Low |
| Does any single threshold complete more iteration-2 training levels than 39°? By how many? | **Yes, a later one (40–55°), but by only a few levels (≤ 3)** | On iteration-1 training, 45–50° completed 22/50 against 21 at 39° (D47's check) | Medium |
| Outcome: (a) report as a limit, or (b) worth designing? | **(a), report as a limit** | A window will exist, but I expect its gain to be small and to cost elsewhere (as 50 Hz did on Stereo Madness) | Medium-high |

## Shannyn's answers (2026-11-15)

1. **(a) is the right default:** it's the spread, not the threshold, and real flies vary even more (39 ± 14°), so a real fly would fail this about as often. (b) is tested only if a window shows up.
2. **(b) is defensible only as a labelled variant, never as the fly of record.** ±14° is variability, not a range of equally good means, so a later target is tuning. If done: one D55 dial, labelled "a late-threshold fly, inside the range measured in real flies", with the choosing rule fixed before the sweep is read.
3. **The long-mode take-off is future work:** a new readout and output rule, a new mechanism, not an interface fix.
4. **Added to the check:** the spread-aware ideal fly (above).

**Still open:** the choosing rule's N (above).

## The original questions (kept for the record)

1. Is (a), reporting the limit, the right default, with (b) tested only if a window shows up inside the real range?
2. Is moving the calibration target (b) defensible at all, given the fly of record is calibrated to the mean real-fly threshold?
3. The long-mode take-off: a later, slower take-off without the Giant Fiber. Future work, or worth a look now?
4. Anything to add to the check?
