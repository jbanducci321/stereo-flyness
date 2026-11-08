"""Viewer: the brain panel (R3 v1, docs/notes/brain_panel_design.md), headless."""

import numpy as np
import pandas as pd
import pygame

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Level, Portal
from stereo_flyness.game.recorder import play
from stereo_flyness.viewer.brain_panel import BIN_TICKS, HEIGHT, RASTER_TICKS, BrainTrack, loom_counts, loom_ids
from stereo_flyness.viewer.playback import draw_screen, screen_size
from stereo_flyness.viewer.render import SIZE, save_still
from stereo_flyness.viewer.timeline import Timeline

STIM = loom_ids()[:3]  # three of our driven neurons
OTHER = np.array([11, 12, 13], np.int64)  # neurons we don't drive


def mixed_run(stuck_from=None):
    """A game through a ship portal, a brain log shaped like play_modes' (cube columns blank in ship),
    and a sparse spike record where both driven and other neurons fire."""
    level = Level("mixed", "test", 1500, [], [Portal("ship", 300, 45)])
    log = play(Game(level), lambda g: g.ticks % 50 < 10)
    tl = Timeline(level, log)
    modes = [t.mode for t in tl.ticks[:-1]]  # brain row k saw the game after k ticks
    n = len(modes)
    rng = np.random.default_rng(0)
    cube = np.array([m == "cube" for m in modes])
    stuck = np.zeros(n, bool)
    if stuck_from is not None:
        stuck[stuck_from:stuck_from + 5] = True  # the flag can go off again; the banner stays
    brain = pd.DataFrame({
        "frame": np.arange(n), "tick_seen": np.arange(n), "mode": modes,
        "theta_deg": np.where(cube, 12.5, np.nan), "gap": np.where(cube, 40.0, np.nan),
        "f": np.where(cube, 0.25, np.nan), "rate_hz": np.where(cube, 37.5, np.nan),
        **{f"driven_{s}_{t}": np.where(cube, 5, np.nan) for s in ("left", "right") for t in ("LC4", "LPLC2")},
        "ship_rate_hz": np.where(cube, np.nan, 200.0),
        "spikes_GF_R": rng.integers(0, 3, n), "spikes_GF_L": rng.integers(0, 2, n),
        "spikes_ship_out": np.where(cube, 0, rng.integers(0, 2, n)),
        "fly_press": rng.random(n) < 0.1, "held": np.zeros(n, bool), "active_neurons": np.zeros(n, int),
        "active_in_window": np.zeros(n), "stuck_share": np.where(stuck, 0.8, 0.02), "stuck_flag": stuck,
    })
    flyids = np.concatenate([STIM, OTHER])
    frames, neurons = [], []
    for k in range(n):  # frame k: every driven neuron, plus (k % 3) of the others
        for i in list(range(3)) + [3 + j for j in range(k % 3)]:
            frames.append(k)
            neurons.append(i)
    spikes = {"flyids": flyids, "frame": np.array(frames, np.int32), "neuron": np.array(neurons, np.int32),
              "count": np.ones(len(frames), np.uint16), "stimulated": STIM}
    run = {"rate_hz": 150.0, "backup_from_frame": None}
    return level, log, BrainTrack(brain, spikes, run)


def test_inputs_follow_the_mode_shown():
    _, _, track = mixed_run()
    b = track.brain
    cube = dict(track.input_items(int(np.flatnonzero(b["mode"] == "cube")[0])))
    ship = dict(track.input_items(int(np.flatnonzero(b["mode"] == "ship")[0])))
    assert cube["theta_deg"] == "12.5" and "ship_rate_hz" not in cube
    assert ship["ship_rate_hz"] == "200.0" and "theta_deg" not in ship
    assert track.gf == ["GF_L", "GF_R"] and track.others == ["ship_out"]
    assert "fly_press" not in track.inputs and "active_neurons" not in track.inputs


