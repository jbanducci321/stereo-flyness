"""Video export and event cues."""

import json
import shutil
import subprocess
import wave

import pytest

from stereo_flyness.game.engine import Game
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox
from stereo_flyness.game.recorder import play
from stereo_flyness.viewer.export import FPS, event_cues, export_video
from stereo_flyness.viewer.timeline import Timeline

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def short_timeline():
    level = Level("test", "hand-made", 700, [Box("spike", *hitbox("spike", 400, 15))])
    return Timeline(level, play(Game(level), lambda g: g.ticks == 230))  # jump at x ~ 299: clears the spike


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return {s["codec_type"]: s for s in json.loads(out)["streams"]}


def test_event_cues_list_every_event_in_time_order():
    tl = short_timeline()
    cues = event_cues(tl)
    assert [e for _, e in cues][:2] == ["jump", "land"] and cues[-1][1] == "finish"
    assert [t for t, _ in cues] == sorted(t for t, _ in cues)


@needs_ffmpeg
def test_export_writes_a_60fps_video(tmp_path):
    tl = short_timeline()
    frames = export_video(tl, tmp_path / "run.mp4", tail_seconds=0.5)
    assert frames == tl.last_tick // 4 + 1 + 30
    video = probe(tmp_path / "run.mp4")["video"]
    assert (video["width"], video["height"]) == (1280, 720)
    assert video["r_frame_rate"] == f"{FPS}/1"
    assert int(video["nb_frames"]) == frames


@needs_ffmpeg
def test_export_mixes_in_a_local_audio_file(tmp_path):
    silence = tmp_path / "silence.wav"
    with wave.open(str(silence), "wb") as w:  # 5 s of silence, standing in for a song
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(22050)
        w.writeframes(b"\x00\x00" * 22050 * 5)
    export_video(short_timeline(), tmp_path / "run.mp4", audio=silence)
    assert set(probe(tmp_path / "run.mp4")) == {"video", "audio"}
