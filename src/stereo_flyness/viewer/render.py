"""Drawing one moment of a run: level, player and camera.

Visuals are deliberately simple (D20: gameplay must be exact, visuals don't need to match).
Objects are drawn as their real hitboxes, so what you see is what the engine collides with.
"""

import bisect
from dataclasses import dataclass

import pygame

from stereo_flyness.game import physics as P
from stereo_flyness.game.level import Box
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
    "hazard": (255, 77, 77),
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
    """Draw the run at `tick` onto `surface`. Returns the camera used."""
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

    for box in _visible_boxes(timeline, cam):
        _draw_box(surface, cam, box)
    for portal in timeline.level.portals:
        if cam.left - 50 < portal.x < cam.right + 50:
            r = cam.rect(portal.x - P.PORTAL_WIDTH / 2, portal.y - P.PORTAL_HEIGHT / 2,
                         portal.x + P.PORTAL_WIDTH / 2, portal.y + P.PORTAL_HEIGHT / 2)
            pygame.draw.rect(surface, COLOURS[f"portal_{portal.mode}"], r, width=4, border_radius=12)

    if timeline.death_tick is not None and tick >= timeline.death_tick:
        _draw_death(surface, cam, timeline.at_tick(timeline.death_tick))
    else:
        _draw_player(surface, cam, view)
    draw_driver_label(surface, timeline)
    return cam


DRIVER_LABELS = {  # hard rule 10, D19: a replay always says who controlled the cube
    "fly": "SIMULATION REPLAY: the cube is controlled by the fly brain model",
    "bot": "BOT-DRIVEN: the bot controls the cube; the brain only watches. Not the fly playing",
}
_font = {}


def draw_driver_label(surface: pygame.Surface, timeline: Timeline) -> None:
    """Who controlled the cube, drawn on every frame of a brain run (overlay or not)."""
    label = DRIVER_LABELS.get(getattr(timeline, "driver", None))
    if label is None:
        return
    if "f" not in _font:
        pygame.font.init()
        _font["f"] = pygame.font.SysFont("consolas", 18)
    colour = COLOURS["death"] if timeline.driver == "bot" else COLOURS["ground_line"]
    text = _font["f"].render(label, True, colour)
    surface.blit(text, (16, surface.get_height() - 30))


def _visible_boxes(timeline: Timeline, cam: Camera) -> list[Box]:
    boxes = timeline.level.boxes  # sorted by x0
    if not hasattr(timeline, "_x0"):
        timeline._x0 = [b.x0 for b in boxes]
    lo = bisect.bisect_left(timeline._x0, cam.left - 30)
    hi = bisect.bisect_right(timeline._x0, cam.right)
    return [b for b in boxes[lo:hi] if b.y1 >= cam.bottom and b.y0 <= cam.bottom + cam.height / cam.scale]


def _draw_box(surface, cam: Camera, box: Box) -> None:
    r = cam.rect(box.x0, box.y0, box.x1, box.y1)
    if box.solid:
        pygame.draw.rect(surface, SOLID_COLOUR[box.kind], r)
        pygame.draw.rect(surface, COLOURS["outline"], r, width=1)
    else:
        pygame.draw.rect(surface, COLOURS["hazard"], r)


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
    """Render the run at `seconds` to an image file (no window needed)."""
    surface = pygame.Surface(size)
    render_frame(surface, timeline, timeline.at_time(seconds).tick)
    pygame.image.save(surface, str(path))
