"""Viewer: timeline reconstruction and headless drawing (no window needed)."""

import pygame
import pytest

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level, Portal
from stereo_flyness.game.objects import hitbox
from stereo_flyness.game.recorder import play
from stereo_flyness.viewer.render import COLOURS, SCALE, SIZE, Camera, render_frame, save_still
from stereo_flyness.viewer.timeline import Timeline


def make_timeline(boxes=(), portals=(), policy=lambda g: False, length=3000):
    level = Level("test", "hand-made", length, list(boxes), list(portals))
    return Timeline(level, play(Game(level), policy))


def pixel(surface, xy):
    return tuple(surface.get_at((round(xy[0]), round(xy[1]))))[:3]


def test_timeline_starts_at_the_start_and_matches_the_log():
    tl = make_timeline(length=600)
    assert (tl.ticks[0].x, tl.ticks[0].y, tl.ticks[0].mode) == (0.0, 15.0, "cube")
    assert tl.last_tick == tl.summary.ticks and len(tl.ticks) == tl.last_tick + 1
    assert tl.at_time(1.0).tick == 240 and tl.at_tick(10_000).tick == tl.last_tick


def test_timeline_rebuilds_ship_bounds_from_portal_events():
    tl = make_timeline(portals=[Portal("ship", 300, 45), Portal("cube", 900, 45)],
                       policy=lambda g: False, length=1500)
    modes = {t.mode: t.bounds for t in tl.ticks}
    assert modes["ship"] == (0, 300) and modes["cube"] is None


def test_camera_places_the_player_and_ground():
    tl = make_timeline(length=600)
    view = tl.at_tick(120)
    cam = Camera.following(view)
    sx, sy = cam.to_screen(view.x, view.y)
    assert sx == pytest.approx(0.3 * SIZE[0]) and 0 < sy < SIZE[1]
    _, ground_y = cam.to_screen(0, 0)
    assert ground_y == pytest.approx(0.8 * SIZE[1])
    assert cam.to_screen(view.x + 30, view.y)[0] - sx == pytest.approx(30 * SCALE)


def test_render_draws_player_blocks_and_hazards():
    block, spike = Box("block", *hitbox("block", 520, 15)), Box("spike", *hitbox("spike", 400, 15))
    tl = make_timeline(boxes=[spike, block], policy=lambda g: g.ticks == 200, length=900)
    surface = pygame.Surface(SIZE)
    tick = 150  # the player is at x ~ 195; the screen shows x ~ 25 to 594
    cam = render_frame(surface, tl, tick)
    view = tl.at_tick(tick)
    assert pixel(surface, cam.to_screen(view.x, view.y)) == COLOURS["cube"]
    assert pixel(surface, cam.to_screen(520, 15)) == COLOURS["block"]
    assert pixel(surface, cam.to_screen(400, 15)) == COLOURS["hazard"]


def test_death_is_drawn_after_it_happens():
    tl = make_timeline(boxes=[Box("spike", *hitbox("spike", 400, 15))])
    assert tl.death_tick is not None
    surface = pygame.Surface(SIZE)
    cam = render_frame(surface, tl, tl.death_tick)
    death = tl.at_tick(tl.death_tick)
    assert pixel(surface, cam.to_screen(death.x, death.y)) == COLOURS["death"]


def test_save_still_writes_an_image(tmp_path):
    tl = make_timeline(length=600)
    save_still(tl, 1.0, tmp_path / "still.png")
    img = pygame.image.load(str(tmp_path / "still.png"))
    assert img.get_size() == SIZE
