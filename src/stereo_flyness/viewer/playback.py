"""Live playback of a recorded run: a window at 60 fps with playback controls and an overlay.

The playback logic (`PlaybackClock`, `handle_key`, `recent_events`) is separate from the window,
so it can be tested without a display.

Controls:
    Space      pause / play        Left / Right   back / forward 1 s
    , / .      step one frame      - / +          slower / faster (0.25x-2x)
    R          restart             Esc            quit
"""

from dataclasses import dataclass

import pygame

from stereo_flyness.game import physics as P
from stereo_flyness.viewer.brain_panel import HEIGHT as PANEL_HEIGHT, draw_brain_panel
from stereo_flyness.viewer.render import COLOURS, SIZE, game_area, render_frame
from stereo_flyness.viewer.ship_panel import draw_target
from stereo_flyness.viewer.timeline import Timeline

FPS = 60
SPEEDS = (0.25, 0.5, 1.0, 1.5, 2.0)
SEEK_SECONDS = 1.0
FLASH_SECONDS = 0.35  # how long an event label stays on screen
EVENT_LABELS = {
    "jump": "JUMP",
    "land": "LAND",
    "portal_ship": "SHIP",
    "portal_cube": "CUBE",
    "death": "DEATH",
    "finish": "FINISH",
}


@dataclass
class PlaybackClock:
    """Playback position in game seconds, independent of real time and of the window."""

    duration: float
    time: float = 0.0
    speed_index: int = SPEEDS.index(1.0)
    paused: bool = False

    @property
    def speed(self) -> float:
        return SPEEDS[self.speed_index]

    def update(self, real_dt: float) -> None:
        """Advance by `real_dt` seconds of wall-clock time (scaled by speed, unless paused)."""
        if not self.paused:
            self.seek(real_dt * self.speed)

    def seek(self, delta: float) -> None:
        self.time = min(max(self.time + delta, 0.0), self.duration)

    def step_frame(self, direction: int) -> None:
        self.paused = True
        self.seek(direction / FPS)

    def faster(self) -> None:
        self.speed_index = min(self.speed_index + 1, len(SPEEDS) - 1)

    def slower(self) -> None:
        self.speed_index = max(self.speed_index - 1, 0)

    def restart(self) -> None:
        self.time, self.paused = 0.0, False

    @property
    def tick(self) -> int:
        return int(self.time * P.TICKS_PER_SECOND + 1e-9)


def handle_key(clock: PlaybackClock, key: int) -> bool:
    """Apply a key press. Returns False when the viewer should quit."""
    if key == pygame.K_ESCAPE:
        return False
    actions = {
        pygame.K_SPACE: lambda: setattr(clock, "paused", not clock.paused),
        pygame.K_LEFT: lambda: clock.seek(-SEEK_SECONDS),
        pygame.K_RIGHT: lambda: clock.seek(SEEK_SECONDS),
        pygame.K_COMMA: lambda: clock.step_frame(-1),
        pygame.K_PERIOD: lambda: clock.step_frame(+1),
        pygame.K_MINUS: clock.slower,
        pygame.K_KP_MINUS: clock.slower,
        pygame.K_EQUALS: clock.faster,
        pygame.K_PLUS: clock.faster,
        pygame.K_KP_PLUS: clock.faster,
        pygame.K_r: clock.restart,
    }
    if key in actions:
        actions[key]()
    return True


def recent_events(timeline: Timeline, tick: int, seconds: float = FLASH_SECONDS) -> list[str]:
    """Events in the last `seconds` up to `tick`, most recent first (duplicates removed)."""
    window = int(seconds * P.TICKS_PER_SECOND)
    seen, out = set(), []
    for t in range(min(tick, timeline.last_tick), max(-1, tick - window), -1):
        for e in timeline.ticks[t].events:
            if e not in seen:
                seen.add(e)
                out.append(e)
    return out


