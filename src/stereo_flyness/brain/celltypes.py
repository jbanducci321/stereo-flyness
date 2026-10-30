"""Look up FlyWire IDs by cell type, checked against the model's neuron list (v783).

Cell types come from the flywire_annotations v3.1.0 table (`root_id`, `cell_type`, `side`),
which scripts/find_target_neurons.py downloads into data/. Its root IDs are already v783 IDs,
but every ID handed out here is still checked against Completeness_783.csv (hard rule 4).
"""

import numpy as np
import pandas as pd

SIDES = ("left", "right")


class CellTypes:
    """FlyWire IDs by cell type and side."""

    def __init__(self, annotations: pd.DataFrame, model_ids):
        ann = annotations[["root_id", "cell_type", "side"]].dropna(subset=["cell_type"])
        self._ann = ann.astype({"root_id": "int64"})
        self._model_ids = set(int(i) for i in model_ids)

    @classmethod
    def from_files(cls, path_annotations, path_comp):
        ann = pd.read_csv(path_annotations, sep="\t", usecols=["root_id", "cell_type", "side"],
                          low_memory=False)
        return cls(ann, pd.read_csv(path_comp, index_col=0).index)

    def ids(self, *types: str, side: str | None = None) -> list[int]:
        """Sorted IDs of every neuron of `types`, optionally on one side only."""
        if side is not None and side not in SIDES:
            raise ValueError(f"side must be one of {SIDES}, not {side!r}")
        sel = self._ann[self._ann["cell_type"].isin(types)]
        if side is not None:
            sel = sel[sel["side"] == side]
        found = set(sel["cell_type"])
        if missing := [t for t in types if t not in found]:
            raise KeyError(f"No neurons of type {missing} (side={side})")
        ids = sorted(sel["root_id"])
        if not_in_model := [i for i in ids if i not in self._model_ids]:
            raise KeyError(f"IDs not in the model's v783 neuron list: {not_in_model[:5]}")
        return ids


def top_partners(con: pd.DataFrame, post_id: int, n: int) -> list[int]:
    """The `n` presynaptic neurons with the most synapses onto `post_id` (ties broken by ID)."""
    rows = con[con["Postsynaptic_ID"] == post_id]
    syn = rows.groupby("Presynaptic_ID")["Connectivity"].sum().reset_index()
    syn = syn.sort_values(["Connectivity", "Presynaptic_ID"], ascending=[False, True])
    return [int(i) for i in syn["Presynaptic_ID"].head(n)]


def input_similarity(con: pd.DataFrame, ids: list[int]) -> np.ndarray:
    """Cosine similarity of the neurons' input synapse counts (rows and columns in `ids` order).

    Neurons that share input partners score high. For columnar visual inputs this is a stand-in
    for "nearby in the visual field", since the connectome has no visual-field positions.
    """
    rows = con[con["Postsynaptic_ID"].isin(ids)]
    m = rows.pivot_table(index="Postsynaptic_ID", columns="Presynaptic_ID", values="Connectivity",
                         aggfunc="sum", fill_value=0).reindex(ids, fill_value=0)
    x = m.to_numpy(float).copy()
    norm = np.linalg.norm(x, axis=1, keepdims=True)
    x = np.divide(x, norm, out=np.zeros_like(x), where=norm > 0)
    return x @ x.T


def grow_order(sim: np.ndarray, start: int) -> list[int]:
    """Indices in the order a patch grows from `start`: each step adds the neuron with the
    highest mean similarity to the patch so far (ties broken by index)."""
    order, left = [start], [i for i in range(len(sim)) if i != start]
    total = sim[start].copy()
    while left:
        best = max(left, key=lambda i: (total[i], -i))
        order.append(best)
        left.remove(best)
        total += sim[best]
    return order
