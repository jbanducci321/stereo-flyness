"""The D37 runaway-cascade test and the stuck-state diagnostic."""

import numpy as np
import pytest

from stereo_flyness.experiments.cascades import (
    cascade_flags, find_cascades, load_stuck_state, save_stuck_state, stuck_share,
)
from stereo_flyness.experiments.pathway_tests import Condition


def test_cascade_needs_both_ratio_and_extra():
    # The known S2 cascade: 2.6x and ~8,000 above the median; a 3x ratio alone would miss it
    flags = cascade_flags({0: 4800, 1: 4845, 2: 12808, 3: 4900, 4: 4700}, ratio=2, min_extra=5000)
    assert flags == {0: False, 1: False, 2: True, 3: False, 4: False}
    # A small condition can double by chance without thousands of extra neurons
    assert not any(cascade_flags({0: 26, 1: 60, 2: 25}, ratio=2, min_extra=5000).values())
    # Thousands extra but not 2x: not a cascade
    assert not any(cascade_flags({0: 10000, 1: 16000, 2: 10500}, ratio=2, min_extra=5000).values())
    assert cascade_flags({0: 99999}, ratio=2, min_extra=5000) == {0: False}  # nothing to compare with


def test_find_cascades_on_saved_trials(tmp_path):
    cond = Condition("S1", "S1/up_R/100Hz", "corrected", {"up_R": [1]}, [(1, {})], {}, trials=4)
    for t, n in enumerate([100, 120, 9000, 110]):
        path = cond.path(tmp_path, t)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, all_ids=np.arange(n))
    assert find_cascades([cond], tmp_path, ratio=2, min_extra=5000) == {("corrected/S1/up_R/100Hz", 2)}


def test_stuck_state_round_trip_and_share(tmp_path):
    path = tmp_path / "stuck.csv"
    save_stuck_state(path, [3, 1, 2, 4], "test note")
    ids = load_stuck_state(path)
    assert list(ids) == [1, 2, 3, 4]
    assert stuck_share([1, 2, 99], ids) == pytest.approx(0.5)
    assert np.isnan(stuck_share([1], []))
