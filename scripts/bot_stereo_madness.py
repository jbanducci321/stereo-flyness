"""Validate the engine: can the search bot beat our Stereo Madness?

Beating it shows our physics (docs/game_physics.md) plus our converted layout make a playable,
faithful level. A failure shows the exact spot that's impossible, which points at the
assumption to revisit.

This validates the *game*, not the fly. Nothing here tunes anything, so the held-out rule (D7)
isn't touched. Outputs are git-ignored (D9):
    results/runs/bot_stereo_madness/ticks.parquet + summary.json   (the winning run, if any)

Usage:
    uv run python scripts/fetch_stereo_madness.py      # once, if not built yet
    uv run python scripts/convert_stereo_madness.py    # once
    uv run python scripts/bot_stereo_madness.py
"""

import sys
import time
from pathlib import Path

from stereo_flyness.game.bot import replay, solve
from stereo_flyness.game.level import Level

ROOT = Path(__file__).resolve().parents[1]
LEVEL = ROOT / "data" / "gd" / "stereo_madness.json"
OUT = ROOT / "results" / "runs" / "bot_stereo_madness"


def main() -> int:
    if not LEVEL.exists():
        print("Stereo Madness isn't built. Run fetch_stereo_madness.py, then convert_stereo_madness.py.")
        return 1
    level = Level.load(LEVEL)
    print(f"Searching {level.name} ({len(level.boxes)} hitboxes, {len(level.portals)} portals)...")
    t0 = time.perf_counter()
    result = solve(level)
    took = time.perf_counter() - t0

    if not result.success:
        print(f"NOT BEATEN after {result.nodes:,} states ({took:.1f} s, ship merge steps {result.merge_steps}).")
        print(f"Farthest point: x = {result.farthest_x:.0f} of {level.length:.0f} "
              f"({result.farthest_x / level.length:.1%}, ~{result.farthest_x / 311.58:.1f} s in)")
        print("What killed the attempts there (kind, GD id, x): count")
        for (kind, gd_id, x), n in result.stuck.most_common(8):
            print(f"  {kind:<12} id {gd_id}  x {x}: {n}")
        return 2

    log = replay(level, result)
    log.save(OUT)
    s, df = log.summary, log.to_frame()
    print(f"BEATEN: {result.nodes:,} states searched in {took:.1f} s (ship merge steps {result.merge_steps})")
    print(f"Winning run: {s.seconds:.2f} s, {s.jumps} jumps, held for {df.held.mean():.0%} of ticks")
    print("Mode switches:")
    for _, row in df[df.events.str.contains("portal")].iterrows():
        print(f"  {row.events:<12} at {row.time:6.2f} s  (x {row.x:7.0f}, y {row.y:5.1f})")
    print(f"Saved to {OUT.relative_to(ROOT)} (git-ignored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
