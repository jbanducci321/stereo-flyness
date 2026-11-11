import numpy as np
import pytest

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level
from stereo_flyness.interface.modes import ShipController
from stereo_flyness.interface.ship_encoding import ShipEncoder

DNP22 = {"DNp22_R": [901], "DNp22_L": [902]}


def neurons():
    ids = iter(range(1, 1000))
    return {t: {s: [next(ids) for _ in range(2)] for s in ("right", "left")} for t in ("T4c", "T4d", "T5c", "T5d")}


def controller(terms="self"):
    level = Level("flat", "test", 3000.0, [], start_mode="ship")
    return ShipController(ShipEncoder(level, neurons(), 150.0, terms=terms), DNP22), Game(level)


def test_any_dnp22_spike_releases_silence_holds():
    c, _ = controller()
    quiet = {"DNp22_R": np.array([0]), "DNp22_L": np.array([0])}
    assert c.output(quiet) is True
    assert c.output({**quiet, "DNp22_L": np.array([1])}) is False
    assert c.output({**quiet, "DNp22_R": np.array([2])}) is False


def test_groups_are_the_two_motion_inputs_and_it_watches_dnp22():
    c, _ = controller()
    assert set(c.groups) == {"motion_down", "motion_up"}
    assert len(c.groups["motion_down"]) == 8 and set(c.watch) == set(DNP22)


def test_encode_needs_the_game_for_floor_and_ceiling():
    c, game = controller()
    with pytest.raises(RuntimeError):
        c.encode(game.player)
    c.bind(game)
    game.player.y, game.player.vy = 150.0, 4.0  # climbing mid-area: the scene moves down
    rates, row = c.encode(game.player)
    assert row["driven_group"] == "down" and row["omega_deg"] < 0
    assert np.all(rates["motion_down"] > 0) and np.all(rates["motion_up"] == 0)


def test_settings_record_the_design():
    c, _ = controller("full")
    s = c.settings()
    assert s["terms"] == "full" and s["omega_full_deg"] == 30.0 and s["ship_rate_hz"] == 150.0


def test_dnp22_ids_are_required():
    level = Level("flat", "test", 3000.0, [], start_mode="ship")
    with pytest.raises(ValueError):
        ShipController(ShipEncoder(level, neurons(), 150.0), {})
