"""The closed loop in any mode (interface/modes.py) on a tiny connectome.

Wiring: four "looming" neurons excite a "Giant Fiber" (as in test_closed_loop.py), and a separate
"ship input" neuron excites a "ship output" neuron. The ship controller here is a test stand-in
only: the real one is Shannyn's design (Step 5).
"""

import numpy as np
import pandas as pd
import pytest

from stereo_flyness.brain.stepper import BrainStepper
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level, Portal
from stereo_flyness.game.objects import hitbox
from stereo_flyness.interface.closed_loop import play
from stereo_flyness.interface.encoding import CubeEncoder
from stereo_flyness.interface.modes import Controller, CubeController, ShipNotDesigned, play_modes

LOOM = [101, 102, 103, 104]
GF, OTHER, SHIP_IN, SHIP_OUT = 105, 106, 107, 108
PATCHES = {"right": {"LC4": [101], "LPLC2": [102]}, "left": {"LC4": [103], "LPLC2": [104]}}
WATCH = {"GF_R": [GF], "GF_L": [], "other": [OTHER], "ship_out": [SHIP_OUT]}


@pytest.fixture
def connectome(tmp_path):
    ids = [*LOOM, GF, OTHER, SHIP_IN, SHIP_OUT]
    index = {f: i for i, f in enumerate(ids)}
    pd.DataFrame({"Completed": True}, index=pd.Index(ids)).to_csv(tmp_path / "comp.csv")
    edges = [(n, GF, 300, 1) for n in LOOM] + [(SHIP_IN, SHIP_OUT, 300, 1)]
    pd.DataFrame({
        "Presynaptic_ID": [e[0] for e in edges], "Postsynaptic_ID": [e[1] for e in edges],
        "Presynaptic_Index": [index[e[0]] for e in edges], "Postsynaptic_Index": [index[e[1]] for e in edges],
        "Connectivity": [e[2] for e in edges], "Excitatory": [e[3] for e in edges],
        "Excitatory x Connectivity": [e[2] * e[3] for e in edges],
    }).to_parquet(tmp_path / "con.parquet")
    return tmp_path / "comp.csv", tmp_path / "con.parquet"


class StandInShip(Controller):
    """Test only: drives the ship input at a fixed rate; holds while the ship output fired."""

    mode = "ship"

    def __init__(self, rate=200.0):
        self.rate = rate
        self.groups = {"ship_in": [SHIP_IN]}

    def encode(self, player):
        return {"ship_in": np.array([self.rate])}, {"ship_rate_hz": self.rate}

    def output(self, counts):
        return int(counts["ship_out"].sum()) > 0


def spike_level(length=1500):
    return Level("one spike", "test", length, [Box("spike", *hitbox("spike", 30 * 20 + 15, 15))])


def mixed_level(portal_x=600.0, length=2400.0, boxes=()):
    return Level("mixed", "test", length, list(boxes), portals=[Portal("ship", portal_x, 15.0)])


def stepper(connectome, enc, seed=3, ship=True):
    inputs = {"loom": enc.ids, **({"ship_in": [SHIP_IN]} if ship else {})}
    return BrainStepper(*connectome, inputs=inputs, watch=WATCH, seed=seed)


def test_cube_only_matches_the_cube_loop_exactly(connectome):
    """On a cube level, play_modes with the cube controller reproduces closed_loop.play run for run."""
    level = spike_level()
    enc = CubeEncoder(level, PATCHES, 78.0, 200.0)
    old = play(Game(level), stepper(connectome, enc, ship=False), enc, chunk_frames=60)
    new = play_modes(Game(level), stepper(connectome, enc, ship=False), {"cube": CubeController(enc)}, chunk_frames=60)
    assert (new.brain["mode"] == "cube").all()
    pd.testing.assert_frame_equal(old.brain, new.brain.drop(columns="mode"))
    assert old.game_log.to_frame().equals(new.game_log.to_frame())
    s_old, s_new = dict(old.summary), dict(new.summary)
    assert s_new.pop("modes") == {"cube": CubeController(enc).settings()}
    assert s_old == s_new
    assert s_new["completed"] and s_new["jumps"] >= 1


def test_switches_inputs_and_output_rule_at_the_ship_portal(connectome):
    level = mixed_level()
    enc = CubeEncoder(level, PATCHES, 78.0, 200.0)
    rec = play_modes(Game(level), stepper(connectome, enc), {"cube": CubeController(enc), "ship": StandInShip()},
                     chunk_frames=60)
    b = rec.brain
    cube, ship = b[b["mode"] == "cube"], b[b["mode"] == "ship"]
    assert len(cube) and len(ship) and (b["mode"].iloc[: len(cube)] == "cube").all()  # cube first, then ship
    # Cube part: nothing looms, so no input, no Giant Fiber spike and no press.
    assert cube["spikes_GF_R"].sum() == 0 and not cube["held"].any()
    # Ship part: the cube's input is off (its columns are blank), the ship's is on, and the ship's rule decides.
    assert ship["theta_deg"].isna().all() and (ship["ship_rate_hz"] == 200.0).all()
    assert ship["spikes_GF_R"].sum() == 0
    assert (ship["held"] == (ship["spikes_ship_out"] > 0)).all() and ship["held"].any()
    # The game got exactly the holds the ship's rule produced (frame i's decision is tick i + 1, D40).
    game = rec.game_log.to_frame()
    assert (game["held"].to_numpy() == b["held"].to_numpy()).all()
    assert game["held"].iloc[len(cube):].sum() == ship["held"].sum() > 0
    assert rec.summary["completed"] and set(rec.summary["modes"]) == {"cube", "ship"}


def test_the_cube_rule_no_longer_presses_in_ship_mode(connectome):
    """A looming-driven Giant Fiber can't hold the ship: in ship mode only the ship's rule counts."""
    level = mixed_level()
    enc = CubeEncoder(level, PATCHES, 78.0, 200.0)
    rec = play_modes(Game(level), stepper(connectome, enc), {"cube": CubeController(enc), "ship": StandInShip(rate=0.0)},
                     chunk_frames=60)
    ship = rec.brain[rec.brain["mode"] == "ship"]
    assert not ship["held"].any()  # the stand-in's input is 0 Hz, so the ship never holds


def test_ship_mode_stops_until_the_ship_is_designed(connectome):
    level = mixed_level()
    enc = CubeEncoder(level, PATCHES, 78.0, 200.0)
    with pytest.raises(NotImplementedError, match="aren't designed yet"):
        play_modes(Game(level), stepper(connectome, enc, ship=False),
                   {"cube": CubeController(enc), "ship": ShipNotDesigned()}, chunk_frames=60)


def test_bad_controller_sets_are_refused(connectome):
    level = mixed_level()
    enc = CubeEncoder(level, PATCHES, 78.0, 200.0)
    st = stepper(connectome, enc)
    with pytest.raises(ValueError):
        play_modes(Game(level), st, {"cube": ShipNotDesigned()})
    with pytest.raises(KeyError, match="no controller for mode 'ship'"):
        play_modes(Game(level), st, {"cube": CubeController(enc)}, chunk_frames=60)
