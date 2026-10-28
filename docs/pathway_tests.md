# Pathway tests (S4)

*Shannyn, task S4. Last updated 2026-10-27. Status: draft for Jacob's review.*

This is the design for the Step 0 pathway tests: what to stimulate, at what rates, what to measure, and what counts as "it works". Jacob implements and runs them (J4). The results feed the go/no-go in `docs/FEASIBILITY.md` (T3) and the interface decisions (T4).

## General setup

- **Network:** the whole brain (FlyWire v783, all 138,639 neurons). The subcircuit doesn't exist yet (S5), and the whole-brain results are the reference it must later reproduce.
- **Runner:** `BrainStepper.run_frames()` (D17) with **240 Hz frames (4.17 ms)**, the physics tick (D23). 4.17 ms bins are fine enough for latencies, given the 238 ms jump window.
- **Model:** Shiu's default parameters, unchanged. Input is Poisson stimulation of the named cell types (D16). All IDs come from `configs/target_neurons_783.csv` (S2).
- **Trials:** 10 per condition, with different seeds, unless stated. Report mean ± SD.
- **Rates:** a sweep of **0, 25, 50, 100, 150, 200 Hz**. 150 Hz is Shiu's default and 100 Hz reproduced sugar → MN9. These are model input rates, not claimed LC4 firing rates; real looming responses (S3 reading) set which part of the range is plausible.
- **Side:** stimulate one side (right) and record both sides. LC4 and LPLC2 synapse only onto the Giant Fiber on their own side (805 and 1,080 synapses, none crossing), so the other side is a built-in control.
- **Logging:** save per-frame spike counts for every watched neuron, plus the run config, seed, git commit and sign version (`original` or `corrected`, steering only), in `results/pathway_tests/` (git-ignored).

### What J4 needs that the runner doesn't have yet
- **Silencing (E5).** `BrainStepper` has no silencing option. Shiu's own `silence()` in `shiu_model.py` sets a neuron's outgoing weights to zero, which is the lesion method D5 allows. The stepper needs to call it before building.
- **Watching many neurons (E6).** Recording the Giant Fiber's top input partners means a watch group of ~40 neurons. That should already work with `watch=`.
- **The corrected connectivity file (steering).** A small script that writes the T4/T5-corrected copy into `data/` (see "Two sign versions").

## Escape: LC4 / LPLC2 → Giant Fiber (DNp01)

**Watch:** both Giant Fibers (`DNp01`), and for E6 the top input partners listed there.

### E1. Dose–response
- **Stimulate:** right LC4 alone (50 neurons), right LPLC2 alone (102), then both, at each rate in the sweep, for 1 s.
- **Measure:** Giant Fiber firing rate, each side.
- **It works if:** the right Giant Fiber's rate rises with input rate, and the left Giant Fiber stays near zero.
- **Why it matters:** this is the basic "does the pathway carry the signal" check, and the curve sets the range for the input-strength dial.
- **Also note:** whether LC4 and LPLC2 together drive more than the sum of each alone. Real looming responses depend on both.

### E2. Latency and offset
- **Stimulate:** both right LC4 and LPLC2, on for 300 ms, off for 300 ms, repeated 3 times per trial. Use the lowest rate that drives the Giant Fiber reliably in E1, and 150 Hz.
- **Measure:**
  - **onset latency:** time from input on to the first Giant Fiber spike;
  - **offset:** time from input off to the last Giant Fiber spike;
  - spikes per "on" period.
- **It works if:** onset latency is well inside the 238 ms window to clear a spike (`docs/game_physics.md` §3), ideally under ~50 ms, and firing stops within about one 60 fps frame (~17 ms) of input off.
- **Why it matters:**
  - The ~35–50 ms we have so far came from sugar → MN9, which goes through several steps. LC4 → Giant Fiber is one step, so the real number may be shorter. The game needs the real one.
  - **Holding re-jumps the moment the cube lands** (`docs/game_physics.md` §3). A Giant Fiber that keeps firing after the looming input ends means unwanted repeated jumps. Offset matters as much as onset for the output rule (T4).

### E3. Recruitment
- **Stimulate:** a random 10%, 25%, 50% and 100% of right LC4 neurons, at 150 Hz, for 1 s. Draw 5 different random subsets per fraction.
- **Measure:** Giant Fiber rate and onset latency.
- **It works if:** there's a clear threshold, a fraction below which the Giant Fiber stays quiet.
- **Why it matters:** each LC4 neuron covers part of the visual field, so a bigger looming image activates more of them. This curve tells the input encoding how many neurons an approaching obstacle must activate before the fly "jumps". It's the biological basis for the encoding, and it may make a separate firing-threshold dial unnecessary.

