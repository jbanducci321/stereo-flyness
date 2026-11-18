# Fix 2 (b): what raising it would involve

*Jacob, 2026-11-17. **A factual note, not a proposal.** It recommends nothing either way. D61 found D56's condition met ("(b) may be raised again only if fix 1 passes its held-out bar") and left the decision to both of us, after the Stereo Madness runs (D60). This note sets out what each choice would cost, so the decision can be made on paper. Nothing in it is run, and it reads no Stereo Madness data beyond D54.*

## What (b) is (already agreed, `fix2_design.md`)

- **A labelled variant, never the fly of record:** "a late-threshold fly, inside the range measured in real flies" (Shannyn, 2026-11-15). The fly of record stays calibrated to the mean measured threshold (39°), and is what Part 2 reports.
- **One D55 dial:** θ_full re-calibrated so the fly's mean first spike sits later, with its spread kept.
- **The mean is already chosen by the agreed rule:** with fix 1 (ii), the spread-aware ideal fly's best shifted mean is **50°**, completing 7 training levels against 0 at 37.1° (margin N = 3; `results/ideal_fly/it2_all_spread_fix1.md`, D56). 50° is inside the real-fly range (39 ± 14°).
- **Passing N earned (b) a design note only.** It still has to pass D55's held-out bar.

## What raising it would take, in order

1. **A D-entry raising it**, logging the sequence as D56 asks.
2. **A design note for (b)** (as `fix1_design.md` was for fix 1), with Shannyn's biology argument, which `fix2_design.md` already has in outline, and her dated predictions. It also has to fix three things the existing notes leave open (below).
3. **Re-calibration** (D43's method): about 10 θ_full values × 10 trials of the calibration loom, under an hour with 4 workers. Then a check that the closed-loop first spike lands where intended, as R2 did for the record (37.1 ± 7.3°).
4. **A new held-out suite** (below). Generated and frozen before any run: its seeds, counts and hashes in the config and tests, built without being opened, as the iteration-2 suites were. About 10 minutes to build.
5. **Fly runs on the training levels** (like fix 1's step 3): the variant against the record, both with fix 1 (ii), on the 50 iteration-2 training levels, seeds 0–2. About **300 runs, ~6 hours** (fewer if the record arm can be reused, see below).
6. **The held-out runs:** the new suite plus the no-harm check, both arms, seeds 0–2. At 40 + 20 levels, that's **360 runs, ~7.5 hours** (D61's 360 took 7 h 23 min).
7. **Two openings** (training, then held-out) with reports fixed and checksummed beforehand, and a D-entry for each.

**Roughly two nights of runs and four or five PRs.** None of it touches the connectome or the vendored files.

## The non-obvious costs

### The iteration-2 held-out suite is spent

D55 judges a fix on "a fresh held-out suite, opened once, at the end of iteration 2", and D61 opened it. **So (b) can't be judged without a third held-out suite.** That changes D55, which only both of us can do:
- the new suite needs its own seed range (e.g. from 3,000,000) and v4's generator unchanged;
- its frozen hashes go in `tests/data/` beside the others.

Iteration 1's 20 held-out cube levels can serve as the no-harm check again. They've been seen twice now (Part 1 and D61), which D55 already allows for a check, not a test.

### Three things the existing notes don't fix

1. **What 50° means for calibration.** The (b) rule shifted the mean of the closed-loop first spike. The record calibrates θ_full on the open-loop loom to 39° and gets 37.1° closed loop (R2 says the two match). So we need to decide whether the variant targets 50° on the calibration loom, or the θ_full that gives a 50° closed-loop mean. These may differ, and the spread may not stay at 7.3° when θ_full changes. **This has to be fixed before calibrating,** or the target becomes a choice made after seeing the result.
2. **The main measure.** For fix 1 it was "gets past the first fix-case drop". For (b) it would presumably be "gets past the first double spike", but D55 asks each fix's design note to fix it. That includes:
   - which groups count as a double spike;
   - whether triple spikes count (no threshold near the biology clears them);
   - what happens to a level with none.
3. **Whether the record arm is rerun.** D61 ran both arms fresh at one commit. Step 3's fix-1 arm (`17a0ffe`) could be reused only if the code it ran is unchanged, which a new dial would likely break. Running both arms again is the clean choice, and the estimates above assume it.

### What it can and can't show

- **The gain shown so far is the ideal fly's, not the real fly's.** On training, the ideal spread-aware fly at 37.1° completes 0 levels and at 50° completes 7. The real fly of record with fix 1 completed 0 of 50 (D57), and died next at the double spike (32 deaths). Whether moving its mean helps by as much is unknown.
- **Later isn't simply better.** Iteration 1's 50 Hz fly (first spike ~84°, outside the real range) was better on the held-out cube levels, not significantly, and worse on Stereo Madness (D49, D50, D54). 50° is much closer to the real range than 84°, but no fly run has tried it.
- **Triple spikes and 1-cell pairs stay a limit either way.** They need θ ≥ ~94° (`fix2_design.md`). (b) only targets the double spike.
- **Stereo Madness:** D60's runs are the fly of record. Showing the variant on Stereo Madness would be extra runs there, which need both of us to agree (D55), with N fixed first. It would still be context, not a test.

### Dials

Fix 1 used none of D55's 2–3 dials (`fix1_design.md`). (b) would be the first.

## If it isn't raised

- **Nothing is run.** D56's (a) and D58 stand: the double spike is reported as a finding about putting a one-shot escape reflex into a timing game, confirmed by the real fly (48% predicted, D57; it's now the top cause of death).
- **The write-up says that D61 met the condition and that we chose not to raise (b), with our reason.** The no-brain sweep that found the window (D56) is reported as it is: an ideal fly, not a fly result.
- **(b) can be named as future work** beside the long-mode take-off.

## For the decision

**What's settled either way:**
- the fly of record;
- fix 1's verdict (D61);
- the Stereo Madness runs (D60).

**What raising (b) adds:**
- one labelled variant;
- a change to D55 (a third held-out suite);
- one dial;
- about two nights of runs before the write-up.

**What not raising it leaves:** the double spike as a reported limit, with the ideal-fly window as context.
