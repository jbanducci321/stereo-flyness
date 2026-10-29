# Pathway test results (J4)

*Jacob, J4 checkpoint 4. Run 2026-10-28 on the whole brain (FlyWire v783, Shiu et al. model, frozen weights). Design: `docs/pathway_tests.md` (S4). Rules for judging: D28–D35 in `docs/decisions.md`, agreed before the full runs.*

## Summary

| Pathway | Verdict | In one line |
|---|---|---|
| **Escape:** LC4/LPLC2 → Giant Fiber (cube jump) | **GO** | Drives the right Giant Fiber in every trial at every rate, within ~8–13 ms, and stops within ~3–13 ms of input off |
| **Steering:** T4/T5 → VS → DNp20 (ship), original signs | **GO** | "Down" drives VS cells and DNp20 in every trial; "up" gives exactly 0 and, added to "down", suppresses it |
| **Steering, T4/T5-corrected signs** | **GO** | Same pattern, ~10–15% stronger |

- **Sign version carried forward (D28):** **original**. The fallback is not triggered.
- **What these verdicts mean:** the model *can* carry the signals the game needs. They are not yet evidence that the fly can *play*. That needs the interface (T4) and closed-loop runs (Step 2).

## How the run went

- **Trials:**
  - **Round 1:** 490 trials, 109 min with 4 workers.
  - **Round 2:** 150 trials (E2 at D32's lower rate, S2, and S3 at the half-of-maximum rate), 36 min.
- **Setup:**
  - All 640 trials came from clean commits on `jb-pathway-tests` (`aac1f33` for round 1, `f74e94d` for round 2; runner code identical).
  - Each trial is saved per 4.2 ms frame, with every active neuron recorded (D34).
  - The pilot is excluded (D33).
- **No-input baselines:** 30 trials (E4 none, S0 × 2 sign versions) gave **0 spikes anywhere in the brain** (D30).
- **Reproduce:** `scripts/run_pathway_tests.py`, then `scripts/analyse_pathway_tests.py`. The full report (all tables) is written to git-ignored `results/pathway_tests/analysis/report.md`.

Rates below are mean Hz per neuron ± SD across 10 trials, unless stated.

## Escape: LC4 / LPLC2 → Giant Fiber

### E1 dose–response (right input; the right Giant Fiber fired in 10/10 trials in every condition)

| Input rate | LC4 only: GF right / left | LPLC2 only: GF right / left | **LC4 + LPLC2: GF right / left** |
|---|---|---|---|
| 25 Hz | 12.9 / 0.1 | 68.4 / 43.0 | **76.9 ± 3.1 / 43.8 ± 2.7** |
| 50 Hz | 54.9 / 21.4 | 102.7 / 68.8 | **126.0 ± 2.3 / 74.5 ± 3.2** |
| 100 Hz | 94.7 / 32.6 | 133.7 / 89.8 | **164.1 ± 1.4 / 92.5 ± 1.6** |
| 150 Hz | 120.0 / 29.6 | 159.9 / 98.7 | **187.2 ± 2.4 / 98.6 ± 2.3** |
| 200 Hz | 141.5 / 29.5 | 178.2 / 104.4 | **205.3 ± 1.8 / 101.7 ± 2.7** |

**D29 rules** (judged on LC4 + LPLC2):

| Rule | Result |
|---|---|
| 0. Fires reliably at one or more rates | **PASS:** 10/10 trials at every rate |
| 1. Rises with input (200 vs 25 Hz, > 2 pooled SDs) | **PASS:** +128.4 Hz against a bar of 5.1 Hz |
| 2. Right beats left by > 2 pooled SDs at every reliable rate | **PASS** at all five rates (right − left = 33–104 Hz against bars of 3–6 Hz). Right/left ratio 1.7–2.0× |
| 3. E2 onset < 100 ms and 4 × SD < 238 ms, at every E2 rate | **PASS** at 25 Hz (12.6 ± 1.1 ms) and 150 Hz (8.4 ± 0.0 ms) |

**Not additive:** LC4 + LPLC2 together drive *less* than the sum of each alone (e.g. at 150 Hz, 187 Hz vs 120 + 160). The S4 plan asked about this.

### E2 latency and offset (LC4 + LPLC2, 300 ms on / 300 ms off × 3; 30 cycles per rate)

| Input rate | Onset latency | Offset after input stops | Spikes per 300 ms "on" |
|---|---|---|---|
| 25 Hz (D32's lower rate) | 12.6 ± 1.1 ms | 3.4 ± 3.9 ms (max 12.6) | 22.7 ± 1.9 |
| 150 Hz | 8.4 ± 0.0 ms | 12.9 ± 8.4 ms (max 29.4) | 55.8 ± 0.9 |

- **Resolution:** latencies are measured to the end of the 4.2 ms frame holding the first spike. They are upper bounds quantised to 4.2 ms. "± 0.0" means every first spike fell in the same frame (true latency 4.2–8.4 ms), not that latency is exactly constant.
- **For the game:**
  - Onset is far inside the ~238 ms window to clear a spike.
  - Firing stops within ~1 game frame (17 ms) at 25 Hz, but can run up to ~30 ms at 150 Hz.
  - The output rule (T4) needs to handle this so that holding doesn't re-jump on landing.

### E3 recruitment (random subsets of right LC4, 150 Hz)

| LC4 neurons driven | Right GF | Trials with a GF spike | First spike (median) |
|---|---|---|---|
| 10% (5) | 3.0 ± 4.4 | 5/10 | 58.8 ms |
| 25% (12) | 29.6 ± 4.7 | 10/10 | 23.1 ms |
| 50% (25) | 74.9 ± 8.3 | 10/10 | 12.6 ms |
| 100% (50) | 121.2 ± 3.7 | 10/10 | 8.4 ms |

- **There's a threshold between ~5 and ~12 LC4 neurons.** Which neurons are picked matters near threshold: at 10%, the five subsets gave 0–11 Hz.
- More neurons give both a higher rate and an earlier first spike, so a growing looming image could map to a growing number of driven neurons (input encoding, T4).

### E4 specificity controls (D30)

| Control (150 Hz) | Right GF | Left GF | Trials with a GF spike |
|---|---|---|---|
| None (0 Hz) | 0 | 0 | 0/10 |
| Right LC10a (119 neurons) | 0 | 0 | 0/10 |
| Right sugar GRNs (21) | 0 | 0 | 0/10 |

All quiet (0% of the looming response). The two-step routes from LC10a noted in S4 don't fire the Giant Fiber at this input.

### E5 lesions (LC4 + LPLC2 at 150 Hz)

| Condition | Right GF | Left GF |
|---|---|---|
| Nothing silenced (E1) | 187.2 ± 2.4 | 98.6 ± 2.3 |
| E5b: inhibitory partners silenced (CB3707, SAD014, CL038, PVLP010, LHAD1g1, CB0010, CB0563) | 212.0 ± 2.1 | 103.5 ± 2.5 |
| E5c: excitatory partners silenced (DNp70, PVLP122b, PVLP062, PVLP151) | 168.3 ± 2.9 | **0.0** |

- **Feed-forward inhibition is recruited:** silencing the inhibitory partners raises the right Giant Fiber by ~13%.
- **The left Giant Fiber is driven entirely through the excitatory partners.** Silencing them removes it completely.

### E6 / D34: what the looming input recruits

- With LC4 + LPLC2 at 150 Hz, **997 neurons fire**: 152 stimulated (our input) and **845 of the fly's own**. The full list per condition is in the trial files, for S5.
- **Right Giant Fiber:**
  - 65 of its 483 input neurons fire (stimulated ones not counted).
  - Biggest active drivers: DNp70 (+, 322 synapses), PVLP010 (−), LHAD1g1 (−), PVLP122b (+).
  - Excitatory and inhibitory drive are roughly balanced (rate × synapses: 77k vs 71k).
- **Left Giant Fiber:**
  - 55 inputs fire, mostly excitatory.
  - Mainly the left DNp70 (232 synapses) and two **right-side PVLP151** neurons (51 + 35 synapses), which cross the midline.
  - This, with E5c, explains how the left side is reached.

## Steering: T4/T5 → VS cells → DNp20 / DNp22

### S1 direction selectivity (right input; original signs, corrected in brackets)

| Input rate | "Down" (T4d+T5d): VS right | "Down": DNp20 right | "Up" (T4c+T5c): VS right / DNp20 | "Up": LPi09 right |
|---|---|---|---|---|
| 25 Hz | 113.1 (128.4) | 73.3 (88.5) | 0 / 0 | 66.2 |
| 50 Hz | 154.1 (170.1) | 103.7 (112.2) | 0 / 0 | 102.9 |
| 100 Hz | 197.8 (213.9) | 126.0 (134.0) | 0 / 0 | 144.8 |
| 150 Hz | 223.3 (239.2) | 137.0 (139.4) | 0 / 0 | 170.8 |
| 200 Hz | 241.0 (256.5) | 139.6 (143.9) | 0 / 0 | 189.3 |

- Left VS cells stay at 0 throughout.
- "Down" also drives DNp22 (101–150 Hz).

### S3 horizontal-motion control, and D31 rule 3

| Sign version | Rate (D32) | "Down": VS right | Horizontal: VS right | Horizontal: DNp20 right ("down") |
|---|---|---|---|---|
| Original | 50 Hz | 154.1 ± 0.5 | 65.2 ± 1.0 | 64.3 (103.7) |
| Corrected | 25 Hz | 128.4 ± 0.4 | 15.0 ± 0.7 | 22.1 (88.5) |
| *Original, 150 Hz (reported only)* | | *223.3* | *157.3* | |

### S2 opponent inhibition (reported, not part of the go/no-go)

| "Up" rate added | Original ("down" fixed at 50 Hz): VS / DNp20 | Corrected ("down" fixed at 25 Hz): VS / DNp20 |
|---|---|---|
| 0 Hz | 154.3 / 104.1 | 128.6 / 88.8 |
| 25 Hz | 128.6 / 89.1 | 82.6 / 61.7 |
| 50 Hz | 105.2 / 75.6 | 36.0 / 34.5 |
| 100 Hz | 68.3 / 54.4 | 4.4 / 0.4 |
| 200 Hz | 18.0 / 18.3 | 0.5 / 0.0 |

Adding upward motion suppresses VS and DNp20 strongly, while LPi09 rises (63 → 188 Hz). This matches the known opponent organisation (LPi neurons).

**D31 rules** (both sign versions):

| Rule | Original | Corrected |
|---|---|---|
| 1. "Down" fires right VS and DNp20 reliably | **PASS** (10/10 at every rate) | **PASS** |
| 2. "Up" gives VS and DNp20 < 10% of "down" | **PASS** (0%) | **PASS** (0%) |
| 3. Horizontal < "down" by > 2 pooled SDs, at the half-of-maximum rate | **PASS** (89.0 vs bar 1.5) | **PASS** (113.4 vs bar 1.2) |

## Caveats

- **Frame resolution:** latencies are quantised to 4.2 ms (see E2).
- **Rule 2's steering selectivity is close to automatic:** "up" reaches VS cells only through inhibitory LPi neurons, so 0 was expected (D31 calls it a sanity check). S2 is the more informative result.
- **Firing rates are high:** the Giant Fiber reaches ~200 Hz and VS cells ~250 Hz. A real Giant Fiber fires a few spikes per escape, and VS cells signal mostly with graded potentials. These are model rates under strong direct drive, not predictions of real ones.
- **The input encoding is ours:** we drive LC4/LPLC2 and T4/T5 directly, so looming detection and direction selectivity are built into our input, not computed by the fly (S4 caveat).
- **No gap junctions** in the model (Giant Fiber–TTM, VS–VS, VS–DNOVS). The jump itself (TTM) is outside the brain data.
- **One D32 pick was marginal:** the corrected half-of-maximum rate (25 Hz) qualified at 50.07% of maximum.

## What this means for the next steps

- **Output rule (T4), escape:**
  - The Giant Fiber fires continuously while driven and for up to ~30 ms after.
  - A "jump on the first spike, then a refractory window" rule fits this better than "jump while firing".
- **Input encoding (T4), escape:**
  - E3 suggests encoding looming size as the number of LC4 (and LPLC2) neurons driven, with the threshold at ~10–25% of LC4.
  - Even 25 Hz is enough for fast, reliable responses.
- **Ship (T4, Step 5):**
  - **Horizontal motion also drives VS cells and DNp20** (64 of 104 Hz at 50 Hz, original).
  - The level scrolls sideways, so encoding forward motion through T4a/b–T5a/b would push the ship controller. The ship encoding should avoid driving horizontal-motion neurons, or account for them.
- **Subcircuit (S5):** the 845 recruited neurons (escape) and the steering equivalents, plus E5's partner effects, are in the trial files.
