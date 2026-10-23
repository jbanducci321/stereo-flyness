"""Cube physics on flat ground, checked against docs/game_physics.md §1 and §3."""

from pathlib import Path

import pytest

from stereo_flyness.game import physics as P
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level


def flat_game():
    return Game(Level(name="flat", source="test", length=100_000))


def jump_once(game):
    """Press for one tick, then release until landing. Returns (peak height, airtime ticks)."""
    game.tick(True)
    peak, airtime = game.player.bottom, 1
    while not game.player.on_ground:
        game.tick(False)
        peak = max(peak, game.player.bottom)
        airtime += 1
    return peak, airtime


def test_starts_resting_on_the_ground():
    p = flat_game().player
    assert (p.x, p.bottom, p.vy, p.mode, p.on_ground) == (0.0, 0.0, 0.0, "cube", True)


def test_horizontal_speed_is_311_58_units_per_second():
    game = flat_game()
    for _ in range(P.TICKS_PER_SECOND):
        game.tick(False)
    assert game.player.x == pytest.approx(311.58, abs=0.01)
    assert game.time == 1.0
    assert game.player.on_ground and game.player.bottom == 0.0


def test_jump_height_and_airtime_match_the_physics_doc():
    peak, airtime = jump_once(flat_game())
    assert peak == pytest.approx(64.0, abs=0.1)  # §3: 2.13 blocks; video measured 64.0 (§9)
    assert airtime == 103  # §3: 0.429 s


def test_holding_rejumps_on_landing_and_height_does_not_depend_on_hold_length():
    short_peak, airtime = jump_once(flat_game())
    game = flat_game()
    bottoms = []
    for _ in range(3 * airtime):
        game.tick(True)
        bottoms.append(game.player.bottom)
    # Holding through a whole jump gives the same height (no variable jump height for the cube)...
    assert max(bottoms[:airtime]) == pytest.approx(short_peak)
    # ...and the cube jumps again straight after landing: it's never on the ground two ticks running.
    grounded = [i for i, b in enumerate(bottoms) if b == 0.0]
    assert grounded and all(b - a > 1 for a, b in zip(grounded, grounded[1:]))


def test_released_button_never_jumps():
    game = flat_game()
    for _ in range(500):
        game.tick(False)
    assert game.player.bottom == 0.0


def test_fall_speed_is_capped():
    game = flat_game()
    game.player.y, game.player.on_ground = 5000.0, False
    for _ in range(400):
        game.tick(False)
        assert game.player.vy >= -P.MAX_FALL_SPEED
    assert game.player.vy == -P.MAX_FALL_SPEED


def test_same_inputs_give_the_same_run():
    inputs = [(i % 37) < 3 for i in range(2000)]
    runs = []
    for _ in range(2):
        game = flat_game()
        for held in inputs:
            game.tick(held)
        runs.append((game.player, game.ticks))
    assert runs[0] == runs[1]


def test_game_package_never_imports_the_brain_or_interface():
    game_dir = Path(__file__).resolve().parents[1] / "src" / "stereo_flyness" / "game"
    for path in game_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "stereo_flyness.brain" not in text and "stereo_flyness.interface" not in text, path.name
