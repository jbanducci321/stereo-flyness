"""The T4/T5 sign-corrected connectivity copy (D27), a labelled sensitivity check, not tuning.

The model's synapse signs are machine-learning neurotransmitter predictions (Eckstein et al.
2024). They mark ~12-14% of T4d/T5d neurons inhibitory, although T4/T5 are cholinergic
(excitatory). D27 runs the steering tests on both the original connectome and a copy where every
connection *from* a T4 or T5 neuron (T4a-d, T5a-d) is excitatory.

Rules (D27):
- Only T4/T5 are corrected.
- The original file is never modified.
- Results from the copy are always labelled "corrected".
"""

from dataclasses import dataclass

import pandas as pd

T4T5_TYPES = tuple(f"{t}{s}" for t in ("T4", "T5") for s in "abcd")
CORRECTED_NAME = "Connectivity_783_T4T5corrected.parquet"


@dataclass
class CorrectionReport:
    neurons: int  # T4/T5 neurons given as presynaptic sources
    neurons_flipped: int  # of those, how many had inhibitory outgoing signs
    connections_flipped: int  # connection rows changed from -1 to +1
    synapses_flipped: int  # synapses on those rows
    rows_total: int


def correct_signs(con: pd.DataFrame, presynaptic_ids) -> tuple[pd.DataFrame, CorrectionReport]:
    """A copy of `con` with every connection from `presynaptic_ids` made excitatory.

    Only the `Excitatory` column and the signed weight (`Excitatory x Connectivity`) change.
    Synapse counts, partners and every other neuron's connections are untouched.
    """
    ids = set(int(i) for i in presynaptic_ids)
    out = con.copy()
    rows = out["Presynaptic_ID"].isin(ids) & (out["Excitatory"] < 0)
    out.loc[rows, "Excitatory"] = 1
    out.loc[rows, "Excitatory x Connectivity"] = out.loc[rows, "Connectivity"]
    report = CorrectionReport(
        neurons=len(ids & set(con["Presynaptic_ID"])),
        neurons_flipped=con.loc[rows, "Presynaptic_ID"].nunique(),
        connections_flipped=int(rows.sum()),
        synapses_flipped=int(con.loc[rows, "Connectivity"].sum()),
        rows_total=len(con),
    )
    return out, report
