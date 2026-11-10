# Ship design reading: the DNOVS readout and a speed anchor

*Shannyn, Step 5 groundwork. Last updated 2026-11-09. Reading for Q2 (output rule) and Q4 (calibration anchor) in `docs/notes/ship_brief.md`, plus a connectome check. Nothing here is a decision: the ship design is proposed separately and logged as a D entry once agreed.*

**Sources**
- Suver MP, Huda A, Iwasaki N, Safarik S, Dickinson MH (2016). An array of descending visual interneurons encoding self-motion in *Drosophila*. *J Neurosci* 36:11768–11780. doi:10.1523/JNEUROSCI.2277-16.2016
- Maisak MS, Haag J, Ammer G, Serbe E, Meier M, Leonhardt A, Schilling T, Bahl A, Rubin GM, Nern A, Dickson BJ, Reiff DF, Hopp E, Borst A (2013). A directional tuning map of *Drosophila* elementary motion detectors. *Nature* 500:212–216. Results read from the published abstract and from Maisak's dissertation (LMU Munich), which reproduces the paper's text.

## Summary

- **DNp20 (DNOVS1) doesn't spike in the real fly** and mainly targets neck motor neurons. A spike-based hold/release rule on DNp20 would read a signal the real neuron never sends.
- **DNOVS2 spikes and reaches the wing motor region.** The connectome check below supports **DNp22 = DNOVS2** (not DNOVS3): its numbered VS inputs are VS2 and VS3 only, exactly the cells Suver found coupled to DNOVS2.
- **A speed anchor exists:** T4 and T5 respond most to motion at a temporal frequency of ~1 Hz (30°/s for a 30° grating) in non-flying flies. Using it needs one stated choice of ours: how far away the ship's scenery is.

## Suver et al. 2016: the DNOVS neurons in *Drosophila*

**What they did.** Whole-cell recordings from three descending neurons (DNOVS1, DNOVS2, DNHS1), from VS and HS cells, in tethered flies at rest and in flight. Fills identified their coupled partners and thoracic targets. Stimuli: rotation of the visual world around different body axes at 22.5°/s, and 1 Hz vertical and horizontal gratings. A tracking system related each neuron's tuning to head, wing and abdomen movements.

| | DNOVS1 (our DNp20) | DNOVS2 (our DNp22, see below) |
|---|---|---|
| Spikes | **None:** "purely graded changes in membrane potential" | **Yes:** small spikes (~1–5 mV) on graded changes. Rate rises ~8–9 Hz per mV (8.2 in flight, 8.8 at rest) |
| Dye-coupled VS cells | VS4, VS5, VS6 | VS2, VS3 |
| Thoracic targets | Neck motor region only; dye-coupled to frontal neck motor neurons | Neck, wing and haltere motor regions |
| Change in flight | Baseline +4.7 ± 1.6 mV | Baseline +24.5 ± 13.9 Hz, and much larger motion responses |
| Tuning | A rotation axis (roll/pitch mix) | A rotation axis (roll/pitch mix) |

Other points:
- All three neurons encode **rotations** of the body, not translations. Each correlated with a set of motor programs, which the authors stress isn't causal.
- They found no dye coupling to ocellar neurons, unlike in the blowfly, and suggest the ocellar input may be chemical.
- VS and HS cells responded only a few mV more in flight, while DNOVS2 and DNHS1 spike rates rose much more.

## Maisak et al. 2013: T4/T5 speed tuning

- Calcium imaging of T4 and T5 in non-flying flies, with gratings moving front to back at speeds spanning two orders of magnitude.
- **T4 responded most at 30°/s, a temporal frequency of 1 Hz** (Fig. 3e). T5 peaked at a similar temporal frequency. The dissertation sums up the optimum of both as "around 1–2 Hz".
- **Not yet checked:** reports that flight or octopamine shift the optimum higher (Jung et al. 2011; Suver et al. 2012). If they hold up, the anchor depends on behavioural state, and the ship flies.

## Connectome check: which VS cells feed DNp20 and DNp22

**Method.** FlyWire v783 (`data/Connectivity_783.parquet`) with cell types from `data/flywire_annotations_v3.1.0_neurons.tsv`. Every VS-type cell (VS1–VS8, VSm, VST1, VST2), synapses onto each DNp20 and DNp22, summed per presynaptic type and side. All 4 descending neurons and 32 VS cells are in `data/Completeness_783.csv`.

