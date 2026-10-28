"""Export a recorded run to video, and the hooks music and sound effects will attach to later.

Frames are rendered headlessly at 60 fps (every 4th physics tick) and piped as raw RGB into the
ffmpeg program (must be on PATH). No extra Python dependency.

Audio (D19/D20): `audio` mixes in a local audio file, e.g. a song, aligned to the run's start.
`event_cues` lists when each event happens, which is the hook for sound effects (a jump sound on
"jump", a crash on "death"). The song and the game's sound effects are copyrighted, so they're
only ever loaded from the user's own local files and never committed.
"""

import shutil
import subprocess
from pathlib import Path

import pygame

from stereo_flyness.game import physics as P
from stereo_flyness.viewer.playback import FPS, PlaybackClock, draw_overlay
from stereo_flyness.viewer.render import SIZE, render_frame
from stereo_flyness.viewer.timeline import Timeline

TICKS_PER_FRAME = P.TICKS_PER_SECOND // FPS  # 4


def event_cues(timeline: Timeline) -> list[tuple[float, str]]:
    """(seconds, event) for every event in the run, in order: where sound effects would go."""
    return [(t.time, e) for t in timeline.ticks for e in t.events]


def export_video(timeline: Timeline, path: Path, size=SIZE, overlay: bool = True,
                 audio: Path | None = None, tail_seconds: float = 1.0) -> int:
    """Render the run to `path` (MP4, H.264). Returns the number of frames written.

    The video holds on the last frame for `tail_seconds` so a death or finish stays visible.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg not found on PATH (needed for video export).")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    w, h = size
    cmd = [ffmpeg, "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-"]
    if audio is not None:
        cmd += ["-i", str(audio), "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(path)]

    pygame.font.init()
    font = pygame.font.SysFont("consolas", 20)
    surface = pygame.Surface(size)
    n_frames = timeline.last_tick // TICKS_PER_FRAME + 1 + round(tail_seconds * FPS)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for frame in range(n_frames):
            tick = min(frame * TICKS_PER_FRAME, timeline.last_tick)
            render_frame(surface, timeline, tick)
            if overlay:
                clock = PlaybackClock(timeline.duration, time=tick / P.TICKS_PER_SECOND)
                draw_overlay(surface, timeline, clock, font)
            proc.stdin.write(pygame.image.tobytes(surface, "RGB"))
    finally:
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg failed while writing {path}")
    return n_frames
