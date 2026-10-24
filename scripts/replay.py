"""Replay a recorded run (Step 1.3).

Usage:
    uv run python scripts/replay.py results/runs/bot_stereo_madness --still 30
        save a picture of the run at 30 s (default: results/replays/<run>_<seconds>s.png)

The level is found from the run's summary (Stereo Madness -> data/gd/stereo_madness.json), or
given with --level. Replays of Stereo Madness are RobTop-derived and stay in git-ignored results/
(D9).
"""

import argparse
import sys
from pathlib import Path

from stereo_flyness.game.level import Level
from stereo_flyness.game.recorder import RunLog
from stereo_flyness.viewer.render import save_still
from stereo_flyness.viewer.timeline import Timeline

ROOT = Path(__file__).resolve().parents[1]
KNOWN_LEVELS = {"Stereo Madness": ROOT / "data" / "gd" / "stereo_madness.json"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path, help="run folder (ticks.parquet + summary.json)")
    parser.add_argument("--level", type=Path, help="level JSON (default: found from the run's summary)")
    parser.add_argument("--still", type=float, metavar="SECONDS", help="save a picture of this moment")
    parser.add_argument("--out", type=Path, help="output file for --still")
    args = parser.parse_args()

    log = RunLog.load(args.run)
    level_path = args.level or KNOWN_LEVELS.get(log.summary.level)
    if level_path is None or not level_path.exists():
        print(f"Can't find the level for '{log.summary.level}'. Pass it with --level.")
        return 1
    timeline = Timeline(Level.load(level_path), log)

    if args.still is None:
        print("Pass --still SECONDS (live playback comes in the next checkpoint).")
        return 1
    out = args.out or ROOT / "results" / "replays" / f"{args.run.name}_{args.still:g}s.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_still(timeline, args.still, out)
    print(f"Saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