| Input | DNp20 L | DNp20 R | DNp22 L | DNp22 R |
|---|---|---|---|---|
| VS1 | – | 1 | – | – |
| VS2 | – | 1 | **16** | **15** |
| VS3 | 21 | 13 | **26** | **20** |
| VS4 | **21** | **27** | – | – |
| VS5 | **18** | **22** | – | – |
| VS6 | **9** | **51** | – | – |
| VS7 | 9 | 18 | – | – |
| VS8 | 4 | 49 | – | – |
| VSm | – | – | 173 | 151 |
| VST1 | 1 | 5 | 9 | 42 |
| VST2 | 26 | 122 | 16 | 14 |
| All VS types | 109 (9.8%) | 309 (20.9%) | 240 (8.7%) | 242 (9.2%) |
| All inputs | 1,115 | 1,477 | 2,755 | 2,643 |

**Against Suver's dye coupling**
- **DNp22 matches DNOVS2:** of the numbered VS cells it gets input from VS2 and VS3 only, on both sides. This is evidence for DNOVS2 over DNOVS3 (Namiki et al. 2018 list both; `docs/notes/dnovs.md`).
- **DNp20 broadly matches DNOVS1:** most of its numbered VS input is from VS4–VS8, and almost none from VS1–VS2. FlyWire numbers VS cells to VS8 and Suver's *Drosophila* labels stop at VS6, so the numbering may not correspond one to one.
- **Limits:** dye coupling shows gap junctions; these are chemical synapses, the only kind FlyWire and the model contain. The two agreeing is support, not proof.

**Other findings**
1. **VSm changes "DNp22 is the weaker link".** Counting only VS1–VS8 gives DNp22 42 / 35 synapses (the figures in `dnovs.md` and `ship_brief.md`). Adding VSm, which "down" motion drives strongly (T4d + T5d → VSm: 7,654 synapses), DNp22's VS input is about the same as DNp20's. The pathway tests watched VS1–VS8 only (16 cells, `docs/FEASIBILITY.md`), not VSm, VST1 or VST2.
2. **Ocellar neurons are the biggest input to both** (OCG01 types; e.g. OCG01c → DNp22 L: 417 synapses), consistent with the name "descending neurons of the ocellar and vertical system". Our input never drives the ocelli, so this input stays silent in every run.
3. **Front-to-back motion reaches DNp20's inputs far more than DNp22's:**

   | T4/T5 synapses onto | VS2 | VS3 | VS4 | VS5 | VS6 | VSm |
   |---|---|---|---|---|---|---|
   | Down (T4d + T5d) | 11,136 | 9,318 | 4,074 | 2,533 | 1,769 | 7,654 |
   | Front-to-back (T4a + T5a) | 0 | 85 | 1,004 | 1,695 | 2,753 | 5 |

   Any encoding of forward scrolling (`docs/notes/t4_proposals.md` §5) would drive DNp20 much more than DNp22.

## What this means for the ship design (proposals for discussion)

| Question | Bearing |
|---|---|
| Q2: which neuron | **DNp22 is the stronger readout:** it matches a spiking neuron with wing motor targets and gets little scrolling input. DNp20 matches a non-spiking neck neuron. Changes D-pathway wording that treats DNp20 as the main output (`decisions.md`, pathway rules), so it's for discussion, not a change yet. |
| Q2: rate rule | DNOVS2's spike rate tracks its membrane potential roughly linearly, so a rate- or window-based rule (not a single spike) is closer to how it signals. |
| Q1: what the fly sees | The DNOVS neurons encode body **rotation**. The ship's climb and fall are translation, which still moves the scene down or up past both eyes. Using that is our mapping, stated as such. |
| Q3: population | DNp22's numbered VS inputs (VS2, VS3) get almost only "down" motion (T4d/T5d). |
| Q4: anchor | T4/T5 peak at ~1 Hz (30°/s for a 30° grating, non-flying). Calibrating needs our choice of scenery distance to turn game speed into °/s; that choice gets logged like θ_full. |
| Model limits | No gap junctions (VS–DNOVS and DNOVS1–neck motor neurons are electrical); no ocellar input; the model's VS cells spike, while real ones signal mostly with graded potentials. |

## Still open

- Whether flight shifts the T4/T5 optimum (Jung et al. 2011; Suver et al. 2012), and by how much.
- DNOVS2 response size at a known speed (Suver Fig. 3G gives spike rates at 22.5°/s rotation; figure only).
- How VSm responded to "down" drive in the pathway tests (it wasn't watched, but every neuron that fired was recorded, D34), and whether the subcircuit keeps it.
- What VSm is, and whether it has a described counterpart.
