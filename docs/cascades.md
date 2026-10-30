# Runaway cascades in the whole-brain model

This is the follow-up D37 asks for (J5, 2026-10-30). It uses `scripts/analyse_cascades.py`, with full output in git-ignored `results/cascades/report.md`. It covers all 1,410 whole-brain pathway-test and probe trials.

## Summary

1. **There is one runaway state, not three.**
   - All 3 cascades end in the same self-sustaining pattern of **~8,300 neurons**; 8,189 are shared by all three.
   - It fires at a median of ~48 Hz and is centred on the **mushroom body**: ~2,000 KCg-m and ~1,300 KCab Kenyon cells. It also includes olfactory receptor and antennal-lobe neurons, PAM dopamine neurons and ~155 descending neurons.
2. **It doesn't stop.**
   - Each cascade trial was rerun exactly, with the same seed and input, for 2 s instead of 1 s. The first second matched the saved trial frame for frame in all 6 reruns.
   - **With the input kept on:** ~2,800–3,200 neurons fire per frame for the whole second.
   - **With all input switched off at 1 s:** ~1,975 neurons still fire per frame, flat, until the end of the run.
   - In this model, once the state starts, nothing turns it off.
3. **It doesn't touch our output neurons, at least with no input.** In the self-sustaining state (input off), the Giant Fibers, VS cells, DNp20/22 and LPi09 are all at 0 Hz. Whether it changes their response to *new* input (a loom arriving while the brain is stuck) hasn't been tested.
4. **Different neurons set it off each time.**
   - The take-off comes late, at ~617, ~630 and ~777 ms. Before it, a few hundred neurons that fire in no other trial of the condition switch on, mostly antennal-lobe local neurons (lLN1_bc, lLN2), Kenyon cells and SMP neurons.
   - The first 50 such neurons share 0–22 between cascades, so there's no single trigger neuron.
5. **The upward-motion link is weak evidence.**
   - All 3 cascades had upward-motion (T4c/T5c) input. Among all game-input trials, 37% did, so getting 3 of 3 by luck has a chance of **0.05**.
   - But all 3 were steering trials, which stimulate thousands of T4/T5 neurons. Among steering trials 62% had upward input, so 3 of 3 by luck has a chance of **0.24**.
   - The trials that come closest without cascading are also both-sides upward-motion trials (up to 8% of the state's neurons).
   - So upward motion *may* push the brain towards the state, but 3 events can't show it.

## A better cascade test than a ratio

D37's proposed test (more than 3× the condition's median active count) flags only 2 of the 3 cascades (`docs/subcircuit_candidates.md`). Because there's one specific state, a test can look for that state directly:

| Trials | Share of the 8,189 stuck-state neurons that fire |
|---|---|
| The 3 cascade trials | 97.3%, 98.1%, 98.4% |
| The other 1,407 trials | at most 8.1% (99th percentile 7.4%, median 1.7%) |

- **Possible rule:** a trial is a cascade if **≥ 50%** of the stuck-state neurons fire.
- The gap is wide, so any threshold from ~10% to ~95% gives the same answer on all current trials.
- It doesn't depend on how busy a condition normally is, and the list of neurons can be saved with the analysis.
- Whether to use it instead of a ratio is Shannyn's call (D37).

## Why it might happen (hypotheses, not tested)

- **Shiu's model has no spike-rate adaptation and no noise.** In the real mushroom body, Kenyon cells fire sparsely, because of feedback inhibition from the APL neuron, which is non-spiking and graded. The model doesn't capture that, so a recurrent excitatory loop may be able to lock in.
- **It matches the "activity spreads late" timing:** the state builds slowly, then takes off.
- If so, the state is a property of the model, not of the fly. That should be said plainly in the write-up.

## What it means for us

- **Subcircuit (D37):** this supports leaving cascade trials out of the build. The extra neurons belong to one runaway state of the model, not to the brain's response to game input.
- **Closed loop (Step 2 onward), which matters more:**
  - The state appeared 3 times in ~1,260 simulated seconds of game-like input. That's roughly 0.2% per second, so ~7% of 30 s runs, and more with heavy T4/T5 input.
  - Once it starts, it stays. A tuning grid of 200 × 30 s runs would probably contain several runs that get stuck partway.
  - It leaves our output neurons silent when there's no input, but its effect on their responses hasn't been tested.
  - The run recorder should flag it (planned in R1), and results should report it.
- **Open questions, not run yet:**
  - Does a loom or steering input during the stuck state still drive the Giant Fibers and VS cells normally?
  - Can the mini-brain (which excludes most of these neurons) enter the state at all?
  - Does the state appear in the whole brain on game-length input?
