# Subcircuit rule (task S5): working notes

*Shannyn, 2026-10-28. Checkpoint 1: sizes of candidate rules. Checkpoint 2: three candidate specs for J5 validation. Not a decided rule yet.*

**The question:** which neurons go into the subcircuit that replaces the whole brain for tuning runs (J5)? The size budget is D18: up to ~20k neurons / ~3M connections. Cutting the brain removes the input that boundary neurons got from outside, which changes their dynamics, so the rule is effectively a hidden dial (PROJECT_BRIEF §3.3) and must be decided and logged.

## Checkpoint 1: candidate rules by size and input kept

Numbers from `scripts/subcircuit_sizes.py` (FlyWire v783, flywire_annotations v3.1.0). Both pathways together. Every rule includes the core: LC4, LPLC2, T4c/d, T5c/d, VS1–VS8, LPi09, DNp01, DNp20, DNp22.

- **paths≤k:** every neuron on an input → output path of at most k synapse hops.
- **core+partners:** every direct input and output partner of the output neurons.
- **min_syn:** only connections with at least this many synapses count when growing the rule.
- **"Input kept":** share of that neuron's input synapses whose presynaptic neuron is inside the subcircuit.

| Rule | min_syn | Neurons | Connections | Fits D18 | GF input kept | DNp20 input kept | VS input kept | GF inhibitory partners kept |
|---|---|---|---|---|---|---|---|---|
| paths≤2 | 1 | 6,966 | 119k | yes | 69% | 16% | 65% | 13/22 |
| paths≤3 | 1 | 27,245 | 2.14M | **no** (neurons) | 99% | 96% | 97% | 22/22 |
| core+partners | 1 | 7,812 | 165k | yes | 100% | 100% | 67% | 22/22 |
| paths≤2 | 5 | 6,798 | 105k | yes | 41% | 16% | 65% | 5/22 |
| paths≤3 | 5 | 7,828 | 234k | yes | 85% | 42% | 69% | 19/22 |
| core+partners | 5 | 7,188 | 119k | yes | 94% | 96% | 66% | 22/22 |
| paths≤2 | 10 | 6,762 | 98k | yes | 32% | 10% | 65% | 4/22 |
| paths≤3 | 10 | 7,010 | 135k | yes | 70% | 28% | 65% | 12/22 |
| core+partners | 10 | 7,030 | 110k | yes | 86% | 91% | 66% | 22/22 |

(22 = the neurons of the seven inhibitory partner types listed in `docs/pathway_tests.md` E5b.)

## What this shows

- **Size isn't the constraint.** Almost every rule is far below the D18 budget: ~7k neurons, mostly the ~6,000 T4c/d and T5c/d input neurons themselves. Only paths≤3 with no synapse minimum is too big. So the rule can be chosen on biology and fidelity, not compute.
- **Pure path rules lose the Giant Fiber's inhibition.** paths≤2 keeps only 4–13 of the 22 inhibitory partner neurons, and only 10–16% of DNp20's input. That's because paths≤k keeps only neurons that are *fed by* our inputs, so other inputs onto the outputs are cut.
- **core+partners keeps nearly all direct input** to the GF and DNp20, but each partner's own inputs are cut, so partners that are driven from elsewhere in the brain will be quieter than in the whole brain.
- **VS cells keep only ~66% of their input** under every rule except paths≤3/min 1. The missing part is mostly the horizontal-motion T4a/b and T5a/b (~25%), which we don't stimulate.

## Checkpoint 2: candidate specs for J5

Written in Jacob's spec format (`scripts/extract_subcircuit.py`, branch `jb-subcircuit`) in `configs/subcircuits/`. Each includes every pathway-test input and watched neuron (`pathway_tests = true`), so the validator can rerun every test, plus the core cell types on both sides.

| Spec | Adds | Neurons | Connections | Notes |
|---|---|---|---|---|
| **A** `sc_partners5` | Every direct input/output partner (≥ 5 synapses) of DNp01, DNp20, DNp22 | **10,316** | 174k | Extracted on the whole brain, 2026-10-28. Fits D18 easily |
| **B** `sc_active` | Every neuron that fired in E1–E3 and S1–S3 (original signs, D34 record) | Jacob to extract | | Needs the trial files on Jacob's machine |
| **C** `sc_partners5_active` | A + B | Jacob to extract | | Expected ~11k |

**Input kept by A** (share of whole-brain input synapses):
- Giant Fibers: 93–95%. DNp20: 95–96%. DNp22: 95%. Excitatory and inhibitory kept about equally.
- VS cells: right 80–97%, **left only 38–95%** (VS1, VS5–VS8 left: 38–54%).

**Why the left/right gap:** `pathway_tests = true` includes the S3 inputs, the horizontal-motion T4a/b and T5a/b, but only on the right (the tests stimulate the right side). So right VS cells keep their horizontal input and left ones don't. See question 3 below.

**Why these three, given the pathway results** (`docs/pathway_results.md`):
- **A** keeps the Giant Fiber's recruited partners whatever drives them: DNp70 and PVLP151 (the whole left-GF response, E5c) and the inhibitory partners (E5b: +13% when silenced). The pathway results show both matter.
- **B** keeps exactly what the tests recruit: 845 of the fly's own neurons for escape (E6), plus the steering equivalents. It's the most targeted, but see question 2.
- **C** is the safe union, if A and B each miss something.

## Open questions

1. **Validation tolerances (with Jacob):** how close must a subcircuit be to the whole brain to pass? For example: the D29/D31 verdicts unchanged, key-group rates within ~10%, E2 onset within one frame. Decide **before** looking at the validation results.
2. **B is right-side biased.** All tests stimulated the right side, so neurons only recruited by left-side input are missing. The game will likely drive both sides, so B probably needs a mirrored run, or it can only be a check on A. A and C don't have this problem for direct partners.
3. **Horizontal-motion inputs (T4a/b, T5a/b):** include them on **both** sides, or leave them out and run S3 only on the whole brain. The pathway results show horizontal motion drives VS/DNp20 substantially (64 vs 104 Hz), and a scrolling level is horizontal motion, so this links to the ship encoding decision (T4).
4. **Min-synapse threshold:** FlyWire analyses commonly treat connections under ~5 synapses as less reliable **[confirm a source]**. A 5 → 10 comparison would show how sensitive the result is.
5. **`min_rate_hz = 0`** in B keeps any neuron with even one spike across all trials. A small threshold (e.g. 1 Hz) is worth comparing.
