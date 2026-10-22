# Data

Nothing in this folder except this README is committed. Every file is downloaded or extracted locally.

Download the connectome files (about 104 MB, checksums verified):

```bash
uv run python scripts/download_data.py
```

| File | Source | Version | License | Status |
|---|---|---|---|---|
| `Connectivity_783.parquet` | [Shiu et al. model repo](https://github.com/philshiu/Drosophila_brain_model), commit `91bdd1e` | FlyWire v783 | Repo: MIT. Underlying FlyWire data: CC BY 4.0 ([Zenodo](https://zenodo.org/records/10676866)) | `download_data.py` |
| `Completeness_783.csv` | Same as above | FlyWire v783 | Same as above | `download_data.py` |
| Cell-type labels | [Codex](https://codex.flywire.ai/) (requires sign-in) or [flywire_annotations](https://github.com/flyconnectome/flywire_annotations) | v783 | To be checked: see the Codex download page's citation requirements | Not yet downloaded |
| Stereo Madness level data | Extracted locally from Geometry Dash level data | GD 2.1 copy | Level design © RobTop Games. **Never commit.** | Not yet extracted |

## What's in the connectome files

- `Completeness_783.csv`: one row per neuron (138,639), indexed by FlyWire root ID. The row order defines the model's neuron index.
- `Connectivity_783.parquet`: one row per connected pair (15,091,983 pairs, 54,492,922 synapses), with columns:
  - `Presynaptic_ID` / `Postsynaptic_ID`: FlyWire root IDs;
  - `Presynaptic_Index` / `Postsynaptic_Index`: the model's neuron indices;
  - `Connectivity`: synapse count;
  - `Excitatory`: +1 or −1, from the predicted neurotransmitter;
  - `Excitatory x Connectivity`: the signed weight the model uses.

FlyWire root IDs can change between releases when neurons are re-proofread, so IDs from papers using v630 must be checked against v783.

## Citations

When using this data, cite:

- Dorkenwald, S. et al. (2024). Neuronal wiring diagram of an adult brain. *Nature* 634, 124–138.
- Schlegel, P. et al. (2024). Whole-brain annotation and multi-connectome cell typing of *Drosophila*. *Nature* 634, 139–152.
- Shiu, P. K. et al. (2024). A *Drosophila* computational brain model reveals sensorimotor processing. *Nature* 634, 210–219.
- Eckstein, N. et al. (2024). Neurotransmitter classification from electron microscopy images at synaptic sites in *Drosophila melanogaster*. *Cell* 187, 2574–2594. (These are the source of the excitatory/inhibitory signs.)
