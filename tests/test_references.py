"""The no-brain players (D48; always press for the Step 4 draft) on small hand-made levels."""

import numpy as np

from stereo_flyness.experiments.references import always, never, play, random_presses
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox


def spike_level(x=600.0):
    return Level("one_spike", "test", x + 300, [Box("spike", *hitbox("spike", x, 15.0))])


def empty_level(length=1500.0):
    return Level("empty", "test", length, [])


def count_takeoffs(level, press):
    """Ticks on which the cube leaves the ground, playing as `play` does."""
    game, held, takeoffs = Game(level), False, 0
    while not game.over:
        was_on_ground = game.player.on_ground
        game.tick(held)
        takeoffs += was_on_ground and not game.player.on_ground
        held = game.player.mode == "cube" and press(game)
    return takeoffs


def test_never_press_dies_on_the_spike():
    result = play(spike_level(), never)
    assert not result["completed"]
    assert result["death"].startswith("spike")


def test_always_press_jumps_again_on_every_landing():
    level = empty_level()
    result = play(level, always)
    assert result["completed"]
    # Back-to-back jumps the whole way: many take-offs, and never a second tick on the ground.
    game, held, ground_run, longest = Game(level), False, 0, 0
    while not game.over:
        game.tick(held)
        ground_run = ground_run + 1 if game.player.on_ground else 0
        longest = max(longest, ground_run)
        held = always(game)
    assert count_takeoffs(level, always) > 5
    assert longest <= 1


def test_never_press_never_leaves_the_ground():
    assert count_takeoffs(empty_level(), never) == 0


def test_random_presses_are_fixed_by_the_seed():
    level = spike_level()
    a = play(level, random_presses(0.05, np.random.default_rng([0, 7])))
    b = play(level, random_presses(0.05, np.random.default_rng([0, 7])))
    assert a == b


def test_extreme_rates_match_never_and_always():
    level = spike_level()
    assert play(level, random_presses(0.0, np.random.default_rng(0))) == play(level, never)
    assert play(level, random_presses(1.0, np.random.default_rng(0))) == play(level, always)


# --- ship (Step 5, before any ship design) -----------------------------------------------------


def ship_level(length=2000.0, boxes=()):
    return Level("ship_test", "test", length, list(boxes), start_mode="ship")


def heights(level, press, modes):
    """The ship's height after every tick, playing as `play` does."""
    game, held, ys = Game(level), False, []
    while not game.over:
        game.tick(held)
        ys.append(game.player.y)
        held = game.player.mode in modes and press(game)
    return ys


def test_ship_never_hold_falls_to_the_floor_and_always_hold_climbs_to_the_ceiling():
    level = ship_level()
    low, high = heights(level, never, ("ship",)), heights(level, always, ("ship",))
    floor, ceiling = Game(level).bounds
    assert play(level, never, modes=("ship",))["completed"]  # the floor and ceiling don't kill
    assert play(level, always, modes=("ship",))["completed"]
    assert min(low[-50:]) == max(low[-50:]) and low[-1] < floor + 30  # resting on the floor
    assert min(high[-50:]) == max(high[-50:]) and high[-1] > ceiling - 30  # pressed against the ceiling


def test_cube_only_presses_ignore_the_ship():
    """The default (cube only, as in Step 2) never holds in ship mode, even with always."""
    level = ship_level()
    assert heights(level, always, ("cube",)) == heights(level, never, ("cube",))


def test_ship_always_hold_dies_on_a_ceiling_spike():
    floor, ceiling = Game(ship_level()).bounds
    spike = Box("spike", *hitbox("spike", 800.0, ceiling - 15.0))
    level = ship_level(boxes=[spike])
    assert not play(level, always, modes=("ship",))["completed"]
    assert play(level, never, modes=("ship",))["completed"]
