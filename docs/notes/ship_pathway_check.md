# The ship's pathway in the logged steering tests: each eye, and VSm (Step 5)

*Jacob, 2026-11-10. For Shannyn's ship draft (`docs/notes/ship_proposals.md`): (1) does the left eye's "down" input reach DNp22, and (2) how does VSm respond? **No new runs:** the steering tests already drove each eye and both eyes (S1, S2; whole brain, original signs, recruitment runs from J5 that recorded every neuron that fired, D34). They were never judged by D29–D31, so this is descriptive. Reproduce with `uv run python scripts/ship_pathway_check.py`.*

**Correction to `ship_neuron_check.md`:** it said the pathway tests never drove the left eye. Only the *judged* runs were right-eye; S1 and S2 also ran the left eye and both eyes (5 trials each, against 10 for the right). So the "left-eye-only test before the baseline" is already done; this note is its result.

Rates are per cell, in Hz over the 1 s trial, mean ± s.d. across trials. "Down" = all T4d + T5d of the eye(s) driven; "up" = all T4c + T5c.

## 1. Each eye reaches DNp22 (S1, "down" alone)

| Input rate | Right eye: DNp22 R | Left eye: DNp22 L | Both eyes: DNp22 R / L |
|---|---|---|---|
| 25 Hz | 100.8 ± 1.5 | 81.0 ± 0.7 | 97.6 / 59.2 |
| 50 Hz | 124.1 ± 1.1 | 110.8 ± 1.3 | 103.8 / 82.8 |
| 100 Hz | 138.9 ± 3.4 | 124.4 ± 3.2 | 108.0 / 88.8 |
| 150 Hz | 145.8 ± 2.2 | 138.3 ± 1.9 | 114.4 / 92.0 |
| 200 Hz | 147.4 ± 2.7 | 139.1 ± 2.0 | 118.6 / 97.6 |

- **The left eye drives the left DNp22 nearly as well as the right eye drives the right one:** 80–95% of the rate, although the left VS cells get 59% of the synapses (`ship_neuron_check.md`). The pathway saturates, so the synapse gap shrinks in the rates.
- **One eye drives only its own side.** With one eye driven, the other side's DNp22, DNp20 and VS cells stay at 0.
- **Driving both eyes lowers DNp22 on both sides,** against either eye alone: at 150 Hz, 114 and 92 Hz with both eyes, against 146 Hz (right only) and 138 Hz (left only). The VS cells barely change (e.g. VS2 R 292 both, 292 alone; VSm L 182 both, 188 alone), and DNp20 changes little (134 against 137 on the right). So the cut is between VS and DNp22, from the other side. **Not explained here; relevant to Q3's "both eyes".** Still well above zero, so the readout still works.

## 2. VSm (S1, "down" alone)

| Input rate | VSm R (right eye) | VSm L (left eye) | VS2 R | VS3 R |
|---|---|---|---|---|
| 25 Hz | 120.4 ± 0.9 | 74.5 ± 0.0 | 183.2 | 164.6 |
| 50 Hz | 168.2 ± 0.7 | 115.8 ± 0.8 | 226.8 | 209.2 |
| 100 Hz | 215.2 ± 0.6 | 161.3 ± 0.3 | 269.1 | 252.7 |
| 150 Hz | 240.9 ± 0.4 | 188.0 ± 0.4 | 292.4 | 276.7 |
| 200 Hz | 258.8 ± 0.3 | 206.7 ± 0.2 | 307.7 | 292.9 |

- **VSm responds strongly to "down"** on both sides, a little below VS2 and VS3. With VSm's 173 and 151 synapses onto DNp22 (the largest VS input, `ship_reading.md`), it's likely a main route to DNp22, though this doesn't separate the routes.
- The left VSm is lower than the right (≈ 60–80%), in line with the left lobula plate's fewer synapses.

## 3. "Up" (S1 alone, and S2 against "down")

- **"Up" alone drives nothing** in any recorded cell, on either eye or both (all 0, except one DNp20 L spike in 5 trials).
- **"Up" cuts DNp22 hardest** (S2, "down" fixed at 50 Hz, "up" swept):

| "Up" rate | Right eye: DNp22 R | DNp20 R | VS2 R | VSm R |
|---|---|---|---|---|
| 0 | 125.3 | 104.1 | 226.9 | 168.1 |
| 25 Hz | 93.2 | 89.1 | 188.3 | 115.5 |
| 50 Hz | 45.8 | 75.6 | 147.6 | 56.3 |
| 100 Hz | 1.0 | 54.4 | 83.0 | 1.0 |
| 150 Hz | 1.0 | 32.0 | 2.0 | 1.2 |

  At "up" = 100 Hz, DNp22 and VSm are silenced while DNp20 and VS2 still fire. The left eye and both eyes show the same pattern (`results/pathway_tests/analysis/ship_pathway.csv`).

## What it means for the ship (for Shannyn)

- **Both eyes work:** the left side reaches DNp22 at nearly the right side's rate, so "both eyes, asymmetry stated" holds up. But driving both lowers DNp22 by ~20–35% against one eye. It's a property of the connectome, so it stays, and it's worth a line in the results.
- **The draft drives "down" or "up", never both at once** (one sign of the pooled motion), so S2's mixtures don't arise in the game as drafted; they show that "up" input would act on DNp22 through inhibition, as Shannyn's §3 expects.
- **DNp22 fires at ~100–150 Hz when driven,** as her §2 assumed ("one spike every ~2 ticks").
