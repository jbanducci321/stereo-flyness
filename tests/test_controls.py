"""The degree-preserving shuffle (Step 4 control, draft) on small random connectivity tables."""

import numpy as np
import pandas as pd
import pytest

from stereo_flyness.brain.controls import check_shuffle, degree_preserving_shuffle


def table(n_neurons=60, n_edges=900, seed=1):
    """A random table shaped like Connectivity_783: no self-connections or duplicates, one sign per neuron."""
    rng = np.random.default_rng(seed)
    pairs = set()
    while len(pairs) < n_edges:
        a, b = rng.integers(n_neurons, size=2)
        if a != b:
            pairs.add((int(a), int(b)))
    pre, post = np.array(sorted(pairs)).T
    sign = rng.choice([-1, 1], size=n_neurons)
    syn = rng.integers(1, 30, size=n_edges)
    ids = 720575940000000000 + np.arange(n_neurons) * 7  # FlyWire-like IDs, not the index
    return pd.DataFrame({
        "Presynaptic_ID": ids[pre], "Postsynaptic_ID": ids[post],
        "Presynaptic_Index": pre, "Postsynaptic_Index": post,
        "Connectivity": syn, "Excitatory": sign[pre], "Excitatory x Connectivity": syn * sign[pre],
    })


def test_shuffle_keeps_degrees_weights_and_signs():
    con = table()
    out, report = degree_preserving_shuffle(con, seed=0)
    assert check_shuffle(con, out) == []
    # Who connects to whom has changed for most connections.
    assert report.unchanged < 0.2 * len(con)
    assert report.shuffled == len(con) and report.kept == 0


def test_dense_table_needs_and_completes_swap_rounds():
    con = table(n_neurons=20, n_edges=250)  # ~66% dense, so the permutation makes many repeats
    out, report = degree_preserving_shuffle(con, seed=3)
    assert report.rounds > 0
    assert check_shuffle(con, out) == []


def test_same_seed_same_table_different_seed_different_table():
    con = table()
    a, _ = degree_preserving_shuffle(con, seed=5)
    b, _ = degree_preserving_shuffle(con, seed=5)
    c, _ = degree_preserving_shuffle(con, seed=6)
    assert a.equals(b)
    assert not a.equals(c)


def test_kept_connections_stay_in_place():
    con = table()
    keep = np.zeros(len(con), dtype=bool)
    keep[::10] = True
    out, report = degree_preserving_shuffle(con, seed=0, keep=keep)
    assert check_shuffle(con, out, keep=keep) == []
    assert report.kept == keep.sum()
    assert (out.loc[keep, "Postsynaptic_ID"].to_numpy() == con.loc[keep, "Postsynaptic_ID"].to_numpy()).all()


def test_original_table_is_not_modified():
    con = table()
    before = con.copy()
    degree_preserving_shuffle(con, seed=0)
    assert con.equals(before)


def test_check_catches_broken_shuffles():
    con = table()
    out, _ = degree_preserving_shuffle(con, seed=0)
    selfie = out.copy()
    selfie.loc[0, "Postsynaptic_Index"] = selfie.loc[0, "Presynaptic_Index"]
    assert "self-connections" in check_shuffle(con, selfie)
    dup = out.copy()
    dup.loc[1, ["Presynaptic_Index", "Postsynaptic_Index"]] = dup.loc[0, ["Presynaptic_Index", "Postsynaptic_Index"]]
    assert any("duplicate" in f for f in check_shuffle(con, dup))
    weight = out.copy()
    weight.loc[0, "Connectivity"] += 1
    assert "Connectivity changed" in check_shuffle(con, weight)


def test_keep_must_match_the_table():
    with pytest.raises(ValueError):
        degree_preserving_shuffle(table(), seed=0, keep=[True, False])
