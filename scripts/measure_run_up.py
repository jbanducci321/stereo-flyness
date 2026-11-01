"""How far away obstacles are when they start looming, on the cube training levels (D43 start gap).

The calibration loom starts `start_gap` units ahead of the eye. Rather than choose it, we take
it from the levels: along the bot's winning path (no brain), each obstacle's run-up is its gap
at the first tick it becomes the nearest looming object (collision mode, D41), i.e. how long
the fly gets to watch it grow. Reports the median (the calibration start gap) and the
25th/90th percentiles (the sensitivity points; the 10th is past the 39° target, D45), and the
share of approaches that start with the object already at or past 39° ("short run-up").

A column that continues the previous looming object (touching it horizontally, with the same
bottom and top, e.g. the second column of a two-wide block) becomes "nearest" one cell after
it, with no new approach. Those are left out of the headline numbers and reported separately.
A touching column with a different top or bottom (a staircase step) is a new approach (agreed
2026-10-31).

Training levels only (never held-out or Stereo Madness, hard rule 5).

Usage:
    uv run python scripts/measure_run_up.py
"""

import sys

import pandas as pd

from ideal_fly import NO_PATCHES
from inspect_encoding import LEVELS, THRESHOLD_DEG, job
from stereo_flyness.game.engine import Game
from stereo_flyness.game.suites import load_level
from stereo_flyness.interface.encoding import CubeEncoder


def run_ups(level, inputs) -> list[dict]:
    enc, game, seen, out, prev = CubeEncoder(level, NO_PATCHES, 180.0, 150.0), Game(level), set(), [], None
    for held in inputs:
        if game.over:
            break
        loom = enc.encode(game.player)
        o = loom.obstacle
        if o is not None and o not in seen:
            seen.add(o)
            same = prev is not None and abs(o.x0 - prev.x1) < 1e-6 and (o.bottom, o.top) == (prev.bottom, prev.top)
            out.append({"x0": o.x0, "height": o.top - o.bottom, "run_up": loom.gap, "theta_start": loom.theta_deg,
                        "first": not out,
                        "continuation": same})
            prev = o
        game.tick(held)
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    names = sorted(p.stem for p in (LEVELS / "training").glob("cube-*.json") if not p.stem.endswith(".meta"))
    rows = []
    for name in names:
        level, bot = load_level(LEVELS, job(name, "training"))
        rows += [{"level": name, **r} for r in run_ups(level, bot.tick_inputs)]
    df = pd.DataFrame(rows)
    df["difficulty"] = df["level"].str.split("-").str[1]
    q = lambda s: (f"P10 {s.quantile(0.1):.0f}, P25 {s.quantile(0.25):.0f}, median {s.median():.0f}, "  # noqa: E731
                   f"P90 {s.quantile(0.9):.0f} (n = {len(s)})")
    new = df[~df["continuation"]]
    print(f"Run-up before an obstacle starts looming, {len(names)} cube training levels (units from the eye):")
    print(f"  new approaches (headline): {q(new['run_up'])}")
    print(f"  without each level's first obstacle: {q(new.loc[~new['first'], 'run_up'])}")
    for d, g in new.groupby("difficulty"):
        print(f"  {d}: {q(g['run_up'])}")
    print(f"  share under 600: {100 * (new['run_up'] < 600).mean():.0f}%; under 1200: "
          f"{100 * (new['run_up'] < 1200).mean():.0f}%")
    print(f"  heights: {new['height'].value_counts().sort_index().to_dict()}")
    print(f"  short run-up (already >= {THRESHOLD_DEG:g}° when it starts looming): "
          f"{100 * (new['theta_start'] >= THRESHOLD_DEG).mean():.1f}%")
    print(f"  left out, continuing the previous object: {len(df) - len(new)}; every column counted: {q(df['run_up'])}")


if __name__ == "__main__":
    main()
