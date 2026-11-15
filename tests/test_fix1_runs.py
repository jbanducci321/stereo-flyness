"""Fix 1 in fly runs (iteration 2): the controller logs and labels it; iteration-1 runs are unchanged."""

import numpy as np
import pygame

from test_viewer_brain_panel import mixed_run

from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox
from stereo_flyness.game.player import Player
from stereo_flyness.interface.encoding import CubeEncoder
from stereo_flyness.interface.modes import CubeController
from stereo_flyness.viewer.playback import draw_screen, screen_size
from stereo_flyness.viewer.timeline import Timeline

NO_PATCHES = {s: {t: [] for t in ("LC4", "LPLC2")} for s in ("right", "left")}


def _platform_then_pits():
    objs = [("block", 600 + 30 * i + 15, 15) for i in range(6)] + [("pit", 780 + 30 * i + 15, 2) for i in range(3)]
    return Level("t", "test", 2000.0, [Box(k, *hitbox(k, x, y)) for k, x, y in objs])


def test_iteration1_runs_log_and_record_exactly_what_they_did():
    ctrl = CubeController(CubeEncoder(_platform_then_pits(), NO_PATCHES, 200.0, 150.0, rate_scaling=True))
    _, row = ctrl.encode(Player(x=740.0, y=45.0, on_ground=True))
    assert "predicted" not in row
    assert set(ctrl.settings()) == {"theta_full_deg", "rate_hz", "mode", "rate_scaling"}


def test_fix1_runs_flag_predicted_frames_and_record_their_encoding():
    enc = CubeEncoder(_platform_then_pits(), NO_PATCHES, 200.0, 150.0, rate_scaling=True, path="no_press")
    ctrl = CubeController(enc)
    _, on_platform = ctrl.encode(Player(x=740.0, y=45.0, on_ground=True))
    _, on_floor = ctrl.encode(Player(x=300.0, y=15.0, on_ground=True))
    assert on_platform["predicted"] is True and on_floor["predicted"] is False
    assert ctrl.settings()["path"] == "no_press" and ctrl.settings()["view"] == "landing"


def test_the_replay_labels_predicted_frames():
    level, log, track = mixed_run()
    plain = Timeline(level, log, driver="fly", brain=track)
    a = pygame.Surface(screen_size(plain))
    draw_screen(a, plain, 50)
    track.brain["predicted"] = np.ones(len(track.brain), bool)
    track.run["view"] = "landing"
    b = pygame.Surface(screen_size(plain))
    draw_screen(b, plain, 50)
    assert pygame.image.tobytes(a, "RGB") != pygame.image.tobytes(b, "RGB")  # the label is drawn
