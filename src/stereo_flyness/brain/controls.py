"""Control connectomes for Step 4 (draft: docs/notes/step4_proposal.md, not yet agreed).

A control is a new connectivity table with the same columns as Connectivity_783.parquet, written
into git-ignored data/ and read by BrainStepper through its connectivity path, like D27's
sign-corrected copy. The original table is only read; shiu_model.py is not touched.

Degree-preserving shuffle: every connection keeps its presynaptic neuron, synapse count and sign;
the postsynaptic neurons are permuted across connections. So each neuron keeps its number of
inputs and outputs, its total output weight and its sign, and *who connects to whom* is
destroyed. Self-connections and duplicate pairs that the permutation creates are removed by
swapping targets with random other connections until none are left (the original has neither).

`keep` fixes chosen connections in place (the direct LC4/LPLC2 -> Giant Fiber ones for D51's
control b); only the others are shuffled among themselves, so every neuron's degree is still
preserved. `forbid` = (presynaptic indices, postsynaptic indices) bans shuffled connections between
those groups, so no *new* looming -> Giant Fiber connection appears (D51).

Also here (D51): the relay-only network (control c), the random network (control d) and the
sign- and output-matched random lesions.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

POST_COLUMNS = ("Postsynaptic_ID", "Postsynaptic_Index")


def control_path(data_dir, name: str) -> Path:
    """Where control `name` (e.g. "shuffle_s0") lives: data/Connectivity_783_<name>.parquet."""
    return Path(data_dir) / f"Connectivity_783_{name}.parquet"


def file_sha256(path) -> str:
    """The file's SHA-256, recorded with every run so it says exactly which connectome it used."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@dataclass
class ShuffleReport:
    connections: int
    kept: int  # held in place by `keep`
    shuffled: int
    rounds: int  # swap rounds needed to remove self-connections and duplicates (+1 if the careful pass ran)
    unchanged: int  # shuffled connections that ended on their original target by chance


def _masks(forbid, n):
    """Boolean masks over neuron indices for the banned (pre, post) groups, or None."""
    if forbid is None:
        return None
    fpre, fpost = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
    fpre[np.asarray(forbid[0], dtype=int)] = True
    fpost[np.asarray(forbid[1], dtype=int)] = True
    return fpre, fpost


def _bad(pre: np.ndarray, post: np.ndarray, kept: np.ndarray, n: int, banned=None) -> np.ndarray:
    """Positions of shuffled connections that are self-connections, banned pairs, or repeat an earlier pair.

    Within a repeated pair, a kept connection is never marked: the shuffled copies are.
    """
    bad = (pre == post) & ~kept
    if banned is not None:
        bad |= banned[0][pre] & banned[1][post]
    key = pre * n + post
    order = np.lexsort((~kept, key))  # by pair, kept connections first within a pair
    k = key[order]
    repeat = np.zeros(len(k), dtype=bool)
    repeat[1:] = k[1:] == k[:-1]
    bad[order[repeat]] = True
    return np.flatnonzero(bad & ~kept)


def _careful(pre, post_idx, post_id, free, bad, n, rng, max_tries, banned=None):
    """Fix the remaining bad connections one by one with swaps that create no new problem."""
    count: dict[int, int] = {}
    for key in (pre * n + post_idx).tolist():
        count[key] = count.get(key, 0) + 1

    def ban(a, b):
        return banned is not None and bool(banned[0][a] and banned[1][b])

    for b in bad.tolist():
        if pre[b] != post_idx[b] and count[pre[b] * n + post_idx[b]] == 1 and not ban(pre[b], post_idx[b]):
            continue  # already fixed by an earlier swap
        for _ in range(max_tries):
            p = int(free[rng.integers(len(free))])
            if p == b:
                continue
            new_b, new_p = pre[b] * n + post_idx[p], pre[p] * n + post_idx[b]
            if pre[b] == post_idx[p] or pre[p] == post_idx[b] or count.get(new_b, 0) or count.get(new_p, 0):
                continue
            if ban(pre[b], post_idx[p]) or ban(pre[p], post_idx[b]):
                continue
            for key in (pre[b] * n + post_idx[b], pre[p] * n + post_idx[p]):
                count[key] -= 1
            count[new_b], count[new_p] = 1, 1
            post_idx[b], post_idx[p] = post_idx[p], post_idx[b]
            post_id[b], post_id[p] = post_id[p], post_id[b]
            break
        else:
            raise RuntimeError(f"no valid swap found for connection {b} in {max_tries} tries")


