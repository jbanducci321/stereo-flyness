"""Obstacle groups in a cube level, for per-obstacle results (iteration 2, fix 2's threshold check).

A level's objects are split into **groups**: runs of occupied grid columns with fewer than
`SPLIT_COLUMNS` empty columns between them. Generated levels leave at least 4 empty columns between
chunks (the shortest gap, 0.4 s, is ~125 units) and at most 3 inside one (a staircase), so each
group is one generator chunk. Each group gets a type from its shape alone, not from the generator,
so the same code labels any cube level:

- `spike1`, `spike2`, `spike3`: adjacent ground spikes;
- `spaced_pair (gap g)` / `spaced_pair (gap g, block)`: a spike, g empty cells, then a spike or block;
- `block`: one ground block;
- `platform` / `platform+spike`: a 1-high raised run of blocks, maybe with a spike on top;
- `stairs (w-wide)`: rising steps w columns wide;
- `slab_bridge`: ground pits under a continuous slab walkway;
- `slab_hops`: ground pits with separate slab platforms to hop between;
- anything else is `other: ...` with a short description.

This only reads levels. It never changes how levels are made.
"""

from dataclasses import dataclass

from stereo_flyness.game.level import Box, Level

GRID = 30.0
SPLIT_COLUMNS = 4  # this many empty columns or more start a new group


@dataclass(frozen=True)
class Group:
    type: str
    x0: float  # left edge of the leftmost hitbox
    x1: float  # right edge of the rightmost hitbox
    boxes: tuple[Box, ...]


def _col(b: Box) -> int:
    return int(((b.x0 + b.x1) / 2) // GRID)


def _row(b: Box) -> int:
    """Grid row of the object's centre: 0 on the ground, 1 one block up. Pits count as row 0."""
    return max(0, round(((b.y0 + b.y1) / 2 - GRID / 2) / GRID))


def _runs(cols: list[int]) -> list[list[int]]:
    """Split sorted columns into runs of consecutive columns."""
    runs: list[list[int]] = []
    for c in cols:
        if runs and c == runs[-1][-1] + 1:
            runs[-1].append(c)
        else:
            runs.append([c])
    return runs


def classify(boxes: list[Box]) -> str:
    """The type of one group of objects, from its shape."""
    by_col: dict[int, list[Box]] = {}
    for b in boxes:
        by_col.setdefault(_col(b), []).append(b)
    cols = sorted(by_col)
    kinds = {b.kind for b in boxes}
    if "pit" in kinds:
        slab_cols = {c for c in cols if any(b.kind == "slab" for b in by_col[c])}
        pit_cols = {c for c in cols if any(b.kind == "pit" for b in by_col[c])}
        if not slab_cols:
            return f"other: {len(pit_cols)} bare pits"
        return "slab_bridge" if slab_cols == pit_cols else "slab_hops"
    ground_spike = lambda c: [b.kind for b in by_col[c]] == ["spike"] and _row(by_col[c][0]) == 0
    if kinds == {"spike"} and all(ground_spike(c) for c in cols):
        runs = _runs(cols)
        if len(runs) == 1:
            return f"spike{len(cols)}"
        if len(runs) == 2 and len(runs[0]) == len(runs[1]) == 1:
            return f"spaced_pair (gap {runs[1][0] - runs[0][0] - 1})"
        return "other: spikes " + " ".join(str(len(r)) for r in runs)
    if kinds <= {"spike", "block"}:
        if len(cols) == 2 and ground_spike(cols[0]) and [b.kind for b in by_col[cols[1]]] == ["block"]:
            if _row(by_col[cols[1]][0]) == 0 and cols[1] - cols[0] > 1:
                return f"spaced_pair (gap {cols[1] - cols[0] - 1}, block)"
        heights = {c: sum(b.kind == "block" for b in by_col[c]) for c in cols}
        top_spikes = [b for b in boxes if b.kind == "spike" and _row(b) == heights[_col(b)]]
        if all(heights[c] for c in cols) and len(top_spikes) == sum(b.kind == "spike" for b in boxes):
            runs = _runs(cols)
            if len(runs) == 1 and set(heights.values()) == {1}:
                if len(cols) == 1:
                    return "block" if not top_spikes else "other: block+spike"
                return "platform+spike" if top_spikes else "platform"
            run_heights = [heights[r[0]] for r in runs]
            widths = {len(r) for r in runs}
            if (not top_spikes and len(runs) >= 2 and len(widths) == 1
                    and all(all(heights[c] == h for c in r) for r, h in zip(runs, run_heights))
                    and run_heights == list(range(1, len(runs) + 1))):
                return f"stairs ({widths.pop()}-wide)"
    return "other: " + ", ".join(sorted(kinds))


def groups(level: Level) -> list[Group]:
    """The level's obstacle groups, left to right."""
    out: list[Group] = []
    current: list[Box] = []
    for b in sorted(level.boxes, key=lambda b: (_col(b), b.y0)):
        if current and _col(b) - _col(current[-1]) - 1 >= SPLIT_COLUMNS:
            out.append(_group(current))
            current = []
        current.append(b)
    if current:
        out.append(_group(current))
    return out


def _group(boxes: list[Box]) -> Group:
    return Group(classify(boxes), min(b.x0 for b in boxes), max(b.x1 for b in boxes), tuple(boxes))


def outcomes(gs: list[Group], completed: bool, death_x: float | None) -> list[str]:
    """For one run, each group's outcome: "cleared", "died" or "not reached".

    The cube died at the first group it hadn't yet passed: the first whose right edge is not
    behind the cube (the player is 30 units wide, so the death x is at most ~15 past an edge)."""
    if completed or death_x is None:
        return ["cleared"] * len(gs)
    out, dead = [], False
    for g in gs:
        if dead:
            out.append("not reached")
        elif g.x1 + GRID / 2 >= death_x:
            out.append("died")
            dead = True
        else:
            out.append("cleared")
    return out


def isolated(group: Group, runway: float = 600.0) -> Level:
    """A level holding only this group, after a flat runway (shifted on the grid) and before an
    equal one: whether the group can be cleared at all, from a full run-up."""
    shift = runway - (group.x0 // GRID) * GRID
    boxes = [Box(b.kind, b.x0 + shift, b.y0, b.x1 + shift, b.y1) for b in group.boxes]
    return Level(name=f"isolated {group.type}", source="obstacles.isolated",
                 length=group.x1 + shift + runway, boxes=boxes)


def shape_key(group: Group) -> tuple:
    """Identical geometry gives the same key, so each distinct shape is tested once in isolation."""
    left = (group.x0 // GRID) * GRID
    return tuple(sorted((b.kind, round(b.x0 - left, 3), round(b.y0, 3), round(b.x1 - left, 3), round(b.y1, 3))
                        for b in group.boxes))
