"""Viewer: the brain panel's ship mode (D53; docs/notes/brain_panel_design.md "Ship mode"), headless."""

import numpy as np
import pandas as pd
import pygame
import pytest

from stereo_flyness.experiments.ship_baseline import ideal_encoder, ideal_holds
from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.recorder import play
from stereo_flyness.viewer.brain_panel import BrainTrack
from stereo_flyness.viewer.playback import draw_screen, screen_size
from stereo_flyness.viewer.ship_panel import (
    TargetMismatch, group_counts, ids, ship_neurons, ship_targets, variant_tag)
from stereo_flyness.viewer.timeline import Timeline


def test_the_neuron_table_has_one_vs_dnp20_and_dnp22_per_side_and_no_duplicates():
    t = ship_neurons()
    assert not t["flywire_id"].duplicated().any()
    for ty in [f"VS{i}" for i in range(1, 9)] + ["DNp20", "DNp22"]:
        for s in ("left", "right"):
            assert len(ids(ty, side=s)) == 1, (ty, s)
    counts = group_counts()
    assert set(counts) == {(g, s) for g in ("down", "up") for s in ("left", "right")}
    assert all(n > 500 for n in counts.values())


@pytest.mark.parametrize("run, tag", [
    ({"ship_design": "B", "modes": {"ship": {"omega_full_deg": 30.0}}}, "B"),
    ({"ship_design": "C"}, "C"),
    ({"ship_design": "B90", "modes": {"ship": {"omega_full_deg": 90.0}}}, "B90"),
    ({"ship_design": "B", "signs": "corrected"}, "B, corrected signs"),
])
def test_variant_tags(run, tag):
    assert variant_tag(run) == tag


def wall_level():
    boxes = [Box("block", x0, y, x0 + 30.0, y + 30.0) for x0 in (600.0, 1200.0)
             for y in range(0, 300, 30) if not 120 <= y < 210]
    return Level("walls", "test", 1800.0, boxes, start_mode="ship")


def ship_run(level):
    """The ideal B ship's game, logged as play_modes would (row k: the state after k ticks)."""
    enc = ideal_encoder(level, "B")
    policy = lambda g: ideal_holds(enc, g)  # noqa: E731
    game, rows = Game(level), []
    while not game.over:  # the same order as recorder.play, so both games are the same game
        m = enc.encode(game.player, game.bounds)
        held = bool(policy(game))
        dn = 0 if held else 1  # a spike releases, silence holds
        rows.append({"frame": game.ticks, "tick_seen": game.ticks, "mode": "ship", "omega_deg": m.omega_deg,
                     "f": m.f, "rate_hz": m.rate_hz, "driven_group": m.group or "none", "vy": m.vy,
                     "target_dy": m.target_dy, "target_dx": m.dx, "v_req": m.v_req,
                     "spikes_DNp22_R": dn, "spikes_DNp22_L": dn, "fly_press": held, "held": held})
        game.tick(held)
    log = play(Game(level), policy)
    brain = pd.DataFrame(rows).astype({"target_dy": float, "target_dx": float})
    return log, brain


def test_targets_are_recomputed_and_match_the_log():
    level = wall_level()
    log, brain = ship_run(level)
    tl = Timeline(level, log)
    targets = ship_targets(level, tl, brain)
    assert len(targets) == int(brain["target_dy"].notna().sum()) > 0
    o = next(iter(targets.values()))
    assert (o.bottom, o.top) == (120.0, 210.0)


def test_a_target_that_differs_from_the_log_fails_loudly():
    level = wall_level()
    log, brain = ship_run(level)
    k = int(brain["target_dy"].first_valid_index())
    brain.loc[k, "target_dy"] += 0.01
    with pytest.raises(TargetMismatch):
        ship_targets(level, Timeline(level, log), brain)


def test_a_ship_run_draws_with_the_ship_columns():
    level = wall_level()
    log, brain = ship_run(level)
    run = {"driver": "fly", "ship_design": "B", "modes": {"ship": {"ship_rate_hz": 150.0, "omega_full_deg": 30.0,
                                                                   "terms": "B", "eyes": ["left", "right"]}}}
    track = BrainTrack(brain, None, run)
    tl = Timeline(level, log, driver="fly", brain=track)
    assert track.targets
    surface = pygame.Surface(screen_size(tl))
    draw_screen(surface, tl, next(iter(track.targets)) + 5)
    panel = pygame.surfarray.array3d(surface)[:, -200:]
    assert (np.abs(panel - np.array([255, 176, 46])).sum(axis=2) == 0).any()  # DNp22 spikes in amber
