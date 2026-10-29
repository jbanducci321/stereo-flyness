# Subcircuit rule (task S5): working notes

*Shannyn, 2026-10-28. Checkpoint 1: sizes of candidate rules. Not a proposal yet.*

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

## Open questions for checkpoint 2

1. **Use the pathway-test results.** Jacob's runner records every neuron that fires in the whole-brain tests. An **activity-based rule** (keep every neuron that fires in the E1–E6/S1–S3 runs, plus the core) would keep exactly the neurons that shape the outputs. Wait for round 2, then compare it with the rules above.
2. **Fidelity, not just input kept:** the real test is whether the subcircuit reproduces the whole-brain pathway results (J5). Pick 2–3 finalists and have them checked against E1, E2 and S1.
3. **Horizontal-motion inputs:** include T4a/b, T5a/b (~3,000 more neurons) or not? We don't stimulate them, so they'd be silent anyway. Probably not, but decide explicitly.
4. **Min-synapse threshold:** FlyWire analyses commonly treat connections under ~5 synapses as less reliable **[confirm a source]**.
