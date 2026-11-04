# Step 4 proposal: controls and lesions on the cube

*Jacob, 2026-11-04. Draft for discussion: no code, no runs. Shannyn leads the lesion design and interpretation (PROJECT_BRIEF §8); the lesion parts here are questions and engineering facts, not choices. Once agreed, it's logged as a decision before any Step 4 run, like D48 and D49.*

**The question (PROJECT_BRIEF Step 4):** does the fly's play depend on the real wiring? This matters most because of caveat 1: LC4 and LPLC2 synapse directly onto the Giant Fiber, so in cube mode the fly could be little more than a one-hop relay plus a threshold.

## 1. Two engineering facts that change the plan

**a. The "Giant Fiber silenced" lesion would change nothing as planned.**
- Shiu's `silence()`, the lesion method D5 allows, zeroes a neuron's **outgoing** synapses only. The silenced neuron still spikes when driven (`stepper.py`, `silence`).
- Our output rule reads the Giant Fiber's **own spikes** (D42). Silenced this way, it keeps spiking, and the fly presses exactly as before.
- Making it not spike would need its incoming synapses zeroed, a different kind of lesion from D5's. Even then the result is known in advance: no Giant Fiber spikes means no presses, so it plays like "never press". Our output *is* the Giant Fiber, so in this game a Giant Fiber lesion only tests our own output rule.
- In the real fly, Giant Fiber–silenced flies still escape through the long-mode pathway (von Reyn 2014; `docs/notes/giant_fiber_escape.md`). Our output doesn't read that pathway, so we can't reproduce that.
- **Proposal:** drop it, or keep it only as a pipeline check with its outcome stated in advance. **Question for Shannyn.**

**b. "LC4/LPLC2 silenced" is circular (as `docs/pathway_tests.md` already says for E5).**
- Our input drives LC4/LPLC2 directly. Silenced, they still spike, but nothing reaches the Giant Fiber, so the fly never presses.
- That outcome is known in advance, so at most it's a pipeline check (it also confirms nothing else in the brain carries the looming input to the Giant Fiber).
- **Proposal:** keep it as a cheap check with its prediction written down, not as a result. **Question for Shannyn.**

**So the informative tests are the wiring controls.** Below I also suggest one lesion that targets caveat 1 directly (§3c), and the E5 partner lesions as candidates (§4).

## 2. Where it runs
- **On the whole brain**, as D36 fixed. D36 also says a shuffled control on the subcircuit would need the whole D36 pipeline (pathway tests, recruitment, build, validation: days). Running on the whole brain avoids that entirely, and the controls aren't tuned, so the subcircuit's speed isn't needed.
- **Intact reference: the whole brain at the same R, on the same levels and seeds** (60 runs). Rule 5 showed the subcircuit presses on the same frame as the whole brain, so the Step 2 subcircuit runs would very likely give the same result. But comparing like with like (whole brain against whole brain) leaves nothing to argue about, at ~1–1.5 h. It's also a first data point for Step 7.
- **R:** whatever we agree goes forward (my proposal: 150 Hz, `docs/decisions.md`, "Open"). If we agree 50 Hz as a variant, the controls run at the R of record only.
- **Encoding fixed:** θ_full = 200° and everything in D41/D45/D47 stay as they are. **No recalibration for a control network.** Recalibrating would tune the control to behave like the fly, which defeats it.

## 3. The controls (my side: networks and runs)
Each control network is a new connectivity file written into git-ignored `data/`, like D27's sign-corrected copy (`scripts/make_corrected_connectivity.py`). The original file is only read; `shiu_model.py` isn't touched; `BrainStepper` already takes the connectivity path. Each file is built from a fixed seed, so it can be rebuilt anywhere, and its checksum is recorded with the runs.

**a. Degree-preserving shuffle (main control).**
- **How:** keep every connection's presynaptic neuron, synapse count and sign, and randomly permute the postsynaptic neurons across all connections. Then fix self-connections and duplicate pairs with a few swap passes.
- **What it keeps:** each neuron's number of inputs and outputs, its total output weight, and its sign (signs belong to the presynaptic neuron's transmitter).
- **What it destroys:** *who* connects to whom, including LC4/LPLC2 → Giant Fiber.
- **Instances:** 3 shuffles, each played at one Poisson seed (shuffle *k* at seed *k*, k = 0, 1, 2). That gives 60 runs, matching the baseline's 3 seeds, so between-shuffle spread is part of the result.

**b. Random network of the same size (as planned).**
- Same neurons, the same number of connections and the same mix of synapse counts and signs. Connections are placed uniformly at random, so degrees aren't kept either.
- Our input still goes to the LC4/LPLC2 indices, and the Giant Fiber indices are still read.
- 3 instances, as in (a). It's weaker than (a), so it adds little scientifically, but it's in the plan and costs one more night-slot. **Keep or drop?**

