# Step 4 proposal: controls and lesions on the cube

*Jacob, 2026-11-04. Revision 2, with Shannyn's answers of 2026-11-04 (she leads the lesion design and interpretation). For her review before it's logged as D51. No Step 4 run exists yet; nothing here has been run on a control network or a lesion. Once logged, nothing is changed, re-run or dropped after the results are seen (as D48, D49).*

**The question (PROJECT_BRIEF Step 4):** does the fly's play depend on the real wiring? It matters most because of caveat 1. LC4 and LPLC2 synapse directly onto the Giant Fiber (293 connections, 1,885 synapses: 19.9% of the Giant Fibers' input in v783), so in cube mode the fly could be little more than a one-hop relay plus a threshold.

## 1. Fixed setup
- **Whole brain** (D36), **R = 150 Hz** (D50), R × f, θ_full = 200°, collision course, D47's encoding: everything as in the Step 2 baseline of record.
  - The encoding is ours, so it doesn't change with the network. **No recalibration for any control or lesion.**
- **Levels and seeds:** the 20 held-out cube levels, seeds 0, 1, 2 (60 runs per condition). Nothing here is tuned, so reusing them is fine.
- **Reference: the intact whole brain**, same levels and seeds (agreed: like with like). It also gives a first closed-loop look at the subcircuit against the whole brain, for Step 7.
- **Original signs only** (D27's corrected copy isn't used).
- **Every ID checked against v783** (hard rule 4). Every run records its connectivity file, the file's SHA-256 and what was silenced (`play_cube.py`, already built).

## 2. What's not run, and why
- **Giant Fiber silenced: dropped.** Shiu's `silence()` zeroes outgoing synapses only, so a "silenced" Giant Fiber still spikes, and our output reads its spikes (D42). Any lesion that stops it only tests our output rule.
  - **For the write-up (Shannyn):** "In real flies, Giant Fiber–silenced flies still escape through the long-mode pathway (von Reyn et al. 2014), which our output can't see."
- **LC4/LPLC2 silenced: a code check, not a result.**
  - Our input goes only to LC4/LPLC2. Cutting their outputs means nothing in the brain receives the input at all, so "never press" is guaranteed, and it says nothing about other routes.
  - Run on 2 held-out levels at seed 0. It must give **exactly 0 Giant Fiber spikes and 0 presses**; anything else is a bug, and nothing else runs until it's fixed.
- **LC4 only / LPLC2 only: dropped (Shannyn).**
  - θ_full is calibrated on both types together, so halving the input mostly works like lowering R, which Step 3 already covers.
  - It doesn't test the von Reyn 2017 split (LC4 = speed, size from a separate population) either, because our encoding drives both types with size.

## 3. The control networks
Each is a connectivity file written into git-ignored `data/` from a fixed seed (`scripts/make_control_connectivity.py`). The original file is only read; `shiu_model.py` isn't touched. Instance *k* (k = 0, 1, 2) plays at Poisson seed *k*, so 3 instances give 60 runs.

**a. Degree-preserving shuffle** (3 instances).
- Every connection keeps its presynaptic neuron, synapse count and sign; the postsynaptic neurons are permuted across connections, with no self-connections or duplicate pairs.
- Every neuron keeps its in- and out-degree, its total output weight and its sign. Who connects to whom is randomized. Built and checked on the real connectome: 15.1M connections in ~35 s.

