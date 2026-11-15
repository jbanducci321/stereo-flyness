"""Iteration 2, fix 1 (docs/notes/fix1_design.md, step 1 checks): the no-press path option.

- Off by default, and the default encoder is unchanged.
- On, it changes nothing in the air or on the floor (along the bot's path through generated levels).
- On a raised platform, pits past the edge loom in the landing-level view; a plain edge stays silent;
  a spike on the platform keeps its usual θ.
"""

import math

import pytest

from stereo_flyness.game.engine import Game
from stereo_flyness.game.generator import generate
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox
from stereo_flyness.game.player import Player
from stereo_flyness.interface.encoding import PREDICTED_LABELS, VIEWS, CubeEncoder, angular_size

NO_PATCHES = {s: {t: [] for t in ("LC4", "LPLC2")} for s in ("right", "left")}
PLATFORM = 6  # columns 20-25 hold the platform (x 600-780)


def _level(objs):
    boxes = [Box(k, *hitbox(k, x, y)) for k, x, y in objs]
    return Level("t", "test", 3000.0, boxes)


def _platform(after=(), height=1):
    objs = [("block", 600 + 30 * i + 15, 15 + 30 * j) for i in range(PLATFORM) for j in range(height)]
    return _level(objs + list(after))


def _pits(k, width):
    """Pits starting k ground cells after the platform's end (x 780)."""
    return [("pit", 780 + 30 * (k + i) + 15, 2) for i in range(width)]


def _enc(level, path="no_press", view="landing"):
    return CubeEncoder(level, NO_PATCHES, 180.0, 150.0, "collision", path=path, view=view)


def _on_platform(x, height=1):
    return Player(x=x, y=30 * height + 15, on_ground=True)


def test_default_is_off_and_bad_options_are_refused():
    level = _platform()
    assert _enc(level, "current").path == CubeEncoder(level, NO_PATCHES, 180.0, 150.0).path == "current"
    with pytest.raises(ValueError):
        CubeEncoder(level, NO_PATCHES, 180.0, 150.0, path="parallax")
    with pytest.raises(ValueError):
        CubeEncoder(level, NO_PATCHES, 180.0, 150.0, mode="all", path="no_press")


@pytest.mark.parametrize("k", [0, 1, 3])
def test_pits_past_a_platform_loom_in_the_landing_level_view(k):
    level = _platform(_pits(k, 3))
    pit_x0 = 780 + 30 * k
    for x in (700.0, 740.0, 760.0):
        p = _on_platform(x)
        now, fixed = _enc(level, "current").encode(p), _enc(level).encode(p)
        assert now.theta_deg == 0 and now.obstacle is None  # today: nothing looms on the platform
        assert fixed.predicted and fixed.obstacle.x0 == pit_x0 and fixed.obstacle.bottom == 0
        gap = pit_x0 - (x + 15)
        assert fixed.gap == pytest.approx(gap)
        # the same θ as the pit seen from the ground at the same gap
        assert fixed.theta_deg == pytest.approx(math.degrees(angular_size(gap, 0.0, 17.0, 15.0)))


def test_the_pit_reaches_the_threshold_from_the_platform_only_with_the_fix():
    level = _platform(_pits(0, 3))
    xs = [700 + 0.5 * i for i in range(160)]  # walking towards the edge (x 780)
    assert max(_enc(level, "current").encode(_on_platform(x)).theta_deg for x in xs) == 0
    assert max(_enc(level).encode(_on_platform(x)).theta_deg for x in xs) >= 39


@pytest.mark.parametrize("height", [1, 2])
def test_a_plain_step_down_makes_nothing_loom(height):
    level = _platform(height=height)
    enc = _enc(level)
    for x in (620.0, 700.0, 760.0, 779.0):
        loom = enc.encode(_on_platform(x, height))
        assert loom.obstacle is None and loom.theta_deg == 0 and not loom.predicted


def test_a_spike_on_the_platform_keeps_its_usual_theta():
    level = _platform([("spike", 600 + 30 * 4 + 15, 45)] + _pits(0, 3))
    p = _on_platform(650.0)
    now, fixed = _enc(level, "current").encode(p), _enc(level).encode(p)
    assert now.obstacle is not None and not fixed.predicted
    assert (fixed.obstacle, fixed.theta_deg) == (now.obstacle, now.theta_deg)


def test_the_path_is_reused_while_the_fly_does_not_press():
    level = _platform(_pits(2, 3))
    enc, game = _enc(level), Game(level)
    game.player = _on_platform(650.0)
    first = enc.no_press_path(game.player)
    game.tick(False)
    again = enc.no_press_path(game.player)
    assert again.states == first.states[1:] and again.floor_x == first.floor_x


@pytest.mark.parametrize("difficulty,seed", [("easy", 0), ("medium", 0), ("medium", 1), ("hard", 0)])
def test_nothing_changes_in_the_air_or_on_the_floor(difficulty, seed):
    """Along the bot's winning path, every tick off a raised surface encodes identically."""
    g = generate("cube", seed, difficulty, seconds=15)
    now, fixed, game = _enc(g.level, "current"), _enc(g.level), Game(g.level)
    raised = 0
    for held in g.bot.tick_inputs:
        game.tick(held)
        p = game.player
        a, b = now.encode(p), fixed.encode(p)
        if p.on_ground and p.bottom > 1e-6:
            raised += 1
            if not b.predicted:  # objects already on course keep their usual θ
                assert (a.obstacle, a.theta_deg) == (b.obstacle, b.theta_deg)
        else:
            assert a == b
        if game.over:
            break
    if difficulty != "easy":
        assert raised > 0  # the check covers ticks on raised surfaces too


@pytest.mark.parametrize("height,peak", [(1, 13.5), (2, 7.3)])
def test_true_optics_puts_the_pits_on_course_but_they_stay_small(height, peak):
    """Option (i): the same objects come on course, but θ is from the real eye, so it never nears 39°."""
    level = _platform(_pits(0, 3), height=height)
    enc = _enc(level, view="eye")
    looms = [enc.encode(_on_platform(700 + 0.5 * i, height)) for i in range(160)]
    # on course: the pit the walk-off would fall into (the first or second cell, by height)
    assert all(l.predicted and l.obstacle.bottom == 0 and l.obstacle.x0 in (780.0, 810.0) for l in looms)
    assert max(l.theta_deg for l in looms) <= peak + 0.2 < 39


def test_views_and_labels():
    assert set(VIEWS) == set(PREDICTED_LABELS) and _enc(_platform()).view == "landing"
    assert PREDICTED_LABELS["landing"] == "θ shown from landing level, our construction"
    with pytest.raises(ValueError):
        _enc(_platform(), view="parallax")
