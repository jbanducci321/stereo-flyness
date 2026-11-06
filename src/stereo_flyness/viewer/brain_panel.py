"""The brain panel (D19, R2): a strip under the game showing what the brain was given and what it did.

It draws only what the closed-loop run logged (interface/fly_log.py: brain.parquet), exactly as
recorded: no smoothing, no interpolation, no rescaling of counts (hard rule 10). Two boxes, always
kept apart and labelled:
- **INPUT, our encoding:** the values our code computed and fed in on that frame. Only the shown
  mode's inputs are on (interface/modes.py), so the box lists whichever input columns that row
  logged: θ, f and R for the cube; the ship's own columns once its design exists.
- **THE FLY'S SPIKES, recorded:** one lane per watched group (the `spikes_<group>` columns), a mark
  for every frame in the last second with that frame's count; the press each frame's spikes
  decided; how many neurons fired in the whole network; the stuck flag.

Which neurons to show, and how (labels, colours, layout by visual field), is Shannyn's design (R3).
Until then this layout is provisional and says so on screen.

Brain row k saw the game after k ticks (D40), so at timeline tick t the panel shows row t.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pygame

from stereo_flyness.game import physics as P
from stereo_flyness.viewer.render import COLOURS

HEIGHT = 200
WINDOW_TICKS = P.TICKS_PER_SECOND  # spike lanes show the last second
# Logged columns that aren't our input: bookkeeping, the fly's output and the recorder's checks.
NOT_INPUT = {"frame", "tick_seen", "mode", "fly_press", "held", "active_neurons", "active_in_window",
             "stuck_share", "stuck_flag", "backup_flag"}
INPUT_LABELS = {"theta_deg": ("θ", "°"), "gap": ("gap", " u"), "f": ("f", ""), "rate_hz": ("R × f", " Hz")}
PROVISIONAL = "Panel layout provisional: which neurons to show is Shannyn's design (R3)."
SPIKE_COLOUR = (255, 230, 90)
INPUT_COLOUR = (120, 200, 255)


@dataclass
class BrainTrack:
    """A run's brain log, indexed by brain frame."""

    brain: pd.DataFrame

    @classmethod
    def load(cls, run_dir) -> "BrainTrack | None":
        path = Path(run_dir) / "brain.parquet"
        return cls(pd.read_parquet(path)) if path.exists() else None

    def __post_init__(self):
        b = self.brain.reset_index(drop=True)
        if "mode" not in b:  # cube runs from before interface/modes.py
            b = b.assign(mode="cube")
        self.brain = b
        self.groups = [c[len("spikes_"):] for c in b.columns if c.startswith("spikes_")]
        self.inputs = [c for c in b.columns if c not in NOT_INPUT and not c.startswith("spikes_")]
        self._spikes = {g: b[f"spikes_{g}"].to_numpy() for g in self.groups}
        self._press = b["fly_press"].to_numpy(bool) if "fly_press" in b else np.zeros(len(b), bool)

    def __len__(self) -> int:
        return len(self.brain)

    def row(self, tick: int) -> int:
        return max(0, min(tick, len(self) - 1))

    def input_items(self, tick: int) -> list[tuple[str, str]]:
        """(label, value) for every input this frame logged; inputs that are off (blank) are left out."""
        r = self.brain.iloc[self.row(tick)]
        out = []
        for c in self.inputs:
            v = r[c]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            name, unit = INPUT_LABELS.get(c, (c, ""))
            out.append((name, f"{_num(v)}{unit}"))
        return out

    def spike_window(self, group: str, tick: int, window: int = WINDOW_TICKS) -> np.ndarray:
        """The group's recorded counts for the last `window` frames up to `tick` (0 before the run)."""
        end = self.row(tick) + 1
        counts = self._spikes[group][max(0, end - window):end]
        return np.concatenate([np.zeros(window - len(counts), counts.dtype), counts])

    def press_window(self, tick: int, window: int = WINDOW_TICKS) -> np.ndarray:
        end = self.row(tick) + 1
        p = self._press[max(0, end - window):end]
        return np.concatenate([np.zeros(window - len(p), bool), p])


def _num(v) -> str:
    """As logged, to 1 decimal, or 3 significant figures below 1 so small values don't read as 0."""
    if not isinstance(v, (float, np.floating)):
        return str(v)
    return f"{v:.3g}" if 0 < abs(v) < 1 else f"{v:.1f}"


_fonts: dict = {}


def _font(size):
    if size not in _fonts:
        pygame.font.init()
        _fonts[size] = pygame.font.SysFont("consolas", size)
    return _fonts[size]


def _text(surface, text, xy, colour=COLOURS["ground_line"], size=16):
    surface.blit(_font(size).render(text, True, colour), xy)


def draw_brain_panel(surface: pygame.Surface, track: BrainTrack, tick: int) -> None:
    """Draw the panel for `tick` onto `surface` (the strip under the game)."""
    w, h = surface.get_size()
    surface.fill(COLOURS["outline"])
    r = track.brain.iloc[track.row(tick)]
    split = 430

    # Left: our input. A different colour and its own heading, so it's never read as the fly's activity.
    pygame.draw.rect(surface, INPUT_COLOUR, (6, 6, split - 12, h - 12), width=2, border_radius=6)
    _text(surface, "INPUT: our encoding, not the fly", (16, 12), INPUT_COLOUR)
    _text(surface, f"mode: {str(r['mode']).upper()}", (16, 36), INPUT_COLOUR)
    items = track.input_items(tick)
    for i, (name, value) in enumerate(items[:8]):  # two columns of 4
        _text(surface, f"{name}: {value}", (16 + 205 * (i // 4), 60 + 18 * (i % 4)), size=14)
    if not items:
        _text(surface, "no input on this frame", (16, 58), size=15)

    # Right: the fly's spikes, as recorded.
    x0, lane_w = split + 150, w - split - 190
    pygame.draw.rect(surface, SPIKE_COLOUR, (split, 6, w - split - 6, h - 12), width=2, border_radius=6)
    _text(surface, "THE FLY'S SPIKES: recorded, unaltered (last 1 s)", (split + 10, 12), SPIKE_COLOUR)
    lanes = [(g, track.spike_window(g, tick)) for g in track.groups]
    lanes.append(("press decided", track.press_window(tick).astype(int)))
    lane_h = min(22, (h - 70) // max(1, len(lanes)))
    for i, (name, counts) in enumerate(lanes):
        y = 38 + i * lane_h
        _text(surface, name[:18], (split + 10, y + 2), size=14)
        pygame.draw.line(surface, COLOURS["ground"], (x0, y + lane_h - 3), (x0 + lane_w, y + lane_h - 3), 1)
        step = lane_w / len(counts)
        for k in np.flatnonzero(counts):
            xs = round(x0 + k * step)
            pygame.draw.line(surface, SPIKE_COLOUR, (xs, y + 2), (xs, y + lane_h - 4), max(1, round(step)))
        now = int(counts[-1])
        _text(surface, str(now) if now else "", (x0 + lane_w + 4, y + 2), SPIKE_COLOUR, size=14)
    y = 38 + len(lanes) * lane_h + 4
    stuck = bool(r.get("stuck_flag", False))
    _text(surface, f"neurons that fired this frame (whole network): {int(r.get('active_neurons', 0))}"
          + ("   STUCK STATE FLAGGED" if stuck else ""), (split + 10, y), COLOURS["death"] if stuck else COLOURS["ground_line"], size=14)
    _text(surface, PROVISIONAL, (split + 10, h - 24), COLOURS["block"], size=13)
