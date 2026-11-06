import numpy as np
import pandas as pd
import pytest

from stereo_flyness.experiments.step7_analysis import first_split, shared_approaches


def test_identical_games_have_no_split():
    assert first_split([0, 1, 0, 1], [0, 1, 0, 1]) is None


def test_split_is_the_first_differing_press():
    assert first_split([0, 1, 0, 1, 1], [0, 1, 1, 1, 0]) == 2


def test_a_shorter_run_splits_where_it_ended():
    assert first_split([0, 1, 0], [0, 1, 0, 0, 1]) == 3


def brain(theta, press):
    return pd.DataFrame({"theta_deg": np.asarray(theta, float), "gap": np.zeros(len(theta)),
                         "fly_press": np.asarray(press, bool)})


def test_identical_games_match_on_every_approach():
    theta = [0, 10, 20, 30, 0, 0, 10, 20, 0]
    press = [0, 0, 0, 1, 0, 0, 0, 1, 0]
    out = shared_approaches(brain(theta, press), brain(theta, press), [(1, 4), (6, 8)], split=None)
    assert out["matched"] == out["compared"] == 2 and not out["apart"]


def test_approaches_after_the_split_are_left_out():
    theta_w = [0, 10, 20, 30, 0, 0, 10, 20, 0]
    theta_s = [0, 10, 20, 30, 0, 5, 99, 99, 99]  # different after the split: a different game
    w = brain(theta_w, [0, 0, 1, 0, 0, 0, 0, 1, 0])
    s = brain(theta_s, [0, 0, 0, 1, 0, 0, 0, 0, 0])
    split = first_split(w["fly_press"], s["fly_press"])
    assert split == 2
    out = shared_approaches(w, s, [(1, 4), (6, 8)], split)
    # Only the first approach, cut at the split: the whole brain pressed there, the subcircuit not yet.
    assert out["approaches"] == 1 and out["only_whole"] == 1 and out["matched"] == 0


def test_mismatched_input_before_the_split_is_refused():
    w = brain([0, 10, 20], [0, 0, 1])
    s = brain([0, 11, 20], [0, 0, 1])
    with pytest.raises(ValueError):
        shared_approaches(w, s, [(1, 3)], split=None)