**c. Suggested addition: shuffle everything except the looming → Giant Fiber connections.**
- Same as (a), but the direct LC4/LPLC2 → Giant Fiber connections stay in place. That's ~20% of the Giant Fiber's input; its other ~80% and the rest of the brain are shuffled.
- **This is the test of caveat 1.**
  - If the fly plays as well as intact, its play is essentially the one-hop relay plus a threshold, and we say so.
  - If it plays worse (or better), the rest of the wiring shapes the jump, for example through the feed-forward inhibition E5b found.
- I think this is the most informative control we can run. It's your area, though, as it's really a lesion-style question. **Question for Shannyn.**

**What I expect, written down before anything runs** (to be fixed in the decision):
- (a) and (b) mostly never fire the Giant Fiber, so they play like "never press" (~6%).
- The other possibility is runaway activity: a shuffled brain may cascade (the stuck state, D38), and the Giant Fiber would then fire nonstop. A fly that presses all the time jumps every time it lands, which could get further than never pressing. So we need a reference for it (§5).
- (c): no confident prediction. That's why it's worth running.

## 4. Lesions (Shannyn's lead: options only)
Candidates that use D5's method and aren't circular, all from the pathway tests (`docs/pathway_results.md`, E5):
- **E5b in closed loop: the Giant Fiber's inhibitory partners silenced** (CB3707, SAD014, CL038, PVLP010, LHAD1g1, CB0010, CB0563). Open loop, this raised the right Giant Fiber's rate by ~13%. In the game it should move the jump earlier, so we'd predict more (d1) deaths: a direct, sign-specific test of whether recruited inhibition shapes the jump timing.
- **E5c in closed loop: the excitatory partners silenced** (DNp70, PVLP122b, PVLP062, PVLP151). Open loop, the left Giant Fiber went silent and the right fell ~10%. Our rule presses on either Giant Fiber, so the prediction is little change, with slightly later jumps.
- **LC4 only / LPLC2 only** (E5a, dropped before because it was uninformative open loop): with half the input, the threshold θ should move later. It might be more telling in closed loop, but θ_full was calibrated on both types together.
- Every ID gets checked against v783 (hard rule 4), as in the pathway tests.

## 5. How it's judged (to fix before the runs)
- **Levels:** the 20 held-out cube levels (unseen by the controls; the Step 2 and 3 results on them are already known, which is fine because nothing here is tuned). Seeds 0, 1, 2.
- **Score:** mean progress, levels completed by difficulty, D48's death classes, stuck runs (D38), and presses per second (to show "never fires" or "always fires").
- **Comparison:** each control against the intact whole brain, per level, using each setting's median run across the three seeds or instances. D48's "equal", then the two-sided sign test (p < 0.05), as in Step 3. **"Depends on the wiring" = the control is worse at p < 0.05.**
- **References:** never press and random presses (from Step 2), plus **a new one: always press** (no brain, holds every tick), so that a runaway control network can be read correctly.
- **Open-loop check per control network:** the calibration loom (10 trials), giving the first-spike θ and trials fired. It's described only and explains the closed-loop result without changing anything.
- **Replays:** one per control, picked by rule (seed 0, the first held-out level), so the viewer can show what a shuffled brain does.

## 6. Cost and timeline

| Task | Who | Time |
|---|---|---|
| Agree this plan (incl. §1, §3c, §4) and log it | Both | her review + ~30 min |
| Code: shuffle and random-network builders with tests, the always-press reference, a Step 4 runner and report (reusing Step 2's analysis) | Jacob | ~half a day |
| Open-loop check of each control network | runs | ~30 min |
| Runs: intact whole brain + 3 shuffles + 3 random + (c) × 3 + any lesions, 60 runs each | runs | one night (whole brain is ~3× slower than the subcircuit, but control networks that never fire die at the first object, so they're quick) |
| Report and write-up, opened together | Both | ~2 h |

## 7. Questions to settle
1. **Giant Fiber silenced:** drop, or keep as a pipeline check with a stated outcome? (§1a)
2. **LC4/LPLC2 silenced:** keep as a pipeline check? (§1b)
3. **Add the "everything but looming → Giant Fiber" shuffle?** (§3c)
4. **Random network: keep or drop?** (§3b)
5. **Which lesions in closed loop?** (§4)
6. **Intact whole-brain reference:** agree to run it rather than reuse the subcircuit runs? (§2)
7. **R for Step 4:** follows the "which R goes forward" decision.
