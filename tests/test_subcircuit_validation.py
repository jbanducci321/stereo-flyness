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
    assert f["kept_active"] == pytest.approx(2 / 4)  # D36 rule 4: the cut-out neuron 9 counts as lost
    assert f["kept_inside"] == pytest.approx(2 / 3)
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


def test_within_tolerance():
    from stereo_flyness.experiments.subcircuit_validation import within_tolerance
    assert within_tolerance(100, 109) and not within_tolerance(100, 111)
    assert within_tolerance(5, 5.9) and not within_tolerance(5, 6.5)  # 1 Hz floor under 10 Hz
    assert within_tolerance(0, 0) and not within_tolerance(0, 2)


def test_first_spike_agreement_per_onset():
    from stereo_flyness.experiments.subcircuit_validation import first_spike_agreement, first_spikes, onsets

    rates = np.array([[0], [100], [100], [0], [0], [100], [100], [0]], dtype=float)
    assert onsets(rates) == [1, 5]

    def trial(gf):
        return {"rates": rates, "spikes": {"GF_R": np.array(gf, dtype=np.uint16).reshape(-1, 1)}}

    whole = trial([0, 0, 1, 0, 0, 0, 0, 0])  # spikes 1 frame after onset 1; nothing after onset 5
    assert first_spikes(whole, "GF_R") == [1, None]
    close = trial([0, 0, 0, 1, 0, 0, 0, 0])  # 1 frame later: matches
    late = trial([0, 0, 0, 0, 1, 0, 0, 0])  # 2 frames later: doesn't
    extra = trial([0, 0, 1, 0, 0, 0, 1, 0])  # also spikes after onset 5: an unmatched event
    assert first_spike_agreement([whole], [close], "GF_R") == (1, 1)
    assert first_spike_agreement([whole], [late], "GF_R") == (0, 1)
    assert first_spike_agreement([whole], [extra], "GF_R") == (1, 2)


def test_kept_by_type():
    from stereo_flyness.experiments.subcircuit_validation import kept_by_type

    fid = pd.DataFrame({"condition": ["a", "b", "c", "d", "e"], "whole_active": [10, 10, 10, 10, 0],
                        "kept_active": [0.95, 0.91, 0.80, 0.99, math.nan]})
    exp = {"a": "P1", "b": "P1", "c": "P2", "d": "P2", "e": "P3"}
    out = kept_by_type(fid, exp)
    assert out["P1"] == (pytest.approx(0.93), pytest.approx(0.91), True)
    assert out["P2"][0] == pytest.approx(0.895) and out["P2"][1] == pytest.approx(0.80) and not out["P2"][2]
    assert "P3" not in out  # nothing active in the whole brain: no test


def test_paired_cascades():
    from stereo_flyness.experiments.subcircuit_validation import paired_cascades

    whole = {0: 3000, 1: 3100, 2: 11000, 3: 2900}
    sub = {0: 2500, 1: 9000, 2: 2600, 3: 2400}  # the subcircuit runs away in trial 1 instead
    assert paired_cascades(whole, sub, ratio=2, min_extra=5000) == {1, 2}
    assert paired_cascades({0: 5, 1: 5}, {0: 5, 1: 5}, ratio=2, min_extra=5000) == set()


def test_approaches_split_on_new_object_and_on_stopping():
    from stereo_flyness.experiments.subcircuit_validation import approaches

    theta = np.array([0, 5, 10, 20, 8, 12, 0, 0, 3, 4])
    gap = np.array([np.nan, 30, 20, 10, 40, 30, np.nan, np.nan, 50, 45])  # jump at 4: a new object
    assert approaches(theta, gap) == [(1, 4), (4, 6), (8, 10)]


def test_press_agreement_counts_first_press_per_approach():
    from stereo_flyness.experiments.subcircuit_validation import press_agreement

    theta = [0, 5, 10, 20, 8, 12, 16, 0, 3, 4, 5, 6]
    gap = [np.nan, 30, 20, 10, 40, 30, 20, np.nan, 50, 45, 40, 35]
    # approach 1 (1-4): both press, 1 frame apart; approach 2 (4-7): only the whole brain;
    # approach 3 (8-12): 3 frames apart. A second press within an approach is ignored.
    w = pd.DataFrame({"theta_deg": theta, "gap": gap, "fly_press": [0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0]})
    s = pd.DataFrame({"theta_deg": theta, "gap": gap, "fly_press": [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1]})
    r = press_agreement(w, s)
    assert (r["approaches"], r["matched"], r["only_whole"], r["apart"], r["neither"]) == (3, 1, 1, 1, 0)
    assert r["diffs"] == [1, 3]


def test_press_agreement_refuses_different_inputs():
    from stereo_flyness.experiments.subcircuit_validation import press_agreement

    w = pd.DataFrame({"theta_deg": [0, 5], "gap": [np.nan, 30], "fly_press": [0, 1]})
    s = pd.DataFrame({"theta_deg": [0, 6], "gap": [np.nan, 30], "fly_press": [0, 1]})
    with pytest.raises(ValueError):
        press_agreement(w, s)
