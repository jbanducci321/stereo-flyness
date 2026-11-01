"""How far away obstacles are when they start looming, on the cube training levels (D43 start gap).

The calibration loom starts `start_gap` units ahead of the eye. Rather than choose it, we take
it from the levels: along the bot's winning path (no brain), each obstacle's run-up is its gap
at the first tick it becomes the nearest looming object (collision mode, D41), i.e. how long
the fly gets to watch it grow. Reports the median and the 10th/90th percentiles.

A column that touches the previous one horizontally (e.g. the second column of a two-wide block)
becomes "nearest" one cell after it, with no new approach. Those (run-up <= one cell) are left
out of the headline numbers and reported separately.

Training levels only (never held-out or Stereo Madness, hard rule 5).

Usage:
    uv run python scripts/measure_run_up.py
"""

import sys

import pandas as pd

from ideal_fly import NO_PATCHES
from inspect_encoding import LEVELS, job
from stereo_flyness.game.engine import Game
from stereo_flyness.game.suites import load_level
from stereo_flyness.interface.encoding import CELL, CubeEncoder


def run_ups(level, inputs) -> list[dict]:
    enc, game, seen, out = CubeEncoder(level, NO_PATCHES, 180.0, 150.0), Game(level), set(), []
    for held in inputs:
        if game.over:
            break
        loom = enc.encode(game.player)
        if loom.obstacle is not None and loom.obstacle not in seen:
            seen.add(loom.obstacle)
            out.append({"x0": loom.obstacle.x0, "height": loom.obstacle.top - loom.obstacle.bottom,
                        "run_up": loom.gap, "first": not out})
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
    q = lambda s: f"P10 {s.quantile(0.1):.0f}, median {s.median():.0f}, P90 {s.quantile(0.9):.0f} (n = {len(s)})"  # noqa: E731
    new = df[df["run_up"] > CELL]
    print(f"Run-up before an obstacle starts looming, {len(names)} cube training levels (units from the eye):")
    print(f"  new approaches (headline): {q(new['run_up'])}")
    print(f"  without each level's first obstacle: {q(new.loc[~new['first'], 'run_up'])}")
    for d, g in new.groupby("difficulty"):
        print(f"  {d}: {q(g['run_up'])}")
    print(f"  share under 600: {100 * (new['run_up'] < 600).mean():.0f}%; under 1200: "
          f"{100 * (new['run_up'] < 1200).mean():.0f}%")
    print(f"  heights: {new['height'].value_counts().sort_index().to_dict()}")
    print(f"  left out, touching the previous column: {len(df) - len(new)}; every column counted: {q(df['run_up'])}")


if __name__ == "__main__":
    main()