def test_rasters_are_the_recorded_counts_unaltered():
    _, _, track = mixed_run()
    t = 500
    window = track.spike_window("GF_R", t)
    assert len(window) == RASTER_TICKS
    assert np.array_equal(window, track.brain["spikes_GF_R"].to_numpy()[t + 1 - RASTER_TICKS:t + 1])
    early = track.spike_window("GF_R", 3)  # before a full second: zeros, then the run's first frames
    assert np.array_equal(early[-4:], track.brain["spikes_GF_R"].to_numpy()[:4]) and not early[:-4].any()


def test_bins_drop_no_spike():
    """Video draws every 4th tick; the bins tile the run, so every spike is counted exactly once."""
    _, _, track = mixed_run()
    gf = track.brain["spikes_GF_R"].to_numpy()
    assert track.bin_spikes("GF_R", 100) == gf[97:101].sum()  # default: the last 4 ticks
    assert track.bin_spikes("GF_R", 100, since=90) == gf[91:101].sum()  # the live window: since the last drawn
    drawn, total = None, 0
    for tick in range(0, len(track), BIN_TICKS):
        total += track.bin_spikes("GF_R", tick, since=drawn)
        drawn = tick
    last = (len(track) - 1) // BIN_TICKS * BIN_TICKS
    assert total == gf[:last + 1].sum()
    assert track.bin_spikes("GF_R", 0) == gf[0]  # the first frame: nothing before the run


def test_active_neurons_leave_out_what_we_stimulate():
    _, _, track = mixed_run()
    assert list(track.active[:6]) == [0, 1, 2, 0, 1, 2]  # the 3 driven neurons fire every frame, never counted
    assert track.bin_active(5) == 2 and track.active_note == ""  # frames 2-5: distinct others 11, 12


def test_old_runs_fall_back_to_the_cube_inputs_and_say_so_if_unsure():
    _, _, track = mixed_run()
    old = {k: v for k, v in track.spikes.items() if k != "stimulated"}
    ok = BrainTrack(track.brain, old, {"flags": {"stimulated_neurons_excluded": 3}})  # LC4/LPLC2 in this net: 3
    assert list(ok.active[:3]) == [0, 1, 2] and ok.active_note == ""
    unsure = BrainTrack(track.brain, old, {"flags": {"stimulated_neurons_excluded": 99}})
    assert list(unsure.active[:3]) == [3, 4, 5] and "raw" in unsure.active_note
    assert (BrainTrack(track.brain.drop(columns="mode")).brain["mode"] == "cube").all()


def test_eye_rows_match_the_v783_counts():
    assert loom_counts() == {("left", "LC4"): 54, ("left", "LPLC2"): 108, ("right", "LC4"): 50, ("right", "LPLC2"): 102}


def test_panel_is_drawn_under_the_game_and_the_banner_stays(tmp_path):
    level, log, track = mixed_run(stuck_from=200)
    plain = Timeline(level, log, driver="fly")
    tl = Timeline(level, log, driver="fly", brain=track)
    assert screen_size(plain) == SIZE and screen_size(tl) == (SIZE[0], SIZE[1] + HEIGHT)
    a, b = pygame.Surface(screen_size(plain)), pygame.Surface(screen_size(tl))
    for tick in (50, 150, 400):  # cube, before and after the stuck flag (ship mode by 400)
        draw_screen(a, plain, tick)
        draw_screen(b, tl, tick)
        assert pygame.image.tobytes(a, "RGB") == pygame.image.tobytes(b.subsurface((0, 0, *SIZE)), "RGB")
    assert not track.stuck_since(150) and track.stuck_since(400)  # flag was on 200-204 only
    banner_row = SIZE[1] + HEIGHT // 2
    colours = {tuple(b.get_at((x, banner_row)))[:3] for x in range(0, SIZE[0], 7)}
    assert (60, 10, 10) in colours  # the striped banner is drawn
    out = tmp_path / "still.png"
    save_still(tl, 1.0, out)
    assert pygame.image.load(str(out)).get_size() == (SIZE[0], SIZE[1] + HEIGHT)
