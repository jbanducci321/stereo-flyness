"""Drawing one moment of a run: level, player and camera.

Visuals are deliberately simple (D20: gameplay must be exact, visuals don't need to match).
Blocks and slabs are drawn as their real hitboxes. Hazards are drawn as spikes filling their
30-unit visual cell (the cell the fly's encoding sees, D47), with the smaller hitbox that
actually kills outlined on top, so the picture looks right and still shows what the engine checks.
"""

import bisect
from dataclasses import dataclass

import pygame

from stereo_flyness.game import physics as P
from stereo_flyness.game.level import Box
from stereo_flyness.game.objects import KIND_SIZES
from stereo_flyness.viewer.timeline import TickView, Timeline

SIZE = (1280, 720)
SCALE = 2.25  # screen pixels per game unit: a block is ~68 px, close to the phone recording
PLAYER_SCREEN_X = 0.3  # the player sits this far across the screen, as in GD
GROUND_SCREEN_Y = 0.8  # cube mode: the ground line sits this far down the screen

COLOURS = {
    "background": (20, 16, 42),
    "ground": (40, 34, 80),
    "ground_line": (200, 200, 230),
    "block": (150, 150, 175),
    "slab": (215, 215, 232),
    "hazard": (255, 77, 77),  # hazards in the level overview
    "hitbox": (190, 60, 75),  # the faint outline of the hitbox that kills
    "spike": (16, 12, 30),
    "spike_edge": (230, 230, 245),
    "portal_ship": (255, 77, 255),
    "portal_cube": (77, 255, 136),
    "bounds": (74, 163, 255),
    "cube": (77, 217, 255),
    "ship": (255, 184, 77),
    "outline": (10, 10, 20),
    "death": (255, 40, 40),
}
SOLID_COLOUR = {"block": COLOURS["block"], "slab": COLOURS["slab"]}


@dataclass(frozen=True)
class Camera:
    """Maps level coordinates (units, y up) to screen pixels (y down)."""

    left: float  # level x at the screen's left edge
    bottom: float  # level y at the screen's bottom edge
    width: int = SIZE[0]
    height: int = SIZE[1]
    scale: float = SCALE

    @classmethod
    def following(cls, view: TickView, size=SIZE, scale=SCALE) -> "Camera":
        w, h = size
        view_h = h / scale
        left = view.x - PLAYER_SCREEN_X * w / scale
        if view.bounds is not None:  # ship: centre the 300-unit area vertically
            floor, ceiling = view.bounds
            bottom = (floor + ceiling) / 2 - view_h / 2
        else:  # cube: ground near the bottom, rising if the player climbs high
            bottom = max(-(1 - GROUND_SCREEN_Y) * view_h, view.y - 0.6 * view_h)
        return cls(left, bottom, w, h, scale)

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        return (x - self.left) * self.scale, self.height - (y - self.bottom) * self.scale

    def rect(self, x0: float, y0: float, x1: float, y1: float) -> pygame.Rect:
        sx0, sy1 = self.to_screen(x0, y1)
        sx1, sy0 = self.to_screen(x1, y0)
        return pygame.Rect(round(sx0), round(sy1), max(1, round(sx1 - sx0)), max(1, round(sy0 - sy1)))

    @property
    def right(self) -> float:
        return self.left + self.width / self.scale


