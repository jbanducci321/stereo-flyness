# Level format (D22)

One JSON file per level, used for Stereo Madness and every generated practice level.
- **Code:** `src/stereo_flyness/game/level.py` (`Level`, `Box`, `Portal`, `ship_bounds`) and `src/stereo_flyness/game/objects.py` (kinds, hitbox sizes, GD ID mapping).
- **Physics:** facts in `docs/game_physics.md`.

## Conventions
- **Units:** Geometry Dash units (1 block = 30). x increases along the level; **y = 0 is the ground surface**. GD's internal world y is ours + 90; we don't use it.
- **Objects are stored as ready-made hitboxes:** axis-aligned rectangles, resolved when the level is built. The engine only tests rectangle overlaps.
- **Kept:** gameplay objects only. Decoration, colour triggers and coins are dropped; the replay viewer draws its own simple visuals.

## Fields

```json
{
 "format_version": 1,
 "name": "Stereo Madness",
 "source": "official main-level data (D21)",
 "start_mode": "cube",
 "speed": "normal",
 "length": 26384,
 "boxes":   [{"kind": "spike", "x0": 522, "y0": 9, "x1": 528, "y1": 21, "source_id": 8}],
 "portals": [{"mode": "ship", "x": 7995, "y": 165, "source_id": 13}]
}
```

| Field | Meaning |
|---|---|
| `format_version` | Must be `1`. Loading rejects other versions. |
| `name`, `source` | Human-readable; `source` says where the layout came from (e.g. a generator name and seed) |
| `start_mode` | `"cube"` or `"ship"` |
| `speed` | `"normal"` only (Stereo Madness never changes speed) |
| `length` | x where the level ends (reaching it = completed) |
| `boxes[]` | Hitboxes: `kind` plus corners `x0 < x1`, `y0 < y1`; `source_id` is the GD object ID (or null for generated objects) |
| `portals[]` | `mode` (`"cube"`/`"ship"`), the portal's centre `x`, `y`, and an optional `source_id` |

## Object kinds

| Kind | Solid or hazard | Hitbox (w × h) | GD IDs |
|---|---|---|---|
| `block` | Solid | 30 × 30 | 1, 2, 3, 4, 6, 7, 62, 65 |
| `slab` | Solid | 30 × 14 | 40 |
| `spike` | Hazard | 6 × 12 | 8 |
| `small_spike` | Hazard | 4 × 7.6 | 103 |
| `half_spike` | Hazard | 6 × 5.6 | 39 |
| `pit` | Hazard | 9 × 10.8 | 9 |

A rotation of 90° or 270° swaps width and height; other rotations are rejected (Stereo Madness only uses multiples of 90°).

## Ship areas
- Portals store only their position. The engine derives each ship area from the portal's `y` with `ship_bounds(y)`, the GD rule in `docs/game_physics.md` §4: a 300-unit-tall area whose position depends on the portal's height. Keeping the rule in code means generated levels and Stereo Madness behave identically.
- **A ship portal reached while already in ship mode** starts a new ship area with new bounds. Stereo Madness does this at x = 24,045.
- `Level.sections()` lists the stretches between portals with their mode and bounds.

## Where levels live

| Level | Path | Committed? |
|---|---|---|
| Stereo Madness | `data/gd/stereo_madness.json`, built by `scripts/fetch_stereo_madness.py` then `scripts/convert_stereo_madness.py` | **Never** (RobTop's design, D9; held-out test, D7) |
| Generated practice levels | To be decided in Step 1 | Yes (our own) |