def degree_preserving_shuffle(con: pd.DataFrame, seed: int, keep=None, forbid=None, fast_rounds: int = 50,
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
    if forbid is not None:
        n = max(n, int(max(np.max(forbid[0], initial=0), np.max(forbid[1], initial=0))) + 1)
    banned = _masks(forbid, n)

    free = np.flatnonzero(~kept)
    perm = free[rng.permutation(len(free))]
    post_idx[free], post_id[free] = post_idx[perm], post_id[perm]

    rounds = 0
    bad = _bad(pre, post_idx, kept, n, banned)
    # Fast part: swap every bad connection's target with a random other free connection's at
    # once. On a sparse connectome this clears nearly everything in a few rounds.
    while len(bad) and rounds < fast_rounds:
        rounds += 1
        others = np.setdiff1d(free, bad, assume_unique=True)
        partner = others[rng.choice(len(others), size=len(bad), replace=False)]
        post_idx[bad], post_idx[partner] = post_idx[partner], post_idx[bad].copy()
        post_id[bad], post_id[partner] = post_id[partner], post_id[bad].copy()
        bad = _bad(pre, post_idx, kept, n, banned)
    # Careful part: one bad connection at a time, accepting only swaps that leave both
    # connections valid, so the count can only go down.
    if len(bad):
        rounds += 1
        _careful(pre, post_idx, post_id, free, bad, n, rng, max_tries, banned)
        left = _bad(pre, post_idx, kept, n, banned)
        if len(left):
            raise RuntimeError(f"{len(left)} self-connections or duplicates left")

    out = con.copy()
    out["Postsynaptic_Index"], out["Postsynaptic_ID"] = post_idx, post_id
    unchanged = int((post_idx[free] == con["Postsynaptic_Index"].to_numpy()[free]).sum())
    return out, ShuffleReport(len(con), int(kept.sum()), len(free), rounds, unchanged)


def check_shuffle(original: pd.DataFrame, shuffled: pd.DataFrame, keep=None, forbid=None) -> list[str]:
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
    if forbid is not None:
        k = np.zeros(len(shuffled), dtype=bool) if keep is None else np.asarray(keep, dtype=bool)
        hit = np.isin(pre, forbid[0]) & np.isin(post, forbid[1]) & ~k
        if hit.any():
            fails.append(f"{int(hit.sum())} new connections between the forbidden groups")
    return fails


def pathway_mask(con: pd.DataFrame, pre_ids, post_ids) -> np.ndarray:
    """Connections from any of `pre_ids` to any of `post_ids` (FlyWire IDs)."""
    return (con["Presynaptic_ID"].isin(pre_ids) & con["Postsynaptic_ID"].isin(post_ids)).to_numpy()


def relay_only(con: pd.DataFrame, pre_ids, post_ids) -> pd.DataFrame:
    """D51 control c: only the connections from `pre_ids` to `post_ids`, unchanged; nothing else."""
    return con[pathway_mask(con, pre_ids, post_ids)].reset_index(drop=True)


def neuron_signs(con: pd.DataFrame, n_neurons: int, rng) -> np.ndarray:
    """Each model neuron's sign (+1/-1) by index, from its outgoing connections.

    Neurons with no outgoing connection have no sign in the data; they get one at random, in the
    proportion of excitatory neurons among those that have one.
    """
    sign = np.zeros(n_neurons, dtype=np.int64)
    first = con.groupby("Presynaptic_Index")["Excitatory"].first()
    sign[first.index.to_numpy()] = first.to_numpy()
    unknown = sign == 0
    p_exc = float((first > 0).mean())
    sign[unknown] = np.where(rng.random(int(unknown.sum())) < p_exc, 1, -1)
    return sign


def random_network(con: pd.DataFrame, flyids, seed: int) -> pd.DataFrame:
    """D51 control d: the same neurons and number of connections, placed uniformly at random.

    `flyids` maps model index -> FlyWire ID (the completeness file's order). No self-connections
    or duplicate pairs. Each neuron keeps its sign (neuron_signs), and the synapse counts are the
    real ones, shuffled across the new connections.
    """
    rng = np.random.default_rng(seed)
    flyids = np.asarray(flyids, dtype=np.int64)
    n, m = len(flyids), len(con)
    if m > n * (n - 1):
        raise ValueError("more connections than distinct pairs")
    keys = np.empty(0, dtype=np.int64)
    while len(keys) < m:
        need = m - len(keys)
        pre = rng.integers(n, size=int(need * 1.05) + 10)
        post = rng.integers(n, size=len(pre))
        keys = np.concatenate([keys, (pre * n + post)[pre != post]])
        keys = keys[np.sort(np.unique(keys, return_index=True)[1])]  # drop repeats, keep draw order
    keys = keys[:m]
    pre, post = keys // n, keys % n
    sign = neuron_signs(con, n, rng)
    syn = rng.permutation(con["Connectivity"].to_numpy())
    out = pd.DataFrame({
        "Presynaptic_ID": flyids[pre], "Postsynaptic_ID": flyids[post],
        "Presynaptic_Index": pre, "Postsynaptic_Index": post,
        "Connectivity": syn, "Excitatory": sign[pre], "Excitatory x Connectivity": syn * sign[pre],
    })
    out = out.sort_values(["Presynaptic_Index", "Postsynaptic_Index"]).reset_index(drop=True)
    return out[list(con.columns)].astype(con.dtypes.to_dict())


def matched_random_lesion(con: pd.DataFrame, lesion_ids, exclude_ids, seed: int, tol: float = 0.10,
                          involved=None) -> list[int]:
    """D51's random-lesion control: one random neuron per lesioned neuron, same sign, total output
    synapses within +-tol, never in `exclude_ids` or the lesion itself, and never picked twice.

    With `involved` (D51 amendment: the neurons that fired in the recruitment runs), each stand-in
    also has the lesioned neuron's status: involved for involved, not involved for not involved,
    so the control silences exactly as many involved neurons as the lesion.

    Lesioned neurons are matched in ID order, each from its own candidates, with a fixed seed.
    """
    rng = np.random.default_rng(seed)
    out_syn = con.groupby("Presynaptic_ID")["Connectivity"].sum()
    sign = con.groupby("Presynaptic_ID")["Excitatory"].first()
    banned = {int(i) for i in exclude_ids} | {int(i) for i in lesion_ids}
    involved = None if involved is None else {int(i) for i in involved}
    picked = []
    for lid in sorted(int(i) for i in lesion_ids):
        if lid not in out_syn.index:
            raise ValueError(f"{lid} has no outgoing connections to match")
        w, s = out_syn[lid], sign[lid]
        ok = out_syn.index[((out_syn >= (1 - tol) * w) & (out_syn <= (1 + tol) * w) & (sign == s)).to_numpy()]
        ok = [int(i) for i in ok if int(i) not in banned
              and (involved is None or (int(i) in involved) == (lid in involved))]
        if not ok:
            raise ValueError(f"no candidate matches {lid}")
        choice = ok[int(rng.integers(len(ok)))]
        picked.append(choice)
        banned.add(choice)
    return picked
