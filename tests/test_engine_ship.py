"""Ship physics, ship collisions and portals (docs/game_physics.md §4, §5)."""

import pytest

from stereo_flyness.game import physics as P
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level, Portal
from stereo_flyness.game.objects import hitbox


def obj(kind, x, y):
    return Box(kind, *hitbox(kind, x, y))


def ship_game(*boxes, portals=(), length=5000):
    """Starts as a ship resting on the ground: area floor 0, ceiling 300."""
    return Game(Level("test", "hand-made", length, list(boxes), list(portals), start_mode="ship"))


def run(game, held, ticks):
    for _ in range(ticks):
        game.tick(held)
    return game


def test_ship_starts_in_the_ground_area():
    assert ship_game().bounds == (0, 300)


def test_holding_reaches_max_climb_speed_in_93_ticks():
    game, ticks = ship_game(), 0
    while game.player.vy < P.SHIP_MAX_UP:
        game.tick(True)
        ticks += 1
    assert ticks == 93  # §4 derived: 0 -> +8 in 93 ticks (0.39 s)


def test_releasing_from_max_climb_reaches_max_fall_speed_in_170_ticks():
    game = ship_game()
    game.player.y, game.player.vy, game.player.on_ground = 150.0, P.SHIP_MAX_UP, False
    ticks = 0
    while game.player.vy > -P.SHIP_MAX_DOWN:
        game.tick(False)
        ticks += 1
        assert game.player.top < 300 and game.player.bottom > 0  # stays clear of the bounds
    assert ticks == 170  # §4 derived: +8 -> -6.4 in 170 ticks (0.71 s)


def test_speed_limits():
    game = ship_game()
    game.player.y = 150.0
    for held in [True] * 400 + [False] * 400:
        game.tick(held)
        assert -P.SHIP_MAX_DOWN <= game.player.vy <= P.SHIP_MAX_UP


def test_ship_slides_along_floor_and_ceiling_without_dying():
    game = run(ship_game(), held=True, ticks=600)
    assert game.player.alive and game.player.top == 300 and game.player.vy == 0
    run(game, held=False, ticks=600)
    assert game.player.alive and game.player.bottom == 0 and game.player.vy == 0


def test_ship_rests_on_top_of_blocks():
    row = [obj("block", 15 + 30 * k, 45) for k in range(40)]  # y 30-60, from x 0 to 1200
    game = ship_game(*row)
    game.player.y, game.player.on_ground = 75.0, False  # just above the row
    run(game, held=False, ticks=300)
    assert game.player.alive and game.player.bottom == 60 and game.player.on_ground


def test_ship_bumps_along_the_underside_of_blocks():
    row = [obj("block", 15 + 30 * k, 105) for k in range(40)]  # y 90-120 overhead
    game = run(ship_game(*row), held=True, ticks=300)
    assert game.player.alive and game.player.top == 90 and game.player.vy == 0


def test_ship_dies_flying_into_a_wall():
    wall = [obj("block", 615, 15 + 30 * k) for k in range(10)]  # full-height wall at x 600
    game = run(ship_game(*wall), held=False, ticks=600)
    assert game.death is not None and game.death.kind == "block"


def test_ship_dies_on_a_spike():
    game = run(ship_game(obj("spike", 615, 15)), held=False, ticks=600)
    assert game.death.kind == "spike"


def test_cube_to_ship_to_cube_through_portals():
    portals = [Portal("ship", 300, 45), Portal("cube", 1500, 45)]
    game = Game(Level("test", "hand-made", 3000, [], portals))
    modes = []
    for t in range(2400):
        game.tick(300 <= t < 600)  # fly up for a while in the ship section
        modes.append(game.player.mode)
        if game.player.mode == "ship":
            assert game.bounds == (0, 300)
    assert game.player.alive
    assert modes[0] == "cube" and "ship" in modes and modes[-1] == "cube"
    switches = [i for i in range(1, len(modes)) if modes[i] != modes[i - 1]]
    assert len(switches) == 2


def test_portal_missed_vertically_does_not_trigger():
    game = Game(Level("test", "hand-made", 3000, [], [Portal("ship", 300, 200)]))  # y 157-243
    run(game, held=False, ticks=600)
    assert game.player.mode == "cube"


def test_ship_portal_inside_a_ship_section_raises_the_area():
    # Flying along the ceiling (y 270-300) into a ship portal at y 285 moves the area up.
    game = ship_game(portals=[Portal("ship", 600, 285)])
    run(game, held=True, ticks=600)
    assert game.bounds == (120, 420)  # world 375 -> centre 360 -> floor 120 (level y)
    run(game, held=True, ticks=300)
    assert game.player.alive and game.player.top == 420
