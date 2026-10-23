# DNOVS neurons: mapping to FlyWire v783 cell types

*Shannyn, task S2. Last updated 2026-10-22.*

## What DNOVS neurons are
DNOVS ("descending neurons of the ocellar and vertical system") are descending neurons that receive input from the lobula plate VS cells and project to the thoracic ganglia. They were first described in large flies (Strausfeld & Bassemir 1985) and studied physiologically in the blowfly (e.g. Wertz, Borst & Haag 2008, on DNOVS2). Suver et al. (2016) identified and filled DNOVS1 and DNOVS2 in *Drosophila* (their Figure 2A).

## Mapping to FlyWire names
FlyWire uses the systematic names from Namiki et al. (2018), so "DNOVS" does not appear in the annotation table. Namiki et al. (2018), Supplementary file 2 ("Similar neuron" column) gives:

| FlyWire / Namiki type | Similar to | Citation in Namiki Supp. file 2 | Confidence |
|---|---|---|---|
| DNp20 | DNOVS1 | Strausfeld & Bassemir 1985 | Good: one-to-one match |
| DNp22 | DNOVS2 **or** DNOVS3 | Strausfeld & Bassemir 1985; FlyCircuit | Uncertain: could be DNOVS3 |

"Similar neuron" means similar morphology, not a formal identity, so we say DNp20 *corresponds to* DNOVS1 rather than *is* DNOVS1.

## Connectivity check (FlyWire v783, `scripts/find_target_neurons.py`)
- VS cells → DNp20: 82 synapses (left) and 182 (right), from 6 and 8 VS cells, all excitatory. DNp20 is the descending neuron VS cells synapse onto most.
- VS cells → DNp22: 42 (left) and 35 (right), from 2 VS cells per side. It is a much weaker link.
- This fits DNp20 as the main VS-driven steering candidate.

## Caveats
- DNOVS neurons are partly coupled to VS cells by **gap junctions** (Suver et al. 2016, Fig. 2). FlyWire and the Shiu model contain only chemical synapses, so the model underestimates this input.
- DNOVS neurons mainly drive **neck/head movements** for gaze stabilisation (see PROJECT_BRIEF §3.2), so using them for ship hold/release is our interface choice, not the fly's own behaviour.
- One pair each (left/right) of DNp20 and DNp22 exists in v783; all IDs are checked against `Completeness_783.csv`.

## References
- Namiki S, Dickinson MH, Wong AM, Korff W, Card GM (2018). The functional organization of descending sensory-motor pathways in *Drosophila*. *eLife* 7:e34272. Supplementary file 2.
- Strausfeld NJ, Bassemir UK (1985). Lobula plate and ocellar interneurons converge onto a cluster of descending neurons leading to neck and leg motor neuropil in *Calliphora erythrocephala*. *Cell Tissue Res* 240:617–640.
- Suver MP, Huda A, Iwasaki N, Safarik S, Dickinson MH (2016). An array of descending visual interneurons encoding self-motion in *Drosophila*. *J Neurosci* 36:11768–11780.
- Wertz A, Borst A, Haag J (2008). Nonlinear integration of binocular optic flow by DNOVS2, a descending neuron of the fly. *J Neurosci* 28:3131–3140.