### E4. Specificity controls
- **Stimulate**, each at 150 Hz for 1 s:
  1. nothing (baseline);
  2. right **LC10a** (119 neurons; a visual projection neuron with no direct synapses onto the Giant Fiber);
  3. the 21 right sugar GRNs (the sugar → MN9 input).
- **It works if:** the Giant Fiber stays near zero in all three.
- **Why it matters:** it shows the Giant Fiber responds to looming input specifically, not to any strong input.
- **Caveat:** LC10a still reaches the Giant Fiber through 47 neurons in two steps (314 synapses). Every large LC type I checked does (LC12, LC17, LC18: 821–1,244 synapses). Some Giant Fiber activity here would be a real model result, not a failed test, and is worth reporting.

### E5. Lesions (neuron silencing only)
The plan's J4 line says "silence LC4/LPLC2 and check the Giant Fiber goes quiet". **That test is circular:** our input goes straight into LC4/LPLC2, so silencing them removes the input itself. These lesions ask a more useful question instead: how much do the Giant Fiber's *other* inputs (~80% of its synapses) shape the response?

- **E5a, LC4 only:** stimulate LC4 with LPLC2 silenced, and the reverse. Tells us whether either type alone can drive a jump.
- **E5b, inhibitory partners:** stimulate LC4 + LPLC2 with the Giant Fiber's top predicted-inhibitory input partners silenced (CB3707, SAD014, CL038, PVLP010, LHAD1g1, CB0010, CB0563; 22% / 23% of its input together, right / left). If the Giant Fiber fires much more, the looming input is recruiting feed-forward inhibition, and S5 must keep those neurons.
- **E5c, excitatory partners:** the same with the top non-looming excitatory partners silenced (DNp70, PVLP122b, PVLP062, PVLP151).
- **Measure:** Giant Fiber rate and latency, compared with E1 at the same input.
- **Not included without a joint decision:** cutting only the LC4/LPLC2 → Giant Fiber synapses while keeping the neurons. That would directly test the indirect routes, but it edits individual connections, which D5 doesn't cover. Decide with Jacob first.

### E6. Which partners does the looming input recruit?
- **Run during E1** (both types, 150 Hz): also watch the Giant Fiber's top ~20 input partners on each side (ranked by synapse count; see the table below).
- **Measure:** each partner's firing rate.
- **Why it matters:** Shiu-model neurons are silent unless driven. A partner only shapes the Giant Fiber if the looming input actually activates it. The active ones are the candidates for S5's subcircuit rule.

**Giant Fiber input, FlyWire v783** (right / left):

| | Right | Left |
|---|---|---|
| Total input synapses | 5,147 from 483 partners | 4,327 from 479 partners |
| From LPLC2 | 12.1% | 10.6% |
| From LC4 | 8.4% | 8.6% |
| **LC4 + LPLC2** | **20.5%** | **19.2%** |
| Predicted inhibitory | 48% | 51% |
| Largest other partners | CB3707 (−, 6.6%), DNp70 (+, 6.6%) | CB3707 (−, 6.8%), DNp70 (+, 5.8%) |

Signs are predicted neurotransmitters (Eckstein et al. 2024), with glutamate treated as inhibitory as in Shiu's model.

## Steering: T4/T5 → VS cells → DNp20 / DNp22

**Watch:** all 16 VS cells, DNp20 (DNOVS1) and DNp22 (DNOVS2 or 3), both sides, and for S2 the LPi09 neurons.

**What the connectome shows** (all 16 VS cells, 69,082 input synapses):

| Input to VS cells | Share | Route |
|---|---|---|
| T4d + T5d (downward motion) | 55% | direct |
| T4a/b + T5a/b (horizontal motion) | 25% | direct |
| LPi09 (predicted inhibitory) | 10% | direct |
| T4c + T5c (upward motion) | ~0% | only via LPi09 and other LPi neurons (~77k synapses onto LPi09) |

This matches the known biology: VS cells are excited by downward motion and inhibited by upward motion through lobula plate intrinsic (LPi) neurons. It corrects the S2 table, which grouped all four subtypes together as "strong input to VS cells".

### Two sign versions (D26)
**The problem.** T4 and T5 neurons release acetylcholine, so they're excitatory. But the model's sign table (`Excitatory` in `Connectivity_783.parquet`) marks some of them inhibitory. Those signs are machine-learning predictions (Eckstein et al. 2024):

| | Inhibitory in the model's sign table | Not acetylcholine in the annotation table (`top_nt`) |
|---|---|---|
| T4c | 1.7% of neurons | 0.1% |
| T5c | 1.9% | 0.5% |
| **T4d** | **13.7%** (215 of 1,573) | 1.5% |
| **T5d** | **12.1%** (177 of 1,467) | 2.0% |

