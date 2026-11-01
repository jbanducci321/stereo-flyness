"""θ_full calibration helpers (D43), plus an end-to-end check on a tiny connectome."""

import math

import pandas as pd
import pytest

from stereo_flyness.brain.stepper import BrainStepper
from stereo_flyness.game.engine import Game
from stereo_flyness.game.player import Player
from stereo_flyness.interface.calibration import approach_level, crossing, first_spike_theta
from stereo_flyness.interface.closed_loop import play
from stereo_flyness.interface.encoding import CubeEncoder
from test_closed_loop import GF, OTHER, PATCHES, connectome  # noqa: F401 (fixture)


def test_approach_level_starts_at_the_requested_gap():
    lv = approach_level(start_gap=600)
    loom = CubeEncoder(lv, PATCHES, 180, 150).encode(Player())
    assert loom.gap == pytest.approx(600)
    assert loom.theta_deg == pytest.approx(math.degrees(2 * math.atan(15 / 600)))


def test_first_spike_theta():
    brain = pd.DataFrame({"theta_deg": [1.0, 2.0, 3.0, 4.0], "spikes_GF_R": [0, 0, 1, 1], "spikes_GF_L": [0, 0, 0, 1]})
    assert first_spike_theta(brain) == 3.0
    assert first_spike_theta(brain.assign(spikes_GF_R=0, spikes_GF_L=0)) is None


def test_crossing_interpolates_in_log_theta_full():
    assert crossing([100, 1000], [20, 60], target=40) == pytest.approx(math.sqrt(100 * 1000))
    assert crossing([100, 1000], [None, 60], target=40) is None  # nothing brackets the target
    assert crossing([100, 200, 400], [10, 30, 50], target=39) == pytest.approx(
        math.exp(math.log(200) + 0.45 * math.log(2)))


def test_larger_theta_full_fires_later(connectome):  # noqa: F811
    """End to end: a bigger θ_full drives the patch later, so the first spike comes at a larger θ."""
    out = {}
    for tf in (40, 120):
        lv = approach_level(start_gap=300)
        enc = CubeEncoder(lv, PATCHES, tf, 200)
        st = BrainStepper(*connectome, inputs={"loom": enc.ids}, watch={"GF_R": [GF], "GF_L": [], "o": [OTHER]}, seed=2)
        rec = play(Game(lv), st, enc, policy=lambda g: False, chunk_frames=60)
        assert rec.driver == "bot" and not rec.summary["completed"]  # open loop: it never jumps
        out[tf] = first_spike_theta(rec.brain)
    # With one neuron per patch, driving starts at θ = θ_full / 2
    assert out[40] >= 20 and out[120] >= 60 and out[120] > out[40]
