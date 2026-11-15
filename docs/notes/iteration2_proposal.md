# Iteration 2: fixing the walls Stereo Madness found, a proposal for discussion

*Jacob, 2026-11-14; Shannyn's answers and a draft D55 added the same day (end). **Nothing here is logged yet.** Iteration 1 (Steps 0–7 and D54's blind Stereo Madness test) is finished and isn't changed by anything below. Iteration 2 starts only once the D54 result is logged, the write-up's Part 1 is done and the code is tagged `v1.0-research`.*

## Where iteration 1 ended

The fly of record (150 Hz, whole brain, seeds 0–9) reached a **median 9.2%** of Stereo Madness; none of the 30 D54 runs got further than 10.9%, and 90 extra record runs hit the same two places. Those were run after the opening and weren't pre-specified (seeds 10–99), so they're a deviation from D54: logged there as one, kept, and given one footnote in the paper. The headline stays the pre-registered 10.

| Wall | Where | Runs (of the 90) | What happens |
|---|---|---|---|
| **The double spike** | x ~2390–2430 (9.1–9.2%) | 53 | The Giant Fiber fires at ~36–38°, the fly's normal threshold. From there, one jump clears the first spike but lands on the second. |
| **The pits after the raised platform** | x ~2875 (10.9%) | 33 | On top of the platform, the spikes in the pit ahead are below the cube, so they never loom. The fly gets no warning, walks off the edge and falls in. They only loom once it's falling, too late. |

Stills of both are in `results/replays/for_shannyn/` (not committed: Stereo Madness replays stay in `results/`, D9).

**Neither is a fault in the brain.** The pits are a gap in **our encoding**: we only show the fly obstacles that overlap the cube's current height (`interface/encoding.py`, "collision course"), and walking off an edge isn't on that list. The double spike is the fly doing exactly what it does on every level, but here its normal threshold is the wrong moment.

## What iteration 2 is, and isn't

- **It is:** fixing our interface where iteration 1 showed it was what limited the fly, and seeing how far the fly then gets.
- **It isn't:** a test of the fly. We've now seen the level, so nothing here is blind or held-out. It's reported as an exploratory Part 2, after Part 1, never mixed with it.
- **The brain doesn't change.** The connectome stays frozen (hard rule 1, unchanged). Every fix is in `src/stereo_flyness/interface/`, and the brain still decides when to act.

## Proposed rules (to become D55 once agreed)

