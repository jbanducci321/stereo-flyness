"""Viewer: the brain panel (D19, R2) on a mixed cube/ship run, headless."""

import numpy as np
import pandas as pd
import pygame

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level, Portal
from stereo_flyness.game.recorder import play
from stereo_flyness.viewer.brain_panel import HEIGHT, WINDOW_TICKS, BrainTrack
from stereo_flyness.viewer.playback import draw_screen, screen_size
from stereo_flyness.viewer.render import SIZE, save_still
from stereo_flyness.viewer.timeline import Timeline


def mixed_run():
    """A game run through a ship portal, and a brain log shaped like play_modes' (cube columns blank in ship)."""
    level = Level("mixed", "test", 1500, [], [Portal("ship", 300, 45)])
    log = play(Game(level), lambda g: g.ticks % 50 < 10)
    tl = Timeline(level, log)
    modes = [t.mode for t in tl.ticks[:-1]]  # brain row k saw the game after k ticks
    n = len(modes)
    rng = np.random.default_rng(0)
    cube = np.array([m == "cube" for m in modes])
    brain = pd.DataFrame({
        "frame": np.arange(n), "tick_seen": np.arange(n), "mode": modes,
        "theta_deg": np.where(cube, 12.5, np.nan), "gap": np.where(cube, 40.0, np.nan),
        "f": np.where(cube, 0.5, np.nan), "rate_hz": np.where(cube, 75.0, np.nan),
        "ship_rate_hz": np.where(cube, np.nan, 200.0),
        "spikes_GF_R": rng.integers(0, 3, n), "spikes_ship_out": np.where(cube, 0, rng.integers(0, 2, n)),
        "fly_press": rng.random(n) < 0.1, "held": np.zeros(n, bool), "active_neurons": rng.integers(0, 500, n),
        "active_in_window": np.zeros(n), "stuck_share": np.zeros(n), "stuck_flag": np.zeros(n, bool),
    })
    return level, log, brain


def test_inputs_follow_the_mode_shown():
    level, log, brain = mixed_run()
    track = BrainTrack(brain)
    cube_tick = int(np.flatnonzero(brain["mode"] == "cube")[0])
    ship_tick = int(np.flatnonzero(brain["mode"] == "ship")[0])
    cube = dict(track.input_items(cube_tick))
    ship = dict(track.input_items(ship_tick))
    assert cube["θ"] == "12.5°" and "ship_rate_hz" not in cube
    assert ship["ship_rate_hz"] == "200.0" and "θ" not in ship
    assert set(track.groups) == {"GF_R", "ship_out"}
    assert "fly_press" not in track.inputs and "active_neurons" not in track.inputs


def test_spike_lanes_are_the_recorded_counts_unaltered():
    _, _, brain = mixed_run()
    track = BrainTrack(brain)
    t = 500
    window = track.spike_window("GF_R", t)
    assert len(window) == WINDOW_TICKS
    assert np.array_equal(window, brain["spikes_GF_R"].to_numpy()[t + 1 - WINDOW_TICKS:t + 1])
    early = track.spike_window("GF_R", 3)  # before a full second: zeros, then the run's first frames
    assert np.array_equal(early[-4:], brain["spikes_GF_R"].to_numpy()[:4]) and not early[:-4].any()
    assert track.row(10**9) == len(brain) - 1


def test_old_cube_logs_without_a_mode_column_still_load():
    _, _, brain = mixed_run()
    track = BrainTrack(brain.drop(columns="mode"))
    assert (track.brain["mode"] == "cube").all()


def test_panel_is_drawn_under_the_game_for_brain_runs(tmp_path):
    level, log, brain = mixed_run()
    plain = Timeline(level, log, driver="fly")
    with_brain = Timeline(level, log, driver="fly", brain=BrainTrack(brain))
    assert screen_size(plain) == SIZE and screen_size(with_brain) == (SIZE[0], SIZE[1] + HEIGHT)
    ship_tick = int(np.flatnonzero(brain["mode"] == "ship")[0]) + 50
    a, b = pygame.Surface(screen_size(plain)), pygame.Surface(screen_size(with_brain))
    draw_screen(a, plain, ship_tick)
    draw_screen(b, with_brain, ship_tick)
    # The game part is drawn exactly as without the panel.
    assert pygame.image.tobytes(a, "RGB") == pygame.image.tobytes(b.subsurface((0, 0, *SIZE)), "RGB")
    out = tmp_path / "still.png"
    save_still(with_brain, ship_tick / 240, out)
    assert pygame.image.load(str(out)).get_size() == (SIZE[0], SIZE[1] + HEIGHT)