**b. Shuffle keeping the looming → Giant Fiber connections** (3 instances; "the most informative control", Shannyn).
- The 293 direct LC4/LPLC2 → Giant Fiber connections stay in place and **out of the shuffle pool**. They're never moved, and no shuffled connection takes their slots. Everything else is shuffled as in (a). So every neuron's degree is still preserved (Shannyn's condition).
- **Added: no new looming → Giant Fiber connections.** A shuffled connection that would land as a new LC4/LPLC2 → Giant Fiber connection is swapped away, so the direct pathway is exactly the original: no more, no less. (Only 21 of the 314 LC4/LPLC2 neurons don't already connect to a Giant Fiber, so this is rare, but it should be zero.)

**c. Relay-only network** (1 network; Shannyn's optional, cheap addition).
- Only the 293 LC4/LPLC2 → Giant Fiber connections; nothing else. The cleanest version of caveat 1.
- It shows whether the Giant Fiber reaches threshold from those connections alone, and so what the other ~80% of its input adds.
- One network, so its 60 runs are 3 Poisson seeds.

**d. Random network** (3 instances; kept: reviewers expect it).
- Same neurons and number of connections. Connections are placed uniformly at random, with no self-connections or duplicates.
- Each neuron keeps its sign (Dale's law, as in the model), and synapse counts are drawn from the real distribution.
- Our input still goes to the LC4/LPLC2 indices, and the Giant Fiber indices are still read.

## 4. Lesions (closed loop, whole brain, against the intact whole brain)
Whole cell types are silenced, on both sides, with Shiu's `silence()` (D5), exactly as in the pathway tests' E5 (`configs/pathway_tests.toml`).

- **E5b: the Giant Fiber's inhibitory partners silenced.** CB3707, SAD014, CL038, PVLP010, LHAD1g1, CB0010 and CB0563: 22 neurons, all inhibitory.
- **E5c: its excitatory partners silenced.** DNp70, PVLP122b, PVLP062 and PVLP151: 12 neurons, all excitatory.
- **Random-lesion control for each (Shannyn)**, 3 draws with fixed seeds, draw *k* at Poisson seed *k*:
  - the same number of randomly chosen neurons, each matched to one lesioned neuron;
  - **same sign** and **total output synapses within ±10%**;
  - never a Giant Fiber, an LC4/LPLC2 neuron or one of the lesion set.
  - **Why the sign is matched (added):** silencing random inhibitory neurons and silencing random excitatory ones push the brain in opposite directions, so an unmatched control would muddle the comparison. Every lesioned neuron has at least 61 candidates (median ~600–1,200), so the matching is never forced.

## 5. Predictions, written before any run
- **(a) Shuffle and (d) random network (Jacob):**
  - The Giant Fiber mostly never fires, so they play like never press (~6%).
  - The alternative is runaway activity: the Giant Fiber fires nonstop and they play like always press. Either way, **worse than intact**.
- **(b) Looming kept (Shannyn):**
  - A pure relay loses the recruited inhibition (E5b), so it jumps **earlier**: first-spike θ below intact, more (d1) deaths, progress the same or lower.
- **(c) Relay-only:** no confident prediction.
  - It loses the recruited inhibition (earlier) and the recruited excitation (later).
  - Open loop, E5c silenced the left Giant Fiber entirely. So the right one probably still reaches threshold and the left one may not.
- **E5b (Shannyn):** the Giant Fiber fires earlier: first-spike θ below intact (~37°), more (d1) deaths, lower progress.
- **E5c (Shannyn):** first-spike θ later, fewer (d1), more (d2), progress the same or **higher**.
  - **Fixed reading:** if it does better than intact, that isn't "the lesion improved the fly". It's the same late-threshold effect as Step 3 (D49), and it's written up that way.
- **Random lesions:** no clear difference from intact.
- **LC4/LPLC2 code check:** exactly 0 Giant Fiber spikes and 0 presses.

## 6. How it's judged
**Per condition against the intact whole brain:**
- per level, each setting's median run across its 3 seeds or instances;
- D48's "equal" (same killing object, or both completed);
- the two-sided sign test, with equal levels left out;
- "better" or "worse" only at p < 0.05. As in D48, each comparison is tested on its own; the report also says which results survive a Holm correction for the number of comparisons.

**"Depends on the wiring" (a, d)** = worse than intact at p < 0.05.

**"It's a relay" (b, Shannyn's stronger test).** "No clear difference" from intact is *not* evidence of sameness, so the relay reading needs all three of these:
1. progress: no clear difference from intact (sign test);
2. **first-spike θ:** the median first-spike θ without carry-over (D48 amendment) is within the intact brain's seed-to-seed range (the largest difference between any two of its 3 seeds);
3. **death-class mix:** the share of (d1) deaths is within the intact brain's seed-to-seed range. The full class mix is shown beside it.

If (1) holds but (2) or (3) doesn't, it's reported as "plays about as far, but not the same way", not as a relay.

**"It's those neurons" (E5b, E5c).** A lesion's effect is specific only if:
- the lesion differs from intact at p < 0.05, **and**
- it differs from its own random-lesion control at p < 0.05, in the same direction.

**Reported beside every condition (described only):**
- mean progress; completions by difficulty;
- D48's death classes; stuck runs (D38);
- presses per second;
- first-spike θ with and without carry-over;
- approaches with no Giant Fiber spike.

**References:** never press and random presses (Step 2), and always press (built).

**Open-loop check of every network and lesion before the runs**, recorded with the plan but read only as a description:
- the calibration loom, 10 trials;
- first-spike θ and trials fired.

**Replays:** one per condition, picked by rule: seed 0 (instance 0), the first held-out level alphabetically.

## 7. Runs and time

| | Conditions | Runs | Time |
|---|---|---|---|
| Code check | LC4/LPLC2 silenced, 2 levels | 2 | minutes |
| **Night 1** (full-length runs) | intact; E5b; E5c | 180 | ~6 h |
| **Night 2** | E5b and E5c random lesions; shuffle ×3; looming-kept shuffle ×3; relay-only; random network ×3 | 360 | ~6–8 h |

Control networks that never fire die at the first object, so they're quick. Runaway networks would be slower. If night 2 runs over, it finishes the next day; nothing is opened before the whole batch is done (D33).

## 8. Code (after this is logged)
Already built and tested:
- the degree-preserving shuffle, with kept connections;
- the always-press reference;
- `play_cube.py --control / --silence`, recording the connectome file, its SHA-256 and the lesion.

Still to build:
- the forbidden-pairs rule for (b), the relay-only network, the random network and the random-lesion matcher, with tests;
- the Step 4 batch script (blind) and report.
