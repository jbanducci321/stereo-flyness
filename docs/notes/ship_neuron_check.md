# Ship neurons: v783 check (Step 5)

*Jacob, 2026-11-10. Hard rule 4 for the neurons in Shannyn's ship draft (`docs/notes/ship_proposals.md`): the input (T4d/T5d "down" and T4c/T5c "up", both eyes) and the readout (DNp22, with DNp20 for comparison). A check, not a decision. Reproduce with `uv run python scripts/check_ship_neurons.py` (reads only).*

## Summary

- **Every ID checks out.** For each type and side, the IDs in `configs/target_neurons_783.csv` are exactly the annotation table's (flywire_annotations v3.1.0), and every one is in the model (`data/Completeness_783.csv`, all marked completed). No duplicates. Nothing needs adding to the config: it already has both eyes.
- **The left eye is wired like the right, but with fewer synapses.** Each eye's "down" cells reach only that side's VS cells, and VS → DNp22 is the same on both sides (240 and 242 synapses). But the left VS cells get **59%** of the right's "down" input (19,459 against 33,139 synapses), and 55% of the right's input from everything.
- **"Up" cells barely touch VS cells** on either side (64 and 7 synapses), as in the pathway tests: their effect goes through LPi09 and other inhibitory cells.

## The IDs

| Type | Left | Right | Same set as annotations | In v783 |
|---|---|---|---|---|
| T4d | 796 | 777 | yes | all |
| T5d | 740 | 727 | yes | all |
| T4c | 864 | 842 | yes | all |
| T5c | 775 | 766 | yes | all |
| DNp22 | 1 | 1 | yes | all |
| DNp20 | 1 | 1 | yes | all |

Driving all four types on both eyes is **6,287 neurons** (cube: 210 LC4/LPLC2 at most).

## The wiring, per side

Synapses onto each VS type from the same side's eye ("down" = T4d + T5d, "up" = T4c + T5c), from all inputs, and from each VS type onto DNp22 on the same side. No cross-side connections exist at either step.

| VS type | down L | down R | up L | up R | all in L | all in R | → DNp22 L | → DNp22 R |
|---|---|---|---|---|---|---|---|---|
| VS1 | 2,025 | 2,670 | 10 | 0 | 5,411 | 8,675 | – | – |
| VS2 | 4,618 | 6,518 | 6 | 1 | 6,039 | 9,105 | 16 | 15 |
| VS3 | 3,249 | 6,069 | 5 | 0 | 4,050 | 7,576 | 26 | 20 |
| VS4 | 1,839 | 2,235 | 7 | 0 | 2,517 | 3,722 | – | – |
| VS5 | 773 | 1,760 | 2 | 0 | 1,679 | 3,573 | – | – |
| VS6 | 672 | 1,097 | 5 | 0 | 2,059 | 3,338 | – | – |
| VS7 | 665 | 1,054 | 1 | 0 | 1,775 | 3,056 | – | – |
| VS8 | 1,045 | 1,486 | 0 | 0 | 2,321 | 4,186 | – | – |
| VSm | 2,490 | 5,164 | 17 | 4 | 5,030 | 10,819 | 173 | 151 |
| VST1 | 442 | 1,704 | 3 | 1 | 773 | 2,689 | 9 | 42 |
| VST2 | 1,641 | 3,382 | 8 | 1 | 3,623 | 7,036 | 16 | 14 |
| **Total** | **19,459** | **33,139** | **64** | **7** | **35,277** | **63,775** | **240** | **242** |

The VS → DNp22 column matches `ship_reading.md`'s table.

## The left–right difference

- **It's the whole left lobula plate, not the VS cells alone.** The cell counts are about equal on both sides (e.g. 796 against 777 T4d), but the left T4/T5 cells have far fewer output synapses: 135,800 against 218,706 for T4d + T5d (62%), and 193,929 against 293,577 for T4c + T5c (66%). Other lobula plate cells show the same: synapses onto LPi09, LPi11 and Tlp1 on the left are 44–67% of the right's.
- **The lobula doesn't:** LC4 and LPLC2 outputs are about equal on both sides (18,242 against 15,402, and 41,663 against 43,097). So the cube's input isn't affected.
- **Most likely a reconstruction difference, not biology**: the two eyes of a fly are symmetric, and the gap follows one brain region, not one cell type. Not checked against FlyWire's papers; worth a line in the model limits either way.
- **It stays as it is.** Weights are never changed (hard rule 1).

## What it means for the ship (for discussion)

- With both eyes driven equally (the draft's Q3), the same image motion drives the left VS cells less than the right ones. With "either DNp22 spikes = release" (Q2), the right side would likely set most releases.
- The options I see, for Shannyn:
  - **Both eyes, as drafted, with the asymmetry stated.** The connectome as it is, and the right side doing most of the work is a result in itself.
  - **The right eye only, as in the pathway tests.** Tested, but it throws away half the input.
- **Corrected 2026-11-10:** the pathway tests *did* drive the left eye and both eyes (S1, S2: logged recruitment runs, not judged), so no new run was needed. The left side reaches DNp22 at 80–95% of the right side's rate: `docs/notes/ship_pathway_check.md`.