def draw_overlay(surface: pygame.Surface, timeline: Timeline, clock: PlaybackClock, font: pygame.font.Font) -> None:
    """Progress bar, time, mode, button-held indicator, event flashes and playback state."""
    w, _ = surface.get_size()
    view = timeline.at_tick(clock.tick)
    progress = min(view.x / timeline.level.length, 1.0)

    bar = pygame.Rect(w // 2 - 250, 12, 500, 14)  # progress bar, like GD's
    pygame.draw.rect(surface, COLOURS["outline"], bar, border_radius=7)
    pygame.draw.rect(surface, COLOURS["cube"], (bar.x, bar.y, round(bar.w * progress), bar.h), border_radius=7)
    pygame.draw.rect(surface, COLOURS["ground_line"], bar, width=2, border_radius=7)
    backup = (getattr(getattr(timeline, "brain", None), "run", None) or {}).get("backup_from_frame")
    if backup is not None:  # D38's backup flag needs the run's median, so it's marked here, not live
        bx = bar.x + round(bar.w * min(timeline.at_tick(backup).x / timeline.level.length, 1.0))
        pygame.draw.line(surface, COLOURS["death"], (bx, bar.y - 4), (bx, bar.bottom + 4), 3)
        surface.blit(font.render("backup flag", True, COLOURS["death"]), (bx + 4, bar.bottom + 2))

    lines = [
        f"{clock.time:6.2f} / {timeline.duration:.2f} s   {progress:5.1%}",
        f"{view.mode.upper()}   x {view.x:7.0f}   y {view.y:5.1f}",
        f"{'PAUSED' if clock.paused else 'PLAYING'}   {clock.speed:g}x",
    ]
    for i, text in enumerate(lines):
        surface.blit(font.render(text, True, COLOURS["ground_line"]), (16, 36 + 24 * i))

    # Button indicator: filled while held
    centre = (w - 40, 50)
    pygame.draw.circle(surface, COLOURS["ground_line"], centre, 16, width=2)
    if view.held:
        pygame.draw.circle(surface, COLOURS["cube"], centre, 12)

    for i, event in enumerate(recent_events(timeline, clock.tick)):
        colour = COLOURS["death"] if event == "death" else COLOURS["portal_cube"]
        surface.blit(font.render(EVENT_LABELS.get(event, event), True, colour), (w - 140, 80 + 24 * i))


def screen_size(timeline: Timeline, size=SIZE) -> tuple[int, int]:
    """The game's size, plus the brain panel's strip under it for brain runs."""
    return (size[0], size[1] + PANEL_HEIGHT) if getattr(timeline, "brain", None) is not None else tuple(size)


def draw_screen(surface: pygame.Surface, timeline: Timeline, tick: int, clock: "PlaybackClock | None" = None,
                font: "pygame.font.Font | None" = None, since: int | None = None) -> None:
    """One whole frame: the game (with the overlay if `clock` is given) and, for brain runs, the brain
    panel. `since` is the tick drawn before this one: the panel's "now" numbers sum every frame after it."""
    w, h = surface.get_size()
    brain = getattr(timeline, "brain", None)
    game = surface if brain is None else surface.subsurface((0, 0, w, h - PANEL_HEIGHT))
    cam = render_frame(game, timeline, tick)
    draw_target(game_area(game, timeline), cam, timeline, tick)  # ship B/C only: the target opening, our input
    if clock is not None:
        draw_overlay(game, timeline, clock, font)
    if brain is not None:
        draw_brain_panel(surface.subsurface((0, h - PANEL_HEIGHT, w, PANEL_HEIGHT)), brain, timeline, tick, since)


def run_window(timeline: Timeline, size=SIZE, title: str | None = None) -> None:
    """Open a window and play the run until the user quits."""
    pygame.init()
    screen = pygame.display.set_mode(screen_size(timeline, size))
    pygame.display.set_caption(title or f"stereo-flyness replay: {timeline.level.name}")
    font = pygame.font.SysFont("consolas", 20)
    clock, frame_timer = PlaybackClock(timeline.duration), pygame.time.Clock()
    drawn = None  # the tick drawn last, for the panel's bins
    running = True
    while running:
        real_dt = frame_timer.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                running = handle_key(clock, event.key) and running
        clock.update(real_dt)
        draw_screen(screen, timeline, clock.tick, clock, font, since=drawn)
        drawn = clock.tick
        pygame.display.flip()
    pygame.quit()
