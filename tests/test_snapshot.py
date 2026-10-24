"""Game.snapshot / Game.restore: rewinding must be exact, so the bot can backtrack."""

from dataclasses import replace

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level, Portal
from stereo_flyness.game.objects import hitbox


def mixed_level():
    boxes = [Box("block", *hitbox("block", 15 + 30 * k, 15)) for k in range(30, 40)]  # stair base
    boxes += [Box("block", *hitbox("block", 1335 + 30 * k, 45)) for k in range(5)]
    boxes += [Box("spike", *hitbox("spike", 615, 15)), Box("spike", *hitbox("spike", 2500, 15))]
    portals = [Portal("ship", 1800, 45), Portal("cube", 2300, 45)]
    return Level("test", "hand-made", 4000, boxes, portals)


def inputs(n, offset=0):
    return [((t + offset) % 53) < 4 for t in range(n)]


def state(game):
    return (replace(game.player), game.ticks, game.death, game.finished, list(game.events),
            game.bounds, game._next_portal, game._snapped_to, game._snap_offset)


def test_restore_returns_the_exact_state():
    game = Game(mixed_level())
    for held in inputs(700):
        game.tick(held)
    saved, before = game.snapshot(), state(game)
    for held in inputs(900, offset=17):
        game.tick(held)
    assert state(game) != before
    game.restore(saved)
    assert state(game) == before


def test_same_inputs_after_restore_give_the_same_run():
    game = Game(mixed_level())
    for held in inputs(500):
        game.tick(held)
    saved = game.snapshot()

    def continue_run():
        trace = []
        for held in inputs(2500, offset=5):
            game.tick(held)
            trace.append(state(game))
        return trace

    first = continue_run()
    game.restore(saved)
    assert continue_run() == first


def test_snapshot_is_unaffected_by_later_play():
    game = Game(mixed_level())
    saved = game.snapshot()
    for held in inputs(300):
        game.tick(held)
    assert saved.player.x == 0.0 and saved.ticks == 0  # the saved player is a copy, not the live one


def test_rewinding_out_of_a_death():
    game = Game(Level("test", "hand-made", 3000, [Box("spike", *hitbox("spike", 615, 15))]))
    for _ in range(200):
        game.tick(False)
    saved = game.snapshot()
    while not game.over:
        game.tick(False)  # runs into the spike
    assert game.death is not None
    game.restore(saved)
    assert game.death is None and game.player.alive
    for t in range(600):
        game.tick(t == 220)  # jump this time, at x ~ 545: inside the safe window for a spike at 615
    assert game.death is None and game.player.x > 700
