"""Playback logic and overlay, tested without opening a window."""

import pygame
import pytest

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox
from stereo_flyness.game.recorder import play
from stereo_flyness.viewer.playback import (
    FPS, PlaybackClock, draw_overlay, handle_key, recent_events,
)
from stereo_flyness.viewer.render import SIZE, render_frame
from stereo_flyness.viewer.timeline import Timeline


def timeline_with_spike():
    level = Level("test", "hand-made", 3000, [Box("spike", *hitbox("spike", 615, 15))])
    return Timeline(level, play(Game(level), lambda g: g.ticks == 300))


def test_clock_advances_with_speed_and_stops_when_paused():
    clock = PlaybackClock(duration=10.0)
    clock.update(0.5)
    assert clock.time == pytest.approx(0.5) and clock.tick == 120
    clock.faster()
    clock.update(1.0)
    assert clock.speed == 1.5 and clock.time == pytest.approx(2.0)
    clock.paused = True
    clock.update(5.0)
    assert clock.time == pytest.approx(2.0)


def test_clock_stays_within_the_run():
    clock = PlaybackClock(duration=3.0)
    clock.seek(-5)
    assert clock.time == 0.0
    clock.update(100)
    assert clock.time == 3.0


def test_frame_step_pauses_and_moves_one_frame():
    clock = PlaybackClock(duration=10.0, time=1.0)
    clock.step_frame(+1)
    assert clock.paused and clock.time == pytest.approx(1.0 + 1 / FPS)
    clock.step_frame(-1)
    assert clock.time == pytest.approx(1.0)


def test_speed_limits():
    clock = PlaybackClock(duration=1.0)
    for _ in range(10):
        clock.faster()
    assert clock.speed == 2.0
    for _ in range(10):
        clock.slower()
    assert clock.speed == 0.25


def test_keys():
    clock = PlaybackClock(duration=10.0, time=5.0)
    assert handle_key(clock, pygame.K_SPACE) and clock.paused
    handle_key(clock, pygame.K_LEFT)
    assert clock.time == pytest.approx(4.0)
    handle_key(clock, pygame.K_RIGHT)
    handle_key(clock, pygame.K_RIGHT)
    assert clock.time == pytest.approx(6.0)
    handle_key(clock, pygame.K_EQUALS)
    assert clock.speed == 1.5
    handle_key(clock, pygame.K_r)
    assert clock.time == 0.0 and not clock.paused
    assert handle_key(clock, pygame.K_ESCAPE) is False


def test_recent_events_show_the_jump_then_the_death():
    tl = timeline_with_spike()  # jumps too early (x ~ 390), lands, then hits the spike at 615
    jump_tick = next(t.tick for t in tl.ticks if "jump" in t.events)
    assert recent_events(tl, jump_tick + 5) == ["jump"]
    assert "jump" not in recent_events(tl, jump_tick + 100)  # the jump flash has faded (~0.35 s)
    assert tl.death_tick is not None
    assert recent_events(tl, tl.death_tick)[0] == "death"


def test_window_opens_plays_and_quits(monkeypatch):
    """Runs the real playback loop on an invisible display for a few frames."""
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    from stereo_flyness.viewer import playback

    calls = {"n": 0}
    real_get = pygame.event.get

    def fake_get():
        real_get()
        calls["n"] += 1
        return [pygame.event.Event(pygame.QUIT)] if calls["n"] >= 5 else []

    monkeypatch.setattr(pygame.event, "get", fake_get)
    playback.run_window(timeline_with_spike())
    assert calls["n"] == 5


def test_overlay_draws_headless():
    pygame.font.init()
    tl = timeline_with_spike()
    surface = pygame.Surface(SIZE)
    clock = PlaybackClock(tl.duration, time=1.3)
    render_frame(surface, tl, clock.tick)
    before = pygame.image.tobytes(surface, "RGB")
    draw_overlay(surface, tl, clock, pygame.font.SysFont("consolas", 20))
    assert pygame.image.tobytes(surface, "RGB") != before  # something was drawn on top