1. **The connectome stays frozen**, as now.
2. **Interface changes only**, each with its own short design note and Shannyn's biology argument, written and dated before it's run (like ship design B).
3. **Stereo Madness is spent as a held-out test** (agreed 2026-11-14, to go in D54's result). Hard rule 5 is lifted for iteration 2 only: we may look at it and say so openly, but no design change is ever judged on it. Iteration 1's D54 runs and report are never rerun or changed.
4. **Every fix is judged on general levels.** New training and held-out levels with that feature in many sizes (gaps, close double obstacles), **not copies of Stereo Madness's**. A fix counts only if it helps there. Stereo Madness only shows how far the fly then gets, and if a fix helps only there, we report it as fitted to the level.
5. **Extra runs are agreed first.** Any run on held-out levels or Stereo Madness beyond what a decision fixes is agreed by both of us before it's run (agreed 2026-11-14).
6. **Few dials.** At most 2–3 new numbers across iteration 2, each set on training levels, never on Stereo Madness.
7. **Separate folders and configs** (`results/iteration2/`, `configs/iteration2/`), so no run can mix with iteration 1's.
8. **Everything is labelled.** The write-up and any video say "interface adjusted after seeing this level; brain wiring unchanged."

## Fix 1: let the fly see the gap

**The biology question (Shannyn):** real flies do judge gaps by sight. Walking Drosophila estimate a gap's width from the parallax of its far edge and decide whether to cross (gap climbing; Pick & Strauss 2005 and later work), so not seeing the pit is our limit, not the fly's. But gap climbing is slow and deliberate, not a fast escape like the Giant Fiber, and there's no well-mapped "gap → jump" circuit. So the question is how to show the gap to the brain in the most defensible way.

**Options:**

| | What changes | For | Against |
|---|---|---|---|
| **A. Count the fall** (proposed) | The collision course includes where the cube will be if it walks off the edge: the pit's spikes count as "in the way" once the cube would fall into them. They then loom like any other obstacle. | Smallest change. Nothing new reaches the brain: it's our encoding's idea of "in the way" made correct. No new dial. | Still sends the warning through the looming pathway, which isn't what a real fly uses for gaps. |
| **B. Show the edge** | The approaching drop-off is shown as an edge or motion feature to other visual neurons; we then look for a downstream neuron to read as "jump". | Closer to how flies really judge gaps. | A new input *and* a new output rule; much more work; the output neuron is a guess. |
| **C. Something from the gap-climbing literature** | Shannyn's call. | | |

**Proposal: A for iteration 2, with B named as future work.** Before running anything, Shannyn writes down what A should do on the new gap levels.

## Fix 2: the double spike

**First, find out whether it's a threshold problem at all, with no brain.** Run the ideal fly (`scripts/ideal_fly.py`, jumps at a fixed θ) on new double-spike levels across a range of thresholds:
- If some single threshold clears both spikes *and* the rest of the levels, the fly simply fires at the wrong θ for this obstacle.
- If no single threshold works, one looming signal can't time this jump, and the fix has to be different.

**What we already know:** a later threshold isn't free. The 50 Hz variant fires later and died *earlier* in Stereo Madness, at the pits after the block (6%). So I don't expect a one-dial fix, and I'd rather find out cheaply before designing one.

**Possible directions, for after that check (Shannyn's views wanted):**
- ~~the looming signal for a close pair of obstacles treated as one wider object~~ (withdrawn: a bigger object reaches threshold sooner, Ache et al. 2019, so the fly would jump *earlier*, and it already jumps too early here);
- something about when the jump is released, not just when the Giant Fiber fires.

If no single threshold works, the default is to report it as **a limit of a one-shot escape reflex**, not to invent a mechanism: real escape timing selects the take-off mode; it doesn't aim the jump (Shannyn, below).

## Fix 3: the ship

No run has reached a ship section yet. Iteration 1 already showed the ship can't descend fast enough (R6: DNp22 tops out at ~67.5% releases against the ~61% needed just to hold height). A complete run needs a new ship output rule, argued on its own merits. That's the largest piece, and I'd leave it until fixes 1 and 2 show the cube can get there.

## Order and milestones

1. Agree on these rules and log D55.
2. Fix 1 (gap), tested on the new gap levels, then Stereo Madness.
3. Fix 2 (double spike): the ideal-fly check first.
4. Fix 3 (ship output rule).

**Milestones**, each one reported as reached or not:
- past 10.9%;
- the first ship portal (~30%);
- the first ship section cleared;
- a complete run.

## Questions for Shannyn

1. Are you happy with the iteration 1 / iteration 2 split, and with lifting hard rule 5 for iteration 2 only?
2. Fix 1: A, B, or something else? Is A defensible enough, as "our encoding's idea of what's in the way, corrected"?
3. Fix 2: anything from the biology on timing a jump over two close obstacles, or on when an escape is released?
4. Anything in the proposed rules you'd tighten?

---

## Shannyn's answers (2026-11-14)

1. **Split and rule 5:** yes to the split, and to lifting hard rule 5 for iteration 2 only, **with Part 2 always labelled exploratory**.
2. **Fix 1: A is defensible,** framed as *correcting our collision course*: looming already means "what you'll hit if you carry on", and adding gravity makes that right. **We don't claim flies use looming for gaps:** gap crossing is slow, parallax-based and driven by the central complex (Pick & Strauss 2005; she's checking the citation). **B goes to future work.**
3. **Fix 2:** run the ideal-fly threshold check first. Treating the pair as one wider object would make the fly jump earlier (Ache et al. 2019), the wrong way. If no single threshold works, report it as a limit of a one-shot escape reflex rather than invent a mechanism.
4. **Tightened rules:**
   - (a) a **fresh held-out suite** for iteration 2, opened **once, at the end**;
   - (b) the new levels' **ranges fixed before** we study Stereo Madness further, not centred on its exact spacings;
   - (c) a **"fix counts" bar fixed in advance:** better on the new held-out levels, p < 0.05, and no worse on the old ones;
   - (d) **at most one revision per fix,** logged;
   - (e) **fresh Stereo Madness seeds,** with N fixed in advance.

**Jacob's notes on (c) and (e), to settle in D55:**
- **Power for (c):** held-out suites so far have been 20 levels with many ties. A gap fix only changes levels that *have* gaps where the fly dies, so a 20-level suite may not reach p < 0.05 even if the fix works. The fresh suite should be sized for it, e.g. 40 cube levels, all with the feature in its fixed ranges, plus the usual mix.
- **"No worse on the old ones"** needs a definition fixed in advance. Proposed: on the iteration-1 held-out cube levels, *not clearly worse* by the same paired test (no significant drop at p < 0.05), with the count of completed runs reported beside it.
- **Seeds for (e):** 0–99 are used (D54 and the 90 extra runs), so iteration 2's Stereo Madness runs use 100 onwards, e.g. 100–109 for N = 10.

## Draft D55 (to log once Shannyn agrees the wording, after D54's result and the v1.0-research tag)

**D55. Iteration 2: fixing the interface where Stereo Madness found its limits, exploratory** (2026-11-__)

Iteration 1 ends with D54's result and the `v1.0-research` tag. Iteration 2 is reported as an exploratory Part 2, after Part 1 and never mixed with it.
- **Frozen:** the connectome (hard rule 1, unchanged) and everything iteration 1 reported.
- **What may change:** the interface only (`src/stereo_flyness/interface/`), one fix at a time, each with a dated design note and Shannyn's biology argument written before it's run. At most 2–3 new dials across iteration 2, set on training levels only.
- **Stereo Madness is spent as a held-out test.** Hard rule 5 is lifted for iteration 2 only: we may look at it, and say so. No fix is ever judged on it; it shows only how far the fly then gets, on fresh seeds (100 onwards) with N fixed before each set of runs.
- **New levels:** training levels and a **fresh held-out suite** (its own seed range) with each fix's feature (gaps and drops; close pairs of obstacles) in ranges fixed **before** Stereo Madness is studied further, not centred on its spacings. The fresh held-out suite is opened **once, at the end of iteration 2.**
- **A fix counts** only if it's better on the fresh held-out levels (paired test, p < 0.05) and not clearly worse on iteration 1's held-out cube levels, as defined in its design note before it's run.
- **At most one revision per fix,** logged with its reason.
- **Extra runs** on any held-out levels or Stereo Madness are agreed by both of us before they're run.
- **Labels:** Part 2 and any video from it say "exploratory: interface adjusted after seeing this level; brain wiring unchanged."
- **Fix 1 (gaps), option A:** the collision course includes falling under gravity, so obstacles the cube would fall into loom. Framed as correcting our collision course; **no claim that flies use looming for gaps** (gap crossing is parallax-based and central-complex driven; option B is future work).
- **Fix 2 (double spike):** first a no-brain check with the ideal fly across thresholds on the new levels. If no single threshold works, it's reported as a limit of a one-shot escape reflex.
- **Fix 3 (ship):** a new output rule, argued on its own merits, only after fixes 1 and 2.

