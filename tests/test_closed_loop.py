"""The cube closed loop (D40-D42) on a tiny connectome: four "looming" neurons excite a "Giant Fiber"."""

import numpy as np
import pandas as pd
import pytest

from stereo_flyness.brain.stepper import BrainStepper
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox
from stereo_flyness.interface.closed_loop import jump_rule, play
from stereo_flyness.interface.encoding import CubeEncoder

LOOM = [101, 102, 103, 104]
GF, OTHER = 105, 106
PATCHES = {"right": {"LC4": [101], "LPLC2": [102]}, "left": {"LC4": [103], "LPLC2": [104]}}


@pytest.fixture
def connectome(tmp_path):
    ids = [*LOOM, GF, OTHER]
    index = {f: i for i, f in enumerate(ids)}
    pd.DataFrame({"Completed": True}, index=pd.Index(ids)).to_csv(tmp_path / "comp.csv")
    edges = [(n, GF, 300, 1) for n in LOOM]
    pd.DataFrame({
        "Presynaptic_ID": [e[0] for e in edges], "Postsynaptic_ID": [e[1] for e in edges],
        "Presynaptic_Index": [index[e[0]] for e in edges], "Postsynaptic_Index": [index[e[1]] for e in edges],
        "Connectivity": [e[2] for e in edges], "Excitatory": [e[3] for e in edges],
        "Excitatory x Connectivity": [e[2] * e[3] for e in edges],
    }).to_parquet(tmp_path / "con.parquet")
    return tmp_path / "comp.csv", tmp_path / "con.parquet"


def spike_level(col=20, length=1500):
    return Level("one spike", "test", length, [Box("spike", *hitbox("spike", 30 * col + 15, 15))])


def run(connectome, level, theta_full=78.0, rate=200.0, seed=3):
    """theta_full = 78: with one neuron per patch, the patch switches on at 39 deg (D43)."""
    enc = CubeEncoder(level, PATCHES, theta_full, rate)
    st = BrainStepper(*connectome, inputs={"loom": enc.ids}, watch={"GF_R": [GF], "GF_L": [], "other": [OTHER]},
                      seed=seed)
    return play(Game(level), st, enc, chunk_frames=60), st


def test_jump_rule():
    one = {"GF_R": np.array([0]), "GF_L": np.array([1])}
    none = {"GF_R": np.array([0]), "GF_L": np.array([0])}
    assert jump_rule(one) and not jump_rule(none)


def test_the_fly_jumps_the_spike(connectome):
    result, st = run(connectome, spike_level())
    ticks = pd.DataFrame(result.ticks)
    s = result.summary
    assert s["driver"] == "fly" and s["completed"] and s["jumps"] >= 1
    # Every row's tick is the state the brain saw; rows are consecutive
    assert list(ticks["tick"]) == list(range(len(ticks)))
    # Input only while the spike looms, and none once it's behind the eye
    assert (ticks.loc[ticks["theta_deg"] == 0, ["driven_right_LC4", "driven_left_LPLC2"]] == 0).all().all()
    # Brain time equals game time exactly (D40): 240 frames per second
    assert float(st.t / (1000 / 240 * 1e-3)) == pytest.approx(np.ceil(len(ticks) / 60) * 60, abs=1e-6)


def test_press_follows_the_spike_by_one_tick(connectome):
    """D40/D42: Giant Fiber spikes in frame i set `held` for the game tick that follows frame i."""
    result, _ = run(connectome, spike_level())
    ticks = pd.DataFrame(result.ticks)
    assert (ticks["held"] == ((ticks["spikes_GF_R"] + ticks["spikes_GF_L"]) > 0)).all()
    jump = ticks.index[ticks["events"].str.contains("jump")][0]
    assert ticks.loc[jump, "held"] and ticks.loc[jump, "spikes_GF_R"] > 0


def test_no_input_no_press(connectome):
    """Nothing looms, so nothing is driven and the Giant Fiber never fires (D30)."""
    empty = Level("empty", "test", 600, [])
    result, _ = run(connectome, empty)
    ticks = pd.DataFrame(result.ticks)
    assert result.summary["completed"] and result.summary["presses"] == 0
    assert ticks["spikes_GF_R"].sum() == 0 and ticks["active_neurons"].sum() == 0


def test_a_silent_fly_dies_on_the_spike(connectome):
    """With the patch never driven (theta_full huge, R = 0), the cube runs into the spike."""
    result, _ = run(connectome, spike_level(), theta_full=1e9, rate=0.0)
    assert not result.summary["completed"] and result.summary["death"]["kind"] == "spike"
    assert result.summary["presses"] == 0
