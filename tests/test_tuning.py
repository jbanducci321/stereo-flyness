"""Step 3's pick rule on made-up scores with known answers."""

import pytest

from stereo_flyness.experiments.tuning import OpenLoop, pick_rate, tie_margin

ALL_FIRE = {r: OpenLoop(t, 10, 10) for r, t in {25: 60.0, 50: 50.0, 75: 44.0, 100: 41.0, 150: 39.0, 200: 33.0}.items()}


def test_the_best_mean_progress_wins():
    assert pick_rate({25: 0.20, 50: 0.40, 150: 0.30}, ALL_FIRE, default=150, margin=0.01) == (50, [50])


def test_ties_go_to_the_open_loop_theta_closest_to_39():
    # 50, 75 and 100 are within a point of the best; 100 fires at 41°, closest to 39°.
    winner, tied = pick_rate({25: 0.30, 50: 0.395, 75: 0.40, 100: 0.392, 200: 0.10}, ALL_FIRE, default=150, margin=0.01)
    assert tied == [50, 75, 100]
    assert winner == 100


def test_theta_not_the_rate_decides_the_tie():
    # 200 is closer to 150 on a log scale, but 100's θ (41°) is closer to 39° than 200's (33°).
    assert pick_rate({100: 0.5, 200: 0.5}, ALL_FIRE, default=150, margin=0.01)[0] == 100


def test_a_rate_where_fewer_than_half_fire_ranks_last():
    ol = {**ALL_FIRE, 25: OpenLoop(39.0, 4, 10), 50: OpenLoop(55.0, 5, 10)}
    # 25's θ is exactly 39°, but only 4 of 10 fired; 50 has 5 of 10, which is half: it ranks first.
    assert pick_rate({25: 0.5, 50: 0.5}, ol, default=150, margin=0.01)[0] == 50


def test_among_rates_that_rarely_fire_more_fired_ranks_higher():
    ol = {25: OpenLoop(None, 0, 10), 50: OpenLoop(45.0, 3, 10)}
    assert pick_rate({25: 0.5, 50: 0.5}, ol, default=150, margin=0.01)[0] == 50


def test_the_margin_edge_counts_as_tied():
    assert pick_rate({50: 0.40, 150: 0.39}, ALL_FIRE, default=150, margin=0.01) == (150, [50, 150])


def test_a_tie_needs_the_open_loop_check():
    with pytest.raises(ValueError):
        pick_rate({50: 0.4, 150: 0.4}, {150: ALL_FIRE[150]}, default=150, margin=0.01)


def test_no_scores():
    with pytest.raises(ValueError):
        pick_rate({}, ALL_FIRE, default=150, margin=0.01)


def test_tie_margin_is_measured_with_a_floor():
    assert tie_margin(0.40, 0.43) == pytest.approx(0.03)
    assert tie_margin(0.40, 0.395) == 0.01
