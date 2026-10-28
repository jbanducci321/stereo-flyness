"""Difficulty measurements (D26): press windows, spacing, ship openings, tier ordering."""

import pytest

from stereo_flyness.game.bot import solve
from stereo_flyness.game.difficulty import MS_PER_TICK, clusters, measure, press_windows, tightest_opening
from stereo_flyness.game.generator import build_ship, generate
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox


def obj(kind, x, y):
    return Box(kind, *hitbox(kind, x, y))


@pytest.mark.parametrize("n, ticks", [(1, 57), (2, 34), (3, 11)])
def test_spike_press_windows(n, ticks):
    """Single spike: 57 ticks = 238 ms, as measured directly in the engine (game_physics.md §3)."""
    lv = Level("t", "t", 2000, [obj("spike", 615 + 30 * i, 15) for i in range(n)])
    (window,) = press_windows(lv, solve(lv).tick_inputs)
    assert window == pytest.approx(ticks * MS_PER_TICK)


def test_clusters_and_gaps():
    lv = Level("t", "t", 3000, [obj("spike", 615, 15), obj("spike", 645, 15), obj("block", 1215, 15)])
    assert clusters(lv) == [(612, 648), (1200, 1230)]
    stats = measure(lv, solve(lv).tick_inputs)
    assert stats.clusters == 2 and stats.min_gap_s == pytest.approx((1200 - 648) / 311.58, rel=1e-3)
    assert stats.hazards == 2 and stats.solids == 1 and stats.presses == 2


def test_ship_opening_of_a_gap_wall():
    wall = [obj("block", 615, 15 + 30 * j) for j in range(10) if not 4 <= j < 8]  # opening y 120-240
    lv = Level("t", "t", 2000, wall, start_mode="ship")
    assert lv.sections()[0][3] == (0, 300)  # a ship start gets the ground-level area
    assert tightest_opening(lv) == 120


def test_ship_tiers_have_shrinking_openings():
    worst = {d: min(tightest_opening(build_ship(s, d)) for s in range(10)) for d in ("easy", "medium", "hard")}
    assert worst["easy"] >= worst["medium"] > worst["hard"] >= 90


def test_easy_cube_levels_need_no_split_second_presses():
    """Easy levels avoid staircases and platform spikes, so every press window is >= 100 ms."""
    for seed in range(5):
        g = generate("cube", seed, "easy")
        stats = measure(g.level, g.bot.tick_inputs)
        assert stats.presses > 0 and stats.tightest_window_ms >= 100


def test_hard_cube_levels_are_denser_than_easy():
    density = {d: sum(measure(g.level, g.bot.tick_inputs).clusters_per_10s
                      for g in (generate("cube", s, d) for s in range(4))) for d in ("easy", "hard")}
    assert density["hard"] > density["easy"]
