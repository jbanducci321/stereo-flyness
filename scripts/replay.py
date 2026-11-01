"""Replay a recorded run (Step 1.3).

Usage:
    uv run python scripts/replay.py results/runs/bot_stereo_madness
        open a window and play the run (Space pause, Left/Right +-1 s, , . frame step,
        - + speed, R restart, Esc quit)
    uv run python scripts/replay.py results/runs/bot_stereo_madness --still 30
        save a picture of the run at 30 s (default: results/replays/<run>_<seconds>s.png)
    uv run python scripts/replay.py results/runs/bot_stereo_madness --export
        render the run to video (default: results/replays/<run>.mp4; needs ffmpeg)
        --audio FILE   mix in a local audio file (your own copy; never committed)
        --no-overlay   video without the text overlay

The level is found from the run's summary (Stereo Madness -> data/gd/stereo_madness.json), or
given with --level. Replays of Stereo Madness are RobTop-derived and stay in git-ignored results/
(D9).
"""

import argparse
import json
import sys
from pathlib import Path

from stereo_flyness.game.level import Level
from stereo_flyness.game.recorder import RunLog
from stereo_flyness.viewer.export import export_video
from stereo_flyness.viewer.playback import run_window
from stereo_flyness.viewer.render import save_still
from stereo_flyness.viewer.timeline import Timeline

ROOT = Path(__file__).resolve().parents[1]
KNOWN_LEVELS = {"Stereo Madness": ROOT / "data" / "gd" / "stereo_madness.json"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path, help="run folder (ticks.parquet + summary.json)")
    parser.add_argument("--level", type=Path, help="level JSON (default: found from the run's summary)")
    parser.add_argument("--still", type=float, metavar="SECONDS", help="save a picture of this moment")
    parser.add_argument("--out", type=Path, help="output file for --still or --export")
    parser.add_argument("--export", action="store_true", help="render the run to an MP4 video")
    parser.add_argument("--audio", type=Path, help="local audio file to mix into the video")
    parser.add_argument("--no-overlay", action="store_true", help="export without the text overlay")
    args = parser.parse_args()

    log = RunLog.load(args.run)
    level_path = args.level or KNOWN_LEVELS.get(log.summary.level)
    if level_path is None or not level_path.exists():
        print(f"Can't find the level for '{log.summary.level}'. Pass it with --level.")
        return 1
    run_info = Path(args.run) / "run.json"  # brain runs say who drove the cube (fly_log)
    driver = json.loads(run_info.read_text(encoding="utf-8")).get("driver") if run_info.exists() else None
    timeline = Timeline(Level.load(level_path), log, driver=driver)

    if args.export:
        out = args.out or ROOT / "results" / "replays" / f"{args.run.name}.mp4"
        print(f"Rendering {timeline.duration:.1f} s of video...")
        frames = export_video(timeline, out, overlay=not args.no_overlay, audio=args.audio)
        print(f"Saved {out} ({frames} frames)")
        return 0
    if args.still is None:
        s = log.summary
        outcome = "completed" if s.completed else f"died on {s.death_kind} at {s.progress:.1%}"
        print(f"Playing {s.level}: {s.seconds:.1f} s, {outcome}. Esc to quit.")
        run_window(timeline)
        return 0
    out = args.out or ROOT / "results" / "replays" / f"{args.run.name}_{args.still:g}s.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    save_still(timeline, args.still, out)
    print(f"Saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