- FlyWire's own annotation table calls ~98% of T4d/T5d acetylcholine, so the model's sign table disagrees with it as well as with the biology.
- T4d/T5d are the main input to VS cells. In the model, 14% of the T4d → VS synapses and 13% of the T5d → VS synapses push the wrong way.
- The escape pathway is unaffected: all LC4 and LPLC2 → Giant Fiber synapses are excitatory.

**What we do.** Each steering test (S1–S3) runs twice:
- **original:** the connectome exactly as Shiu's model uses it. This stays the main result.
- **corrected:** a copy of the connectivity file with every connection *from* a T4 or T5 neuron (T4a–d, T5a–d) set to excitatory. Nothing else changes.

**Rules:**
- The correction covers T4/T5 only, chosen because there's independent biological evidence for their transmitter. We don't go looking for other neurons to correct; that would be tuning the connectome by another name.
- The corrected file is built by a script, saved in git-ignored `data/` (D13), and never replaces the original. `BrainStepper` takes it as its connectivity path, so Shiu's code stays unchanged (D14).
- Every result is labelled `original` or `corrected` (folder name, tables, plots).
- Which version carries into ship tuning (Step 5) and Stereo Madness is decided before any steering results come in (D26).
- The escape tests (E1–E6) run on the original only.

### S1. Direction selectivity
- **Stimulate:** right T4d + T5d (down) vs. right T4c + T5c (up), each at each rate in the sweep, for 1 s.
- **Measure:** VS cell rates and DNp20/DNp22 rates, each side.
- **It works if:** "down" drives the right VS cells and DNp20, and "up" alone doesn't.

### S2. Opponent inhibition
- **Stimulate:** right T4d + T5d at a fixed rate that drives VS cells (from S1), plus T4c + T5c added at each rate in the sweep.
- **Measure:** VS and DNp20 rates against "down only"; LPi09 rate.
- **It works if:** adding upward motion lowers VS activity, through LPi09.
- **Why the background drive:** neurons in this model are silent at rest, so inhibition onto a silent cell changes nothing we can see. VS cells need ongoing "down" input to show the suppression.

### S3. Horizontal-motion control
- **Stimulate:** right T4a/b + T5a/b at 150 Hz.
- **It works if:** VS and DNp20 respond less than to downward motion at the same rate.

### What "works" would and wouldn't mean for the ship
A direction-selective response from VS cells to DNp20 means the model *can* carry an up/down signal to a descending neuron. It doesn't make the circuit a ship controller: DNOVS neurons mainly drive head movements (see `docs/notes/dnovs.md`), and hold/release would be our interface choice (D11).

## Caveats that apply to the results

- **No gap junctions.** The model has only chemical synapses. It's missing VS–VS coupling, VS–DNOVS coupling (Suver et al. 2016) and the Giant Fiber–TTM electrical synapse. Steering inputs are probably underestimated.
- **VS cells mostly signal with graded potentials**, not spikes. In this model they can only spike, so their responses are a simplification.
- **Predicted-sign errors in T4/T5.** About 13% of the T4d/T5d → VS synapses have the wrong sign in the model. The steering tests therefore run on both the original and a corrected copy (see "Two sign versions" under Steering).
- **Direct stimulation skips the visual computation.** We drive LC4/LPLC2 and T4/T5 directly. Their looming and direction selectivity is built into our encoding, not computed by the fly's circuit.
- **Whole brain now, subcircuit later.** These are reference results; the subcircuit (S5, J5) must reproduce them.

## Results feed into

| Result | Used for |
|---|---|
| E1 dose–response | input-strength dial and its range (T4) |
| E2 latency, offset | how early the looming input must start; output rule (T4) |
| E3 recruitment | input encoding: looming size → number of LC4 neurons driven (T4) |
| E5, E6 | subcircuit rule (S5) |
| S1–S3 | go/no-go for the ship pathway (T3) |

## Sources
- Connectome numbers: FlyWire v783 (`data/Connectivity_783.parquet`) with flywire_annotations v3.1.0 cell types; computed 2026-10-27.
- Game timing: `docs/game_physics.md` §3.
- Eckstein N et al. (2024). Neurotransmitter classification from electron microscopy images at synaptic sites in *Drosophila melanogaster*. *Cell* 187:2574–2594.
- Suver MP, Huda A, Iwasaki N, Safarik S, Dickinson MH (2016). An array of descending visual interneurons encoding self-motion in *Drosophila*. *J Neurosci* 36:11768–11780.
