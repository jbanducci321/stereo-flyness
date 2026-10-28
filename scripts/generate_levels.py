"""Build the practice-level suites from configs/level_suites.toml (D26).

Every level is generated, beaten by the search bot, measured, and cached in results/levels/<suite>/
(git-ignored). Levels already built with the current generator version are skipped. Ship and mixed
levels take ~10-45 s each to validate, so jobs run in parallel.

Usage:
    uv run python scripts/generate_levels.py                   # both suites (~10-15 min on 4 cores)
    uv run python scripts/generate_levels.py --suite training --limit 2 --gallery
        --limit N   at most N levels per kind and difficulty (quick look)
        --gallery   also save an overview picture of each level with the bot's path
        --jobs N    parallel workers (default 4)
Writes results/levels/<suite>/manifest.csv (one row per level) and prints a difficulty summary.
"""

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
from joblib import Parallel, delayed

from stereo_flyness.game import suites
from stereo_flyness.game.bot import replay

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "level_suites.toml"
OUT = ROOT / "results" / "levels"
SUMMARY_COLS = ["clusters_per_10s", "median_gap_s", "tightest_window_ms", "median_window_ms",
                "pct_windows_under_50ms", "tightest_opening", "attempts"]


def _build(job, out, seconds):
    return suites.build(job, out, seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--suite", choices=["training", "held_out"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--gallery", action="store_true")
    args = parser.parse_args()

    config = suites.load_config(args.config)
    all_jobs = suites.jobs(config, args.suite, args.limit)
    todo = [j for j in all_jobs if not suites.is_built(args.out, j)]
    print(f"{len(all_jobs)} levels in scope; {len(all_jobs) - len(todo)} already built; building {len(todo)}...")
    t0 = time.perf_counter()
    Parallel(n_jobs=args.jobs, verbose=5)(delayed(_build)(j, args.out, config["seconds"]) for j in todo)
    print(f"Built {len(todo)} levels in {time.perf_counter() - t0:.0f} s")

    rows = pd.DataFrame([suites.load_row(args.out, j) for j in all_jobs])
    for suite, df in rows.groupby("suite"):
        df.to_csv(args.out / suite / "manifest.csv", index=False)
        print(f"\n== {suite}: {len(df)} levels (means by kind and difficulty) ==")
        summary = df.groupby(["kind", "difficulty"], sort=False)[SUMMARY_COLS].mean().round(2)
        print(summary.to_string())

    if args.gallery:
        from stereo_flyness.viewer.overview import save_overview
        for job in all_jobs:
            level, bot = suites.load_level(args.out, job)
            gallery = args.out / job.suite / "gallery"
            gallery.mkdir(exist_ok=True)
            save_overview(level, gallery / f"{job.name}.png", replay(level, bot))
        print(f"\nGallery images in {args.out}/<suite>/gallery/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
