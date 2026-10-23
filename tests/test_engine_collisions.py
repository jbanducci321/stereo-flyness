"""Cube collisions and death on tiny hand-made levels (docs/game_physics.md §5, §6)."""

import pytest

from stereo_flyness.game import physics as P
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox


def obj(kind, x, y):
    return Box(kind, *hitbox(kind, x, y))


def game_with(*boxes, length=3000):
    return Game(Level(name="test", source="hand-made", length=length, boxes=list(boxes)))


def run(game, held=False, ticks=600):
    for _ in range(ticks):
        game.tick(held)
    return game


def test_standing_on_a_row_of_blocks_then_falling_off_the_end():
    game = game_with(*[obj("block", 15 + 30 * k, 15) for k in range(20)])  # row from x 0 to 600
    game.player.y = 45  # start on top of the row
    run(game, ticks=200)  # x = 260
    assert game.player.alive and game.player.on_ground and game.player.bottom == 30
    run(game, ticks=400)  # off the end at x = 615, then falls to the ground
    assert game.player.alive and game.player.on_ground and game.player.bottom == 0


def test_running_into_a_block_kills_when_it_reaches_the_inner_hitbox():
    game = run(game_with(obj("block", 315, 15)))
    assert game.death is not None and game.death.kind == "block"
    # The inner 9 x 9 box (half width 4.5) touches the block's left side at x = 300.
    assert 300 - P.INNER_HITBOX / 2 <= game.death.x < 300 - P.INNER_HITBOX / 2 + P.X_PER_TICK


def test_jumping_clears_a_block():
    game = run(game_with(obj("block", 315, 15)), held=True, ticks=400)
    assert game.player.alive and game.player.x > 450


def test_grazing_a_block_above_does_not_kill():
    # Block from y 25 to 55 overlaps the top 5 units of the player's box, but not the inner box.
    game = run(game_with(obj("block", 315, 40)), ticks=400)
    assert game.player.alive and game.player.x > 450 and game.player.bottom == 0


def test_spike_kills_on_touching_the_outer_hitbox():
    game = run(game_with(obj("spike", 315, 15)))
    assert game.death.kind == "spike"
    # The spike's hitbox starts at x = 312; the outer box (half width 15) touches it at x = 297.
    assert 297 <= game.death.x < 297 + P.X_PER_TICK


def press_once_at(tick, *boxes, ticks=500):
    game = game_with(*boxes)
    for t in range(ticks):
        game.tick(t == tick)
    return game


def test_a_well_timed_jump_clears_a_spike_and_bad_timing_dies():
    spike = obj("spike", 315, 15)
    survived = [t for t in range(240) if press_once_at(t, spike).player.alive]
    assert survived, "some jump timing must clear a single spike"
    assert 0 not in survived  # jumping far too early lands before the spike
    assert 230 not in survived  # x = 298.6 at that tick: already touching the spike
    # The safe window is one contiguous stretch of ticks.
    assert survived == list(range(survived[0], survived[-1] + 1))


def test_landing_on_a_floating_slab_and_walking_off():
    slab = obj("slab", 315, 53)  # hitbox y 46-60: top flush with the cell top
    assert (slab.y0, slab.y1) == (46, 60)
    game = game_with(slab)
    game.player.x, game.player.y = 300.0, 60 + 15  # start standing on the slab
    run(game, ticks=10)
    assert game.player.alive and game.player.on_ground and game.player.bottom == 60
    run(game, ticks=100)  # past the slab's end (x 330 + 15)
    assert game.player.alive and game.player.bottom == 0


def test_running_under_a_floating_slab_is_safe():
    game = run(game_with(obj("slab", 315, 53)), ticks=400)
    assert game.player.alive and game.player.x > 450


def test_stair_snap_nudges_x_by_at_most_one_unit():
    game = game_with()
    prev, step = obj("block", 0, 15), obj("block", 120, 45)  # one block up, 120 units on
    game._snapped_to, game._snap_offset = prev, 5.0  # last landing was 5 units right of prev's centre
    game.player.x = 124.2
    game._stair_snap(game.player, step)
    assert game.player.x == pytest.approx(125.0)  # target 120 + 5, within 1 unit of 124.2
    game.player.x = 122.0
    game._snapped_to, game._snap_offset = prev, 5.0
    game._stair_snap(game.player, step)
    assert game.player.x == pytest.approx(123.0)  # target 125, clamped to a 1-unit nudge


def test_stair_snap_ignores_non_step_offsets():
    game = game_with()
    game._snapped_to, game._snap_offset = obj("block", 0, 15), 5.0
    game.player.x = 101.0
    game._stair_snap(game.player, obj("block", 100, 45))  # 100 units on: not a standard step
    assert game.player.x == 101.0


def test_reaching_the_end_finishes_the_level():
    game = run(game_with(length=500), ticks=600)
    assert game.finished and game.player.alive and game.death is None
    assert game.progress == 1.0
    x = game.player.x
    run(game, ticks=10)
    assert game.player.x == x  # nothing happens after the level is over


def test_death_record_and_progress():
    game = run(game_with(obj("spike", 1515, 15), length=3000), ticks=2000)
    d = game.death
    assert d.kind == "spike" and d.tick == game.ticks
    assert game.progress == pytest.approx(d.x / 3000)
