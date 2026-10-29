"""Subcircuit-vs-whole-brain comparisons (J5) on made-up data with known answers."""

import math

import numpy as np
import pandas as pd
import pytest

from stereo_flyness.experiments.subcircuit_validation import activity_fidelity, compare_groups, neuron_rates


def fake(ids, counts, n_frames=10):
    """A saved-trial-like dict: total spikes per neuron, all in frame 0."""
    spikes = np.zeros((n_frames, len(ids)), dtype=np.uint16)
    spikes[0] = counts
    return {"meta": {"n_frames": n_frames, "frame_ms": 100.0}, "all_ids": np.array(ids), "all_spikes": spikes}


def test_neuron_rates_average_over_trials():
    rates = neuron_rates([fake([1, 2], [2, 4]), fake([2, 3], [6, 1])])  # 1 s each, 2 s total
    assert rates.to_dict() == {1: 1.0, 2: 5.0, 3: 0.5}
    assert neuron_rates([]).empty


def test_activity_fidelity():
    whole = pd.Series({1: 10.0, 2: 20.0, 3: 30.0, 9: 50.0})  # 9 is cut out of the subcircuit
    sub = pd.Series({1: 11.0, 2: 19.0, 4: 5.0})  # 3 went silent, 4 is newly active
    f = activity_fidelity(whole, sub, sub_ids=[1, 2, 3, 4], exclude=[])
    assert f["whole_active"] == 4 and f["inside"] == 3 and f["cut_active"] == 1
    assert f["kept_active"] == pytest.approx(2 / 3)
    assert f["new_active"] == 1
    assert -1 <= f["r"] <= 1

    same = activity_fidelity(whole, whole, sub_ids=[1, 2, 3, 9])
    assert same["r"] == pytest.approx(1.0) and same["kept_active"] == 1.0 and same["new_active"] == 0

    no_stim = activity_fidelity(whole, sub, sub_ids=[1, 2, 3, 4], exclude=[1, 2])  # our input left out
    assert no_stim["whole_active"] == 2 and no_stim["kept_active"] == 0.0


def test_activity_fidelity_with_nothing_active():
    f = activity_fidelity(pd.Series(dtype=float), pd.Series(dtype=float), sub_ids=[1])
    assert f["whole_active"] == 0 and math.isnan(f["kept_active"]) and math.isnan(f["r"])


def test_compare_groups():
    whole = pd.DataFrame({"key": ["a", "a", "b"], "rate:GF_R": [100.0, 110.0, 0.0]})
    sub = pd.DataFrame({"key": ["a", "a", "b", "c"], "rate:GF_R": [90.0, 100.0, 0.0, 5.0]})
    cmp = compare_groups(whole, sub, ["GF_R", "VS_R"]).set_index("condition")
    assert list(cmp.index) == ["a", "b"]  # only conditions on both networks; VS_R absent
    assert cmp.loc["a", "diff"] == pytest.approx(-10.0)
    assert cmp.loc["a", "rel_error"] == pytest.approx(-10 / 105)
    assert cmp.loc["b", "rel_error"] == 0.0