def render_frame(surface: pygame.Surface, timeline: Timeline, tick: int) -> Camera:
    """Draw the run at `tick` onto `surface`. Returns the camera used.

    Brain runs keep a strip of LABEL_STRIP pixels at the bottom for the driver label, so it never
    covers the game (the ship's floor line sits at the bottom of the view in ship sections)."""
    full, surface = surface, game_area(surface, timeline)
    view = timeline.at_tick(tick)
    cam = Camera.following(view, surface.get_size())
    surface.fill(COLOURS["background"])

    # Ground (y = 0)
    gx, gy = cam.to_screen(cam.left, 0.0)
    if gy < cam.height:
        pygame.draw.rect(surface, COLOURS["ground"], pygame.Rect(0, round(gy), cam.width, cam.height))
        pygame.draw.line(surface, COLOURS["ground_line"], (0, round(gy)), (cam.width, round(gy)), 2)

    # Ship floor/ceiling
    if view.bounds is not None:
        for yb in view.bounds:
            _, sy = cam.to_screen(0, yb)
            pygame.draw.line(surface, COLOURS["bounds"], (0, round(sy)), (cam.width, round(sy)), 3)

    visible = _visible_boxes(timeline, cam)
    solids = [b for b in visible if b.solid]
    for box in visible:
        _draw_box(surface, cam, box, solids, _sections(timeline))
    for portal in timeline.level.portals:
        if cam.left - 50 < portal.x < cam.right + 50:
            r = cam.rect(portal.x - P.PORTAL_WIDTH / 2, portal.y - P.PORTAL_HEIGHT / 2,
                         portal.x + P.PORTAL_WIDTH / 2, portal.y + P.PORTAL_HEIGHT / 2)
            pygame.draw.rect(surface, COLOURS[f"portal_{portal.mode}"], r, width=4, border_radius=12)

    if timeline.death_tick is not None and tick >= timeline.death_tick:
        _draw_death(surface, cam, timeline.at_tick(timeline.death_tick))
    else:
        _draw_player(surface, cam, view)
    draw_driver_label(full, timeline)
    return cam


DRIVER_LABELS = {  # hard rule 10, D19: a replay always says who controlled the player (cube or ship)
    "fly": "SIMULATION REPLAY: the player is controlled by the fly brain model",
    "bot": "BOT-DRIVEN: the bot controls the player; the brain only watches. Not the fly playing",
}
LABEL_STRIP = 30  # px under the game view, for the driver label only
_fonts: dict[int, pygame.font.Font] = {}


def game_area(surface: pygame.Surface, timeline: Timeline) -> pygame.Surface:
    """The part of `surface` the game is drawn in: all of it, less the label strip on brain runs."""
    if DRIVER_LABELS.get(getattr(timeline, "driver", None)) is None:
        return surface
    w, h = surface.get_size()
    return surface.subsurface((0, 0, w, h - LABEL_STRIP))


def font(size: int) -> pygame.font.Font:
    """A cached Consolas font. pygame.quit() (e.g. when a replay window closes) kills every Font
    object, so the cache asks pygame to clear it at quit and fills again on the next use."""
    if not _fonts:
        pygame.font.init()
        pygame.register_quit(_fonts.clear)
    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont("consolas", size)
    return _fonts[size]


