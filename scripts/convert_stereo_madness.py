"""Convert the decoded Stereo Madness data into our level format, validate it, and draw it.

Reads data/gd/stereo_madness_objects.csv (from scripts/fetch_stereo_madness.py) and writes, all
git-ignored (level design (c) RobTop Games, D9):
    data/gd/stereo_madness.json               the level in our format (D22)
    results/levels/stereo_madness_overview.svg  a picture of the whole level

Validation printed:
- object and portal counts;
- for each ship section, whether every gameplay object fits inside the floor/ceiling given by
  the ship-bounds rule (docs/game_physics.md §4) and what touches each boundary.

Stereo Madness is the held-out test (D7): look at it to check the conversion, never to tune.

Usage:
    uv run python scripts/convert_stereo_madness.py
"""

import csv
import sys
from collections import Counter
from pathlib import Path

from stereo_flyness.game.level import Box, Level, Portal
from stereo_flyness.game.objects import GD_ID_TO_KIND, GD_ID_TO_PORTAL, HAZARD_KINDS, hitbox

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "gd" / "stereo_madness_objects.csv"
OUT = ROOT / "data" / "gd" / "stereo_madness.json"
SVG = ROOT / "results" / "levels" / "stereo_madness_overview.svg"

UNITS_PER_SECOND = 311.58  # normal speed (docs/game_physics.md §1)
EPS = 0.5  # units of tolerance when comparing to boundaries


def build_level() -> Level:
    boxes, portals = [], []
    with open(SRC, newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        gd_id, x, y, rot = int(r["id"]), float(r["x"]), float(r["y"]), float(r["rotation"])
        if gd_id in GD_ID_TO_KIND:
            kind = GD_ID_TO_KIND[gd_id]
            boxes.append(Box(kind, *hitbox(kind, x, y, rot), source_id=gd_id))
        elif gd_id in GD_ID_TO_PORTAL:
            portals.append(Portal(GD_ID_TO_PORTAL[gd_id], x, y, source_id=gd_id))
    length = max(float(r["x"]) for r in rows)
    return Level("Stereo Madness", "official main-level data (D21)", length, boxes, portals)


def validate(level: Level) -> None:
    kinds = Counter(b.kind for b in level.boxes)
    print(f"Boxes: {len(level.boxes)} {dict(kinds.most_common())}")
    print(f"Portals: {len(level.portals)}; length {level.length:.0f} units (~{level.length / UNITS_PER_SECOND:.1f} s)")
    print("\nSections:")
    for mode, x0, x1, bounds in level.sections():
        t0, t1 = x0 / UNITS_PER_SECOND, x1 / UNITS_PER_SECOND
        inside = [b for b in level.boxes if b.x1 > x0 and b.x0 < x1]
        if mode == "cube":
            top = max((b.y1 for b in inside), default=0)
            print(f"  cube  {t0:5.1f}-{t1:5.1f} s  x {x0:7.0f}-{x1:7.0f}  {len(inside):4d} objects, highest top y={top:.0f}")
            continue
        floor, ceil = bounds
        print(f"  ship  {t0:5.1f}-{t1:5.1f} s  x {x0:7.0f}-{x1:7.0f}  floor y={floor:.0f} ceiling y={ceil:.0f}  {len(inside):4d} objects")
        # Where each object sits relative to the area. Objects entirely beyond a boundary are
        # out of reach (scenery, or walls of the neighbouring section).
        where = Counter()
        for b in inside:
            if b.y1 <= floor + EPS:
                where["beyond floor (unreachable)"] += 1
            elif b.y0 >= ceil - EPS:
                where["beyond ceiling (unreachable)"] += 1
            elif b.y0 < floor - EPS or b.y1 > ceil + EPS:
                where[f"straddling a boundary ({b.kind})"] += 1
            else:
                where["inside"] += 1
        print(f"        {dict(where)}")
        reach = [b for b in inside if b.y1 > floor + EPS and b.y0 < ceil - EPS]
        lining_ceil = sum(1 for b in reach if b.solid and abs(b.y1 - ceil) <= EPS)
        lining_floor = sum(1 for b in reach if b.solid and abs(b.y0 - floor) <= EPS)
        hz = [b for b in reach if b.kind in HAZARD_KINDS]
        print(f"        solids lining floor/ceiling: {lining_floor}/{lining_ceil}; reachable hazards span "
              f"y {min((b.y0 for b in hz), default=float('nan')):.1f}-{max((b.y1 for b in hz), default=float('nan')):.1f}")


def draw_svg(level: Level, path: Path, row_len: float = 6600.0, scale: float = 0.4) -> None:
    """Simple overview: rows of `row_len` units. Solids grey, hazards red, portals and ship bounds coloured."""
    y_lo, y_hi = -30.0, 600.0
    row_h = (y_hi - y_lo) * scale + 30
    n_rows = int(level.length // row_len) + 1
    width, height = row_len * scale + 20, n_rows * row_h + 10
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
           f'style="background:#14102a;font-family:sans-serif">']

    def rect(x0, y0, x1, y1, colour, row, extra=""):
        X = 10 + (x0 - row * row_len) * scale
        Y = row * row_h + 20 + (y_hi - y1) * scale
        return (f'<rect x="{X:.1f}" y="{Y:.1f}" width="{(x1 - x0) * scale:.1f}" '
                f'height="{(y1 - y0) * scale:.1f}" fill="{colour}" {extra}/>')

    for row in range(n_rows):
        rx0, rx1 = row * row_len, (row + 1) * row_len
        base = row * row_h + 20
        out.append(f'<text x="10" y="{base - 4:.0f}" fill="#bbb" font-size="12">'
                   f'x {rx0:.0f}-{rx1:.0f} ({rx0 / UNITS_PER_SECOND:.1f}-{rx1 / UNITS_PER_SECOND:.1f} s)</text>')
        out.append(rect(rx0, -30, min(rx1, level.length), 0, "#2a2350", row))  # ground
        for mode, x0, x1, bounds in level.sections():
            if mode == "ship" and x1 > rx0 and x0 < rx1:
                a, b = max(x0, rx0), min(x1, rx1)
                for yb in bounds:
                    out.append(rect(a, yb - 1.5, b, yb + 1.5, "#4aa3ff", row, 'opacity="0.8"'))
        for bx in level.boxes:
            if bx.x1 > rx0 and bx.x0 < rx1:
                colour = "#ff4d4d" if not bx.solid else ("#9a9ab0" if bx.kind == "block" else "#d8d8e8")
                out.append(rect(bx.x0, bx.y0, bx.x1, bx.y1, colour, row))
        for p in level.portals:
            if rx0 <= p.x < rx1:
                colour = "#ff4dff" if p.mode == "ship" else "#4dff88"
                out.append(rect(p.x - 2, p.y - 43, p.x + 2, p.y + 43, colour, row))
    out.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")


def main() -> int:
    if not SRC.exists():
        print("Missing data. Run: uv run python scripts/fetch_stereo_madness.py")
        return 1
    level = build_level()
    level.save(OUT)
    validate(level)
    draw_svg(level, SVG)
    print(f"\nWrote {OUT.relative_to(ROOT)} and {SVG.relative_to(ROOT)} (git-ignored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
