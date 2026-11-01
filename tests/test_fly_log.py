"""The run recorder's stuck-state and backup flags (D38), on made-up activity."""

import numpy as np
import pytest

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level
from stereo_flyness.interface.fly_log import FlyRecorder

N = 200
STUCK = list(range(1000, 1100))  # neurons 100-199 (FlyWire IDs 1000-1099) form the "stuck state"
FLYIDS = list(range(900, 1100))


def recorder(**kw):
    game = Game(Level("flat", "test", 100000, []))
    return game, FlyRecorder(game, FLYIDS, "fly", stuck_ids=[*STUCK, 5], **kw)  # 5 isn't in the network


def feed(game, rec, frames):
    for active in frames:
        counts = np.zeros(N, dtype=np.uint16)
        counts[active] = 1
        game.tick(False)
        rec.frame(game, False, {"theta_deg": 0.0}, counts)


def test_stuck_flag_from_the_frame_half_the_state_has_fired():
    game, rec = recorder(window=4)
    quiet = [np.array([0, 1])] * 10
    # 30 stuck-state neurons per frame: the window holds 50% after 2 frames (100 neurons, 50 needed)
    stuck = [np.arange(100 + 30 * (k % 3), 130 + 30 * (k % 3)) for k in range(6)]
    feed(game, rec, quiet + stuck)
    assert rec.settings["stuck_neurons"] == 100  # restricted to the network
    assert rec.stuck_from == 11
    assert not rec.rows[10]["stuck_flag"] and rec.rows[11]["stuck_flag"]
    assert rec.rows[10]["stuck_share"] == pytest.approx(0.3)


def test_window_forgets_old_activity():
    game, rec = recorder(window=3)
    feed(game, rec, [np.arange(100, 160)] + [np.array([], dtype=int)] * 3)
    assert [r["stuck_share"] for r in rec.rows] == pytest.approx([0.6, 0.6, 0.6, 0.0])
    assert [r["active_in_window"] for r in rec.rows] == [60, 60, 60, 0]


def test_backup_flag_needs_3x_median_and_the_floor():
    game, rec = recorder(window=1, backup_floor=50)
    feed(game, rec, [np.arange(10)] * 20 + [np.arange(80)] * 2)
    rec.finish(game)
    assert rec.backup["median_active_in_window"] == 10 and rec.backup["limit"] == 50
    assert rec.backup["from_frame"] == 20 and rec.backup["frames"] == 2
    game, rec = recorder(window=1, backup_floor=100)
    feed(game, rec, [np.arange(10)] * 20 + [np.arange(80)] * 2)
    rec.finish(game)
    assert rec.backup["from_frame"] is None



def test_backup_count_leaves_out_stimulated_neurons():
    game, rec = recorder(window=1, backup_floor=50, stimulated_ids=range(900, 970))  # neurons 0-69
    feed(game, rec, [np.arange(10)] * 20 + [np.arange(80)] * 2)
    rec.finish(game)
    assert rec.settings["stimulated_neurons_excluded"] == 70
    assert [r["active_in_window"] for r in rec.rows[-3:]] == [0, 10, 10]
    assert rec.backup["from_frame"] is None  # only 10 of the 80 aren't ours
    assert rec.rows[-1]["active_neurons"] == 80  # the raw count is still logged

def test_driver_must_be_fly_or_bot():
    with pytest.raises(ValueError, match="driver"):
        FlyRecorder(Game(Level("x", "t", 100, [])), FLYIDS, "human")
