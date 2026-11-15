"""Viewer: timeline reconstruction and headless drawing (no window needed)."""

import pygame
import pytest

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level, Portal
from stereo_flyness.game.objects import hitbox
from stereo_flyness.game.recorder import play
from stereo_flyness.viewer.render import (COLOURS, LABEL_STRIP, SCALE, SIZE, Camera, game_area, render_frame,
                                           save_still, spike_polygons)
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
    assert pixel(surface, cam.to_screen(400, 15)) == COLOURS["spike"]  # inside the triangle
    hx0, hy0, hx1, hy1 = hitbox("spike", 400, 15)
    assert pixel(surface, cam.to_screen(hx0, 15)) == COLOURS["hitbox"]  # the hitbox's faint outline
    assert pixel(surface, cam.to_screen(388, 28)) == COLOURS["background"]  # cell corner: outside the spike


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


def test_brain_runs_are_labelled_with_who_drove_the_cube():
    """Hard rule 10, D19: a bot-driven run can never look like the fly playing."""
    surface = pygame.Surface(SIZE)
    plain = make_timeline()
    render_frame(surface, plain, 0)
    strip = pygame.Rect(0, SIZE[1] - 34, 900, 30)
    before = pygame.surfarray.array3d(surface.subsurface(strip)).copy()
    for driver in ("fly", "bot"):
        tl = make_timeline()
        tl.driver = driver
        render_frame(surface, tl, 0)
        assert (pygame.surfarray.array3d(surface.subsurface(strip)) != before).any(), driver


def test_the_driver_label_has_its_own_strip_the_game_never_draws_into():
    """The label used to sit over the game's bottom edge, where the ship's floor line is."""
    surface = pygame.Surface(SIZE)
    tl = make_timeline()
    tl.driver = "fly"
    render_frame(surface, tl, 0)
    strip = pygame.surfarray.array3d(surface.subsurface((0, SIZE[1] - LABEL_STRIP, SIZE[0], LABEL_STRIP)))
    colours = {tuple(c) for c in strip.reshape(-1, 3)}
    assert tuple(COLOURS["ground"]) not in colours and tuple(COLOURS["outline"]) in colours
    assert game_area(surface, tl).get_height() == SIZE[1] - LABEL_STRIP
    assert game_area(surface, make_timeline()).get_height() == SIZE[1]  # no label, no strip


def test_spikes_fill_their_visual_cell_and_point_away_from_what_holds_them():
    ground = Box("spike", *hitbox("spike", 400, 15))
    assert spike_polygons(ground) == [[(385.0, 0.0), (415.0, 0.0), (400.0, 30.0)]]  # up, on the ground
    ceiling = [("ship", 0.0, 3000.0, (0.0, 300.0))]
    hanging = Box("spike", *hitbox("spike", 400, 285))
    assert spike_polygons(hanging, sections=ceiling) == [[(385.0, 300.0), (415.0, 300.0), (400.0, 270.0)]]
    under_block = Box("spike", *hitbox("spike", 400, 75))
    block = Box("block", *hitbox("block", 400, 105))
    assert spike_polygons(under_block, solids=[block])[0][2] == (400.0, 60.0)  # points down
    on_block = Box("spike", *hitbox("spike", 400, 45))
    low = Box("block", *hitbox("block", 400, 15))
    assert spike_polygons(on_block, solids=[low])[0][2] == (400.0, 60.0)  # points up
    side = Box("spike", *hitbox("spike", 400, 45, rotation=90))
    assert spike_polygons(side)[0][2] == (385.0, 45.0)  # turned, nothing beside it: points at the player
    wall = Box("block", *hitbox("block", 370, 45))
    assert spike_polygons(side, solids=[wall])[0][2] == (415.0, 45.0)  # held on its left: points right
    pit = Box("pit", *hitbox("pit", 400, 2))
    tris = spike_polygons(pit)
    assert len(tris) == 3 and all(y >= 0 for t in tris for _, y in t)  # clipped at the ground
