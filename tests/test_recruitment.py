"""Recruitment runs for the final subcircuit (D43): settings, seeds, and the recruited set."""

import numpy as np
import pytest

from stereo_flyness.experiments.recruitment import recruited_neurons, run_seed, settings
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level
from stereo_flyness.interface.fly_log import FlyRecorder

CFG = {"settings": {"calibrated_rates_hz": [25, 50, 100, 150, 200], "flat_rate_hz": 150.0,
                    "every_object_looms_rate_hz": 150.0}}


def test_the_seven_settings_of_d43_and_d45():
    s = {x.name: x for x in settings(CFG, 204.0, 1165.0)}
    assert len(s) == 7
    assert [s[f"calibrated_R{r}"].rate_hz for r in (25, 50, 100, 150, 200)] == [25, 50, 100, 150, 200]
    assert all(s[f"calibrated_R{r}"].theta_full_deg == 204 and s[f"calibrated_R{r}"].mode == "collision"
               and s[f"calibrated_R{r}"].rate_scaling for r in (25, 150))
    flat = s["preD45_flat_R150"]
    assert (flat.theta_full_deg, flat.rate_hz, flat.rate_scaling) == (1165, 150, False)
    assert (s["all_R150"].mode, s["all_R150"].theta_full_deg, s["all_R150"].rate_scaling) == ("all", 204, True)
    with pytest.raises(ValueError, match="calibrated theta_full"):
        settings(CFG, 0.0, 1165.0)
    with pytest.raises(ValueError, match="flat_theta_full"):
        settings(CFG, 204.0, 0.0)


def test_seeds_are_fixed_and_distinct():
    s = settings(CFG, 204.0, 1165.0)
    seeds = {run_seed(0, lv, x) for lv in ("cube-easy-0", "cube-easy-1") for x in s}
    assert len(seeds) == 14
    assert run_seed(0, "cube-easy-0", s[0]) == run_seed(0, "cube-easy-0", s[0])


def saved_run(tmp_path, name, frames, stuck_ids=(), driver="bot"):
    flyids = list(range(100, 110))
    game = Game(Level("flat", "test", 10000, []))
    rec = FlyRecorder(game, flyids, driver, stuck_ids=stuck_ids, window=1, stuck_share=0.5)
    for active in frames:
        counts = np.zeros(10, dtype=np.uint16)
        counts[active] = 1
        game.tick(False)
        rec.frame(game, False, {}, counts)
    rec.finish(game)
    return rec.save(tmp_path / name)


def test_recruited_set_drops_frames_from_the_stuck_flag(tmp_path):
    normal = saved_run(tmp_path, "a", [[0], [1], []])
    # Neurons 8-9 are the stuck state: the flag starts at frame 2, so neuron 7 (frame 3) is dropped
    stuck = saved_run(tmp_path, "b", [[2], [3], [8, 9], [7]], stuck_ids=[108, 109])
    ids, report = recruited_neurons([normal, stuck])
    assert ids == {100, 101, 102, 103}
    assert report == {"runs": 2, "stuck_runs": 1, "frames_used": 5, "frames_dropped": 2}


def test_only_bot_driven_runs_recruit(tmp_path):
    fly = saved_run(tmp_path, "fly", [[0]], driver="fly")
    with pytest.raises(ValueError, match="bot-driven"):
        recruited_neurons([fly])