def draw_driver_label(surface: pygame.Surface, timeline: Timeline) -> None:
    """Who controlled the player, drawn on every frame of a brain run (overlay or not), in its own
    strip at the bottom of `surface` (render_frame keeps the game out of it)."""
    label = DRIVER_LABELS.get(getattr(timeline, "driver", None))
    if label is None:
        return
    w, h = surface.get_size()
    surface.fill(COLOURS["outline"], pygame.Rect(0, h - LABEL_STRIP, w, LABEL_STRIP))
    colour = COLOURS["death"] if timeline.driver == "bot" else COLOURS["ground_line"]
    text = font(18).render(label, True, colour)
    surface.blit(text, (16, h - LABEL_STRIP + (LABEL_STRIP - text.get_height()) // 2))


def _visible_boxes(timeline: Timeline, cam: Camera) -> list[Box]:
    boxes = timeline.level.boxes  # sorted by x0
    if not hasattr(timeline, "_x0"):
        timeline._x0 = [b.x0 for b in boxes]
    lo = bisect.bisect_left(timeline._x0, cam.left - 30)
    hi = bisect.bisect_right(timeline._x0, cam.right)
    return [b for b in boxes[lo:hi] if b.y1 >= cam.bottom and b.y0 <= cam.bottom + cam.height / cam.scale]


CELL = 30.0  # a grid cell, in level units: a hazard's visual size (as interface/encoding.py)
_TOUCH = 1.0  # level units: closer than this counts as touching, for which way a spike points


def _sections(timeline: Timeline) -> list:
    if not hasattr(timeline, "_sections"):
        timeline._sections = timeline.level.sections()
    return timeline._sections


def _rotated(box: Box) -> bool:
    """True if the hitbox is the kind's size turned 90 degrees (a spike on its side)."""
    w, h = KIND_SIZES[box.kind]
    return w != h and abs(box.x1 - box.x0 - h) < 1e-6 and abs(box.y1 - box.y0 - w) < 1e-6


def spike_polygons(box: Box, solids=(), sections=()) -> list[list[tuple[float, float]]]:
    """Triangles (level coordinates) drawn for a hazard: display only, never used by the game.

    The visual cell is CELL x CELL around the hitbox centre, clipped at the ground, as the encoding
    sees it. A spike points away from what holds it: down if it hangs from a ceiling or a block's
    underside with nothing below it, sideways if its hitbox is turned (away from a block it touches;
    else towards the player), otherwise up. A pit (ground spikes) is three small spikes."""
    cx, cy = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
    x0, x1, y0, y1 = cx - CELL / 2, cx + CELL / 2, max(cy - CELL / 2, 0.0), cy + CELL / 2
    if box.kind == "pit":
        w = CELL / 3
        return [[(x0 + i * w, y0), (x0 + (i + 1) * w, y0), (x0 + (i + 0.5) * w, y1)] for i in range(3)]
    overlap_x = [s for s in solids if s.x0 < x1 - _TOUCH and s.x1 > x0 + _TOUCH]
    overlap_y = [s for s in solids if s.y0 < y1 - _TOUCH and s.y1 > y0 + _TOUCH]
    if _rotated(box):
        if any(abs(s.x1 - x0) < _TOUCH for s in overlap_y):
            return [[(x0, y0), (x0, y1), (x1, cy)]]  # held on its left: points right
        return [[(x1, y0), (x1, y1), (x0, cy)]]  # points left, at the player
    floors, ceilings = [0.0], []
    for mode, a, b, bounds in sections:
        if mode == "ship" and bounds is not None and a <= cx < b:
            floors.append(bounds[0])
            ceilings.append(bounds[1])
    floors += [s.y1 for s in overlap_x]
    ceilings += [s.y0 for s in overlap_x]
    held_above = any(abs(c - y1) < _TOUCH for c in ceilings)
    held_below = any(abs(f - y0) < _TOUCH for f in floors)
    if held_above and not held_below:
        return [[(x0, y1), (x1, y1), (cx, y0)]]  # hangs: points down
    return [[(x0, y0), (x1, y0), (cx, y1)]]


def _draw_box(surface, cam: Camera, box: Box, solids=(), sections=()) -> None:
    r = cam.rect(box.x0, box.y0, box.x1, box.y1)
    if box.solid:
        pygame.draw.rect(surface, SOLID_COLOUR[box.kind], r)
        pygame.draw.rect(surface, COLOURS["outline"], r, width=1)
        return
    for poly in spike_polygons(box, solids, sections):
        pts = [cam.to_screen(x, y) for x, y in poly]
        pygame.draw.polygon(surface, COLOURS["spike"], pts)
        pygame.draw.polygon(surface, COLOURS["spike_edge"], pts, width=2)
    pygame.draw.rect(surface, COLOURS["hitbox"], r, width=1)  # faint: the hitbox that kills


def _draw_player(surface, cam: Camera, view: TickView) -> None:
    h = P.HALF_PLAYER
    r = cam.rect(view.x - h, view.y - h, view.x + h, view.y + h)
    colour = COLOURS["ship"] if view.mode == "ship" else COLOURS["cube"]
    pygame.draw.rect(surface, colour, r)
    pygame.draw.rect(surface, COLOURS["outline"], r, width=3)
    if view.mode == "ship":  # a nose, to tell the ship apart at a glance
        pygame.draw.polygon(surface, COLOURS["outline"],
                            [(r.right, r.centery), (r.right - r.width // 3, r.top + 4),
                             (r.right - r.width // 3, r.bottom - 4)])


def _draw_death(surface, cam: Camera, view: TickView) -> None:
    sx, sy = cam.to_screen(view.x, view.y)
    d = P.HALF_PLAYER * cam.scale
    for a, b in (((-d, -d), (d, d)), ((-d, d), (d, -d))):
        pygame.draw.line(surface, COLOURS["death"], (sx + a[0], sy + a[1]), (sx + b[0], sy + b[1]), 6)


def save_still(timeline: Timeline, seconds: float, path, size=SIZE) -> None:
    """Render the run at `seconds` to an image file (no window needed), with the brain panel for brain runs."""
    from stereo_flyness.viewer.playback import draw_screen, screen_size  # playback imports this module

    surface = pygame.Surface(screen_size(timeline, size))
    draw_screen(surface, timeline, timeline.at_time(seconds).tick)
    pygame.image.save(surface, str(path))
