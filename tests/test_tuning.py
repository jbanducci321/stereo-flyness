"""Step 3's pick rule on made-up scores with known answers."""

import pytest

from stereo_flyness.experiments.tuning import pick_rate


def test_the_best_mean_progress_wins():
    assert pick_rate({25: 0.20, 50: 0.40, 150: 0.30}, default=150, margin=0.01) == (50, [50])


def test_ties_go_to_the_rate_closest_to_the_default():
    # 50 and 100 are within a point of the best (75); 100 is closest to 150 on a log scale.
    winner, tied = pick_rate({25: 0.30, 50: 0.395, 75: 0.40, 100: 0.392, 200: 0.10}, default=150, margin=0.01)
    assert tied == [50, 75, 100]
    assert winner == 100


def test_the_default_wins_any_tie_it_is_in():
    assert pick_rate({100: 0.50, 150: 0.495, 200: 0.50}, default=150, margin=0.01)[0] == 150


def test_log_scale_distance():
    # 75 is a factor of 2 below 150, 200 a factor of 1.33 above: 200 is closer.
    assert pick_rate({75: 0.5, 200: 0.5}, default=150, margin=0.01)[0] == 200


def test_the_margin_edge_counts_as_tied():
    assert pick_rate({50: 0.40, 150: 0.39}, default=150, margin=0.01) == (150, [50, 150])


def test_no_scores():
    with pytest.raises(ValueError):
        pick_rate({}, default=150, margin=0.01)
