"""Control connectomes for Step 4 (draft: docs/notes/step4_proposal.md, not yet agreed).

A control is a new connectivity table with the same columns as Connectivity_783.parquet, written
into git-ignored data/ and read by BrainStepper through its connectivity path, like D27's
sign-corrected copy. The original table is only read; shiu_model.py is not touched.

Degree-preserving shuffle: every connection keeps its presynaptic neuron, synapse count and sign;
the postsynaptic neurons are permuted across connections. So each neuron keeps its number of
inputs and outputs, its total output weight and its sign, and *who connects to whom* is
destroyed. Self-connections and duplicate pairs that the permutation creates are removed by
swapping targets with random other connections until none are left (the original has neither).

`keep` fixes chosen connections in place (e.g. the direct LC4/LPLC2 -> Giant Fiber ones, the
proposal's section 3c); only the others are shuffled among themselves.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

POST_COLUMNS = ("Postsynaptic_ID", "Postsynaptic_Index")


@dataclass
class ShuffleReport:
    connections: int
    kept: int  # held in place by `keep`
    shuffled: int
    rounds: int  # swap rounds needed to remove self-connections and duplicates (+1 if the careful pass ran)
    unchanged: int  # shuffled connections that ended on their original target by chance


def _bad(pre: np.ndarray, post: np.ndarray, kept: np.ndarray, n: int) -> np.ndarray:
    """Positions of shuffled connections that are self-connections or repeat an earlier pair.

    Within a repeated pair, a kept connection is never marked: the shuffled copies are.
    """
    bad = (pre == post) & ~kept
    key = pre * n + post
    order = np.lexsort((~kept, key))  # by pair, kept connections first within a pair
    k = key[order]
    repeat = np.zeros(len(k), dtype=bool)
    repeat[1:] = k[1:] == k[:-1]
    bad[order[repeat]] = True
    return np.flatnonzero(bad & ~kept)


def _careful(pre, post_idx, post_id, free, bad, n, rng, max_tries):
    """Fix the remaining bad connections one by one with swaps that create no new problem."""
    count: dict[int, int] = {}
    for key in (pre * n + post_idx).tolist():
        count[key] = count.get(key, 0) + 1
    for b in bad.tolist():
        if pre[b] != post_idx[b] and count[pre[b] * n + post_idx[b]] == 1:
            continue  # already fixed by an earlier swap
        for _ in range(max_tries):
            p = int(free[rng.integers(len(free))])
            if p == b:
                continue
            new_b, new_p = pre[b] * n + post_idx[p], pre[p] * n + post_idx[b]
            if pre[b] == post_idx[p] or pre[p] == post_idx[b] or count.get(new_b, 0) or count.get(new_p, 0):
                continue
            for key in (pre[b] * n + post_idx[b], pre[p] * n + post_idx[p]):
                count[key] -= 1
            count[new_b], count[new_p] = 1, 1
            post_idx[b], post_idx[p] = post_idx[p], post_idx[b]
            post_id[b], post_id[p] = post_id[p], post_id[b]
            break
        else:
            raise RuntimeError(f"no valid swap found for connection {b} in {max_tries} tries")


def degree_preserving_shuffle(con: pd.DataFrame, seed: int, keep=None, fast_rounds: int = 50,
                              max_tries: int = 100_000) -> tuple[pd.DataFrame, ShuffleReport]:
    """Shuffle the postsynaptic side of `con` (see the module docstring). Returns a new table."""
    rng = np.random.default_rng(seed)
    kept = np.zeros(len(con), dtype=bool) if keep is None else np.asarray(keep, dtype=bool)
    if len(kept) != len(con):
        raise ValueError("keep must have one entry per connection")
    pre = con["Presynaptic_Index"].to_numpy()
    post_idx = con["Postsynaptic_Index"].to_numpy().copy()
    post_id = con["Postsynaptic_ID"].to_numpy().copy()
    n = int(max(pre.max(), post_idx.max())) + 1

    free = np.flatnonzero(~kept)
    perm = free[rng.permutation(len(free))]
    post_idx[free], post_id[free] = post_idx[perm], post_id[perm]

    rounds = 0
    bad = _bad(pre, post_idx, kept, n)
    # Fast part: swap every bad connection's target with a random other free connection's at
    # once. On a sparse connectome this clears nearly everything in a few rounds.
    while len(bad) and rounds < fast_rounds:
        rounds += 1
        others = np.setdiff1d(free, bad, assume_unique=True)
        partner = others[rng.choice(len(others), size=len(bad), replace=False)]
        post_idx[bad], post_idx[partner] = post_idx[partner], post_idx[bad].copy()
        post_id[bad], post_id[partner] = post_id[partner], post_id[bad].copy()
        bad = _bad(pre, post_idx, kept, n)
    # Careful part: one bad connection at a time, accepting only swaps that leave both
    # connections valid, so the count can only go down.
    if len(bad):
        rounds += 1
        _careful(pre, post_idx, post_id, free, bad, n, rng, max_tries)
        left = _bad(pre, post_idx, kept, n)
        if len(left):
            raise RuntimeError(f"{len(left)} self-connections or duplicates left")

    out = con.copy()
    out["Postsynaptic_Index"], out["Postsynaptic_ID"] = post_idx, post_id
    unchanged = int((post_idx[free] == con["Postsynaptic_Index"].to_numpy()[free]).sum())
    return out, ShuffleReport(len(con), int(kept.sum()), len(free), rounds, unchanged)


def check_shuffle(original: pd.DataFrame, shuffled: pd.DataFrame, keep=None) -> list[str]:
    """Everything a degree-preserving shuffle must keep. Returns the failures (empty = pass)."""
    fails = []
    if list(original.columns) != list(shuffled.columns) or len(original) != len(shuffled):
        return ["columns or row count differ"]
    if not (original.dtypes == shuffled.dtypes).all():
        fails.append("column types differ")
    same = ["Presynaptic_ID", "Presynaptic_Index", "Connectivity", "Excitatory", "Excitatory x Connectivity"]
    for col in same:
        if not np.array_equal(original[col].to_numpy(), shuffled[col].to_numpy()):
            fails.append(f"{col} changed")
    if keep is not None:
        k = np.asarray(keep, dtype=bool)
        for col in POST_COLUMNS:
            if not np.array_equal(original[col].to_numpy()[k], shuffled[col].to_numpy()[k]):
                fails.append(f"a kept connection's {col} changed")
    in_deg = lambda df: df["Postsynaptic_Index"].value_counts().sort_index()  # noqa: E731
    if not in_deg(original).equals(in_deg(shuffled)):
        fails.append("in-degrees changed")
    ids = shuffled.groupby("Postsynaptic_Index")["Postsynaptic_ID"].nunique()
    if (ids > 1).any():
        fails.append("Postsynaptic_ID and Postsynaptic_Index no longer match")
    pre, post = shuffled["Presynaptic_Index"].to_numpy(), shuffled["Postsynaptic_Index"].to_numpy()
    if (pre == post).any():
        fails.append("self-connections")
    if shuffled.duplicated(["Presynaptic_Index", "Postsynaptic_Index"]).any():
        fails.append("duplicate pairs")
    return fails
