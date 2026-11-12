import numpy as np
import pandas as pd

from stereo_flyness.experiments.mixed_check import (
    encoding_mismatches, input_rates, mode_mismatches, rule_mismatches, shown_modes)
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level, Portal


def portal_level():
    return Level("mixed", "test", 1500.0, [], portals=[Portal("ship", 600.0, 15.0)])


def logged(level):
    """Holds of a player that never presses, and the brain rows play_modes would log for them."""
    game, held, rows = Game(level), [], []
    h = False
    while not game.over:
        mode = game.player.mode
        rows.append({"tick_seen": game.ticks, "mode": mode,
                     "theta_deg": 10.0 if mode == "cube" else np.nan, "omega_deg": np.nan if mode == "cube" else 5.0,
                     "spikes_GF_R": 0, "spikes_GF_L": 0, "spikes_DNp22_R": 1 if mode == "ship" else 0,
                     "spikes_DNp22_L": 0, "fly_press": False})
        game.tick(h)
        held.append(h)
    return held, pd.DataFrame(rows)


def test_a_correct_log_has_no_mismatches():
    level = portal_level()
    held, brain = logged(level)
    assert set(brain["mode"]) == {"cube", "ship"}
    assert mode_mismatches(level, held, brain) == 0
    assert rule_mismatches(brain) == 0
    assert encoding_mismatches(brain) == 0


def test_a_wrong_mode_label_is_caught():
    level = portal_level()
    held, brain = logged(level)
    first_ship = int((brain["mode"] == "ship").idxmax())
    brain.loc[first_ship, "mode"] = "cube"
    assert mode_mismatches(level, held, brain) == 1


def test_the_wrong_rule_is_caught():
    _, brain = logged(portal_level())
    ship = brain["mode"] == "ship"
    brain.loc[ship, "fly_press"] = True  # pressed although DNp22 spiked: the cube's rule, or none
    assert rule_mismatches(brain) == int(ship.sum())


def test_a_ship_row_with_cube_fields_is_caught():
    _, brain = logged(portal_level())
    i = int((brain["mode"] == "ship").idxmax())
    brain.loc[i, "theta_deg"] = 3.0
    assert encoding_mismatches(brain) == 1


def test_input_rates_split_by_shown_mode():
    modes = ["cube"] * 4 + ["ship"] * 4
    spikes = {"flyids": np.array([10, 20]), "frame": np.array([0, 1, 5]), "neuron": np.array([0, 0, 1]),
              "count": np.array([1, 1, 2])}
    r = input_rates(spikes, modes, {"cube": [10], "ship": [20]})
    assert r["cube"]["shown"] == 2 / 4 * 240 and r["cube"]["not shown"] == 0
    assert r["ship"]["shown"] == 2 / 4 * 240 and r["ship"]["not shown"] == 0


def test_shown_modes_follows_the_portal():
    level = portal_level()
    held, _ = logged(level)
    modes = shown_modes(level, held)
    assert modes[0] == "cube" and modes[-1] == "ship"
