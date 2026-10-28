"""A whole level on one image, split into rows, with the bot's path drawn over it (level gallery)."""

import pygame

from stereo_flyness.game.level import Level
from stereo_flyness.game.recorder import RunLog
from stereo_flyness.viewer.render import COLOURS, SOLID_COLOUR

WIDTH = 1800
ROWS = 3
Y_RANGE = (-20.0, 320.0)  # level units shown in each row (ground-level ship area included)


def draw_overview(level: Level, run: RunLog | None = None, width: int = WIDTH, rows: int = ROWS) -> pygame.Surface:
    seg = level.length / rows
    scale = width / seg
    row_h = round((Y_RANGE[1] - Y_RANGE[0]) * scale) + 24
    surface = pygame.Surface((width, rows * row_h))
    surface.fill(COLOURS["background"])

    def to_px(x, y, row):
        return (x - row * seg) * scale, row * row_h + 18 + (Y_RANGE[1] - y) * scale

    for row in range(rows):
        _, gy = to_px(0, 0, row)
        pygame.draw.line(surface, COLOURS["ground_line"], (0, gy), (width, gy), 1)
    for mode, x0, x1, bounds in level.sections():
        if mode == "ship":
            for row in range(rows):
                a, b = max(x0, row * seg), min(x1, (row + 1) * seg)
                if a < b:
                    for yb in bounds:
                        pa, pb = to_px(a, yb, row), to_px(b, yb, row)
                        pygame.draw.line(surface, COLOURS["bounds"], pa, pb, 1)
    for box in level.boxes:
        row = min(int(box.x0 // seg), rows - 1)
        (px0, py0), (px1, py1) = to_px(box.x0, box.y1, row), to_px(box.x1, box.y0, row)
        colour = SOLID_COLOUR[box.kind] if box.solid else COLOURS["hazard"]
        pygame.draw.rect(surface, colour, pygame.Rect(round(px0), round(py0), max(1, round(px1 - px0)), max(1, round(py1 - py0))))
    for portal in level.portals:
        row = min(int(portal.x // seg), rows - 1)
        (px, py0), (_, py1) = to_px(portal.x, portal.y + 43, row), to_px(portal.x, portal.y - 43, row)
        pygame.draw.line(surface, COLOURS[f"portal_{portal.mode}"], (px, py0), (px, py1), 3)
    if run is not None:  # the bot's path, as a thin line through the player's centre
        df = run.to_frame().iloc[::8]
        points = {}
        for x, y in zip(df.x, df.y):
            row = min(int(x // seg), rows - 1)
            points.setdefault(row, []).append(to_px(x, y, row))
        for pts in points.values():
            if len(pts) > 1:
                pygame.draw.lines(surface, COLOURS["cube"], False, pts, 1)
    return surface


def save_overview(level: Level, path, run: RunLog | None = None) -> None:
    pygame.image.save(draw_overview(level, run), str(path))
