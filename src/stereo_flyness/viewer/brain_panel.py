"""The brain panel (R3, version 1): Shannyn's design, docs/notes/brain_panel_design.md.

A strip under the game in three columns, in the order the signal flows:
1. **What we show the fly** (our input, white/grey, outlined): both eyes as rows of dots, LC4 and
   LPLC2, lit when *we drive* that neuron (in patch order, brightness = the rate we send). Under
   them θ, f and the rate, with a gauge marking the calibrated 39° (D43). These are our encoding's
   driven/not-driven states, never the driven neurons' spikes. In a mode with no eye display yet
   (the ship, until its design is logged), the logged input values are listed instead.
2. **The fly's escape neurons** (the model's activity, amber, filled): both Giant Fibers, which
   light when they spike, with their spike count; a raster of each over the last second, one mark
   per frame with spikes; presses on the same time axis, one tick after the spike that made them
   (▲ with ✓ if it started a jump, grey ▲ if not). Any other watched group gets its own raster.
3. **The rest of the brain** (the model's activity): how many neurons fired per frame over the
   last 2 s, **not counting the neurons we stimulate** (D38); the stuck-state share with its 50%
   line; a banner from the frame the stuck flag starts (D38).

**Nothing is smoothed, interpolated or rescaled** (hard rule 10). Every number is a sum or count of
logged values. The game is drawn every 4th tick at 60 fps, so the "now" numbers are **binned**:
every spike since the previous drawn frame (4 ticks in video), labelled as such. No spike is
dropped, moved or invented. The rasters and traces draw every tick.

Time axis: brain row k saw the game after k ticks (D40); its spikes are drawn at k and its press
at k + 1, where the game applied it.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pygame

from stereo_flyness.game import physics as P
from stereo_flyness.viewer.render import COLOURS, font

HEIGHT = 230
RASTER_TICKS = P.TICKS_PER_SECOND  # ~1 s for the Giant Fibers
TRACE_TICKS = 2 * P.TICKS_PER_SECOND  # ~2 s for active neurons
BIN_TICKS = P.TICKS_PER_SECOND // 60  # video draws every 4th tick
THRESHOLD_DEG = 39.0  # the calibration target (D43)
GAUGE_MAX_DEG = 90.0
ROOT = Path(__file__).resolve().parents[3]
TARGETS = ROOT / "configs" / "target_neurons_783.csv"
LOOM_TYPES = ("LC4", "LPLC2")
SIDES = ("left", "right")
DOTS_PER_ROW = 27

INPUT = (225, 225, 235)  # our input: white/grey, outlined
INPUT_DIM = (70, 70, 85)
AMBER = (255, 176, 46)  # the model's spikes, and only those
AMBER_DIM = (90, 62, 20)
PRESS = (240, 240, 240)
PRESS_DEAD = (110, 110, 110)
TEXT = COLOURS["ground_line"]
SMALL = (150, 150, 170)
# Logged columns that aren't our input: bookkeeping, the fly's output and the recorder's checks.
NOT_INPUT = {"frame", "tick_seen", "mode", "fly_press", "held", "active_neurons", "active_in_window",
             "stuck_share", "stuck_flag", "backup_flag"}


def loom_counts(path=TARGETS) -> dict[tuple[str, str], int]:
    """Neurons per (side, type) for LC4/LPLC2, from the committed v783 target list."""
    t = pd.read_csv(path)
    t = t[t["cell_type"].isin(LOOM_TYPES)]
    return {(s, ty): int(((t["side"] == s) & (t["cell_type"] == ty)).sum()) for s in SIDES for ty in LOOM_TYPES}


def loom_ids(path=TARGETS) -> np.ndarray:
    t = pd.read_csv(path)
    return t.loc[t["cell_type"].isin(LOOM_TYPES), "flywire_id"].to_numpy(np.int64)


@dataclass
class BrainTrack:
    """A run's brain log for the panel: brain.parquet, plus spikes.npz and run.json when loaded from disk."""

    brain: pd.DataFrame
    spikes: dict | None = None  # flyids, frame, neuron, count (and stimulated, for runs that log it)
    run: dict = field(default_factory=dict)

    @classmethod
    def load(cls, run_dir) -> "BrainTrack | None":
        d = Path(run_dir)
        if not (d / "brain.parquet").exists():
            return None
        spikes = None
        if (d / "spikes.npz").exists():
            with np.load(d / "spikes.npz") as z:
                spikes = {k: z[k] for k in z.files}
        run = json.loads((d / "run.json").read_text(encoding="utf-8")) if (d / "run.json").exists() else {}
        return cls(pd.read_parquet(d / "brain.parquet"), spikes, run)

    def __post_init__(self):
        b = self.brain.reset_index(drop=True)
        if "mode" not in b:  # cube runs from before interface/modes.py
            b = b.assign(mode="cube")
        self.brain = b
        self.groups = [c[len("spikes_"):] for c in b.columns if c.startswith("spikes_")]
        self.gf = [g for g in ("GF_L", "GF_R") if g in self.groups]
        self.others = [g for g in self.groups if g not in self.gf]
        self.inputs = [c for c in b.columns if c not in NOT_INPUT and not c.startswith("spikes_")]
        self._spikes = {g: b[f"spikes_{g}"].to_numpy() for g in self.groups}
        self._stuck = b["stuck_flag"].to_numpy(bool) if "stuck_flag" in b else np.zeros(len(b), bool)
        self._stuck_since = np.maximum.accumulate(self._stuck) if len(b) else self._stuck
        self.peak_rate = float(self.run.get("rate_hz") or np.nanmax(b.get("rate_hz", pd.Series([1.0]))) or 1.0)
        self._active_setup()

    def _active_setup(self):
        """Per-frame active neurons without the ones we stimulate, from spikes.npz (D38's count)."""
        n = len(self.brain)
        self.active_note = ""
        if self.spikes is None:
            self.active = self.brain.get("active_neurons", pd.Series(np.zeros(n))).to_numpy()
            self.active_note = " (raw: includes stimulated)"
            self._frames = self._neurons = None
            return
        flyids, frames, neurons = self.spikes["flyids"], self.spikes["frame"], self.spikes["neuron"]
        stim = self.spikes.get("stimulated")
        if stim is None:  # runs from before the recorder saved them: cube runs stimulate exactly LC4 + LPLC2
            stim = loom_ids()
            expected = self.run.get("flags", {}).get("stimulated_neurons_excluded")
            in_net = int(np.isin(stim, flyids).sum())
            if expected is not None and expected != in_net:
                stim = np.zeros(0, np.int64)
                self.active_note = " (raw: stimulated set unknown)"
        keep = ~np.isin(flyids[neurons], np.asarray(stim, np.int64))
        self._frames, self._neurons = frames[keep], neurons[keep]
        self.active = np.bincount(self._frames, minlength=n)[:n] if len(self._frames) else np.zeros(n, int)

    def __len__(self) -> int:
        return len(self.brain)

    def row(self, tick: int) -> int:
        return max(0, min(tick, len(self) - 1))

    def bin(self, tick: int, since: int | None = None) -> tuple[int, int]:
        """Rows (a, b] shown as "now" at `tick`: every frame since the previous drawn one."""
        b = self.row(tick)
        a = b - BIN_TICKS if since is None or since >= tick else min(since, b - 1)
        a = max(-1, a)  # nothing before the run's first frame
        return a, b

    def bin_spikes(self, group: str, tick: int, since: int | None = None) -> int:
        a, b = self.bin(tick, since)
        return int(self._spikes[group][a + 1:b + 1].sum())

    def bin_active(self, tick: int, since: int | None = None) -> int | None:
        """Distinct non-stimulated neurons that fired in the bin (None without spikes.npz)."""
        if self._frames is None:
            return None
        a, b = self.bin(tick, since)
        lo, hi = np.searchsorted(self._frames, [a + 1, b + 1])
        return int(len(np.unique(self._neurons[lo:hi])))

    def window(self, values: np.ndarray, tick: int, size: int) -> np.ndarray:
        """`values` for the last `size` rows up to `tick`, padded with zeros before the run."""
        end = self.row(tick) + 1
        v = values[max(0, end - size):end]
        return np.concatenate([np.zeros(size - len(v), v.dtype), v])

    def spike_window(self, group: str, tick: int, size: int = RASTER_TICKS) -> np.ndarray:
        return self.window(self._spikes[group], tick, size)

    def input_items(self, tick: int) -> list[tuple[str, str]]:
        """(name, value) for every input this frame logged; inputs that are off (blank) are left out."""
        r = self.brain.iloc[self.row(tick)]
        out = []
        for c in self.inputs:
            v = r[c]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                continue
            out.append((c, _num(v)))
        return out

    def stuck_since(self, tick: int) -> bool:
        return bool(self._stuck_since[self.row(tick)]) if len(self) else False


def _num(v) -> str:
    """As logged, to 1 decimal, or 3 significant figures below 1 so small values don't read as 0."""
    if not isinstance(v, (float, np.floating)):
        return str(v)
    return f"{v:.3g}" if 0 < abs(v) < 1 else f"{v:.1f}"


def _text(surface, text, xy, colour=TEXT, size=15):
    surface.blit(font(size).render(text, True, colour), xy)


def _eye(surface, x, y, side, row, counts, rate_frac):
    """One eye: LC4 then LPLC2, dots in patch order, lit when we drive them."""
    _text(surface, f"{side} eye", (x, y), INPUT, 13)
    y += 16
    for ty in LOOM_TYPES:
        n = counts[(side, ty)]
        driven = int(row.get(f"driven_{side}_{ty}", 0) or 0)
        _text(surface, ty, (x, y), SMALL, 11)
        y += 12
        level = int(90 + 165 * max(0.0, min(1.0, rate_frac)))
        for k in range(n):
            cx, cy = x + 3 + (k % DOTS_PER_ROW) * 7, y + 3 + (k // DOTS_PER_ROW) * 7
            if k < driven:
                pygame.draw.circle(surface, (level, level, level), (cx, cy), 3)
            else:
                pygame.draw.circle(surface, INPUT_DIM, (cx, cy), 3, width=1)
        y += 7 * -(-n // DOTS_PER_ROW) + 3
    return y


def _column_input(surface, track, tick, rect):
    x0, y0, w, h = rect
    pygame.draw.rect(surface, INPUT, rect, width=1, border_radius=6)
    _text(surface, "WHAT WE SHOW THE FLY (our input, not its activity)", (x0 + 8, y0 + 6), INPUT, 13)
    r = track.brain.iloc[track.row(tick)]
    mode = str(r["mode"])
    if mode == "cube" and "theta_deg" in r and not pd.isna(r["theta_deg"]):
        counts = loom_counts()
        rate = float(r.get("rate_hz", 0) or 0)
        frac = rate / track.peak_rate if track.peak_rate else 0.0
        y = max(_eye(surface, x0 + 10, y0 + 26, "left", r, counts, frac),
                _eye(surface, x0 + 10 + 205, y0 + 26, "right", r, counts, frac))
        theta, f = float(r["theta_deg"]), float(r.get("f", 0) or 0)
        _text(surface, f"θ {theta:5.1f}°   f {f:.0%}   {rate:.0f} Hz per driven neuron", (x0 + 10, y), INPUT, 14)
        gx, gy, gw = x0 + 10, y + 20, w - 20
        pygame.draw.rect(surface, INPUT_DIM, (gx, gy, gw, 6), width=1)
        pygame.draw.rect(surface, INPUT, (gx, gy, round(gw * min(theta, GAUGE_MAX_DEG) / GAUGE_MAX_DEG), 6))
        tx = gx + round(gw * THRESHOLD_DEG / GAUGE_MAX_DEG)
        pygame.draw.line(surface, AMBER_DIM, (tx, gy - 3), (tx, gy + 9), 2)
        _text(surface, "39° (the real fly's threshold)", (tx + 4, gy + 8), SMALL, 11)
        _text(surface, "Dots are in our patch order, not the eye's real layout.", (x0 + 10, y0 + h - 16), SMALL, 11)
    else:
        _text(surface, f"mode: {mode.upper()}", (x0 + 10, y0 + 28), INPUT, 14)
        items = track.input_items(tick)
        for i, (name, value) in enumerate(items[:8]):
            _text(surface, f"{name}: {value}", (x0 + 10, y0 + 50 + 17 * i), INPUT, 13)
        if not items:
            _text(surface, "no input on this frame", (x0 + 10, y0 + 50), INPUT, 13)
        if mode == "ship":
            _text(surface, "Ship display: added with the ship design (Step 5).", (x0 + 10, y0 + h - 16), SMALL, 11)


def _raster(surface, x, y, w, h, counts, colour):
    pygame.draw.line(surface, AMBER_DIM, (x, y + h), (x + w, y + h), 1)
    step = w / len(counts)
    for k in np.flatnonzero(counts):
        xs = round(x + k * step)
        pygame.draw.line(surface, colour, (xs, y), (xs, y + h - 1), max(1, round(step)))


def _column_escape(surface, track, timeline, tick, since, rect):
    x0, y0, w, h = rect
    pygame.draw.rect(surface, AMBER, rect, width=1, border_radius=6)
    _text(surface, "THE FLY'S ESCAPE NEURONS (the model's activity)", (x0 + 8, y0 + 6), AMBER, 13)
    a, b = track.bin(tick, since)
    for i, g in enumerate(track.gf):
        n = track.bin_spikes(g, tick, since)
        cx = x0 + 60 + i * 150
        if n:
            pygame.draw.circle(surface, AMBER, (cx, y0 + 44), 13)
        pygame.draw.circle(surface, AMBER, (cx, y0 + 44), 13, width=2)
        label = "GF left" if g == "GF_L" else "GF right"
        _text(surface, f"{label}  {n}", (cx + 18, y0 + 36), AMBER if n else AMBER_DIM, 14)
    _text(surface, f"spikes in the last {b - a} tick{'s' if b - a != 1 else ''}"
          + (" (1/60 s)" if b - a == BIN_TICKS else ""), (x0 + 10, y0 + 62), SMALL, 11)
    lx, lw, y = x0 + 80, w - 92, y0 + 80
    lanes = track.gf + track.others
    lane_h = max(10, min(18, (h - 140) // max(1, len(lanes))))
    for g in lanes:
        _text(surface, g, (x0 + 10, y), AMBER, 12)
        _raster(surface, lx, y, lw, lane_h - 4, track.spike_window(g, tick), AMBER)
        y += lane_h
    # Presses on the same axis, at the tick the game applied them (one tick after the spike).
    _text(surface, "press", (x0 + 10, y + 2), PRESS, 12)
    step = lw / RASTER_TICKS
    first = track.row(tick) - RASTER_TICKS + 1
    for t in range(max(1, first), min(tick, timeline.last_tick) + 1):
        view = timeline.ticks[t]
        if view.held:
            xs = lx + (t - first) * step
            colour = PRESS if "jump" in view.events else PRESS_DEAD
            pygame.draw.polygon(surface, colour, [(xs, y + 2), (xs - 4, y + 11), (xs + 4, y + 11)])
            if "jump" in view.events:  # a drawn tick mark (the font has no ✓)
                pygame.draw.lines(surface, PRESS, False, [(xs - 3, y + 16), (xs - 1, y + 19), (xs + 4, y + 13)], 2)
    _text(surface, "Last 1 s. ▲ press: ticked = started a jump, grey = mid-air.", (x0 + 10, y0 + h - 16), SMALL, 11)


def _column_rest(surface, track, tick, since, rect):
    x0, y0, w, h = rect
    pygame.draw.rect(surface, AMBER, rect, width=1, border_radius=6)
    _text(surface, "THE REST OF THE BRAIN (the model's activity)", (x0 + 8, y0 + 6), AMBER, 13)
    now = track.bin_active(tick, since)
    _text(surface, "active neurons" + track.active_note, (x0 + 10, y0 + 28), AMBER, 13)
    if now is not None:
        _text(surface, f"{now} fired in the last {track.bin(tick, since)[1] - track.bin(tick, since)[0]} ticks",
              (x0 + 10, y0 + 44), AMBER, 12)
    trace = track.window(np.asarray(track.active), tick, TRACE_TICKS)
    tx, ty, tw, th = x0 + 10, y0 + 62, w - 20, 60
    pygame.draw.line(surface, AMBER_DIM, (tx, ty + th), (tx + tw, ty + th), 1)
    top = max(1, int(trace.max()))
    step = tw / len(trace)
    for k in np.flatnonzero(trace):
        xs = round(tx + k * step)
        pygame.draw.line(surface, AMBER, (xs, ty + th), (xs, ty + th - round(th * trace[k] / top)), 1)
    _text(surface, f"per frame, last 2 s (scale 0–{top})", (tx, ty + th + 2), SMALL, 11)
    share = float(track.brain["stuck_share"].iloc[track.row(tick)]) if "stuck_share" in track.brain else 0.0
    by = ty + th + 22
    _text(surface, f"stuck-state share (last ~100 ms): {share:.0%}", (tx, by), TEXT, 12)
    bx, bw = tx, tw
    pygame.draw.rect(surface, INPUT_DIM, (bx, by + 16, bw, 8), width=1)
    pygame.draw.rect(surface, COLOURS["death"] if share >= 0.5 else AMBER, (bx, by + 16, round(bw * min(share, 1.0)), 8))
    pygame.draw.line(surface, TEXT, (bx + bw // 2, by + 12), (bx + bw // 2, by + 28), 1)
    _text(surface, "50%", (bx + bw // 2 + 3, by + 26), SMALL, 10)
    _text(surface, "Not counting the neurons we stimulate (D38).", (x0 + 10, y0 + h - 16), SMALL, 11)


def _stuck_banner(surface, w):
    band = pygame.Rect(0, HEIGHT // 2 - 14, w, 28)
    pygame.draw.rect(surface, (60, 10, 10), band)
    for x in range(-28, w, 16):  # stripes, so it can't be mistaken for normal activity
        pygame.draw.line(surface, COLOURS["death"], (x, band.bottom), (x + 28, band.top), 4)
    msg = font(16).render("Model artefact: self-sustaining activity (not fly behaviour, see README)", True, (255, 255, 255))
    surface.blit(msg, (w // 2 - msg.get_width() // 2, band.y + 5))


def draw_brain_panel(surface: pygame.Surface, track: BrainTrack, timeline, tick: int, since: int | None = None) -> None:
    """Draw the panel for `tick` onto `surface` (the strip under the game). `since` is the tick
    drawn before this one; the "now" numbers sum every frame after it (4 ticks by default)."""
    w, h = surface.get_size()
    surface.fill(COLOURS["outline"])
    c1, c2 = 430, 860
    _column_input(surface, track, tick, (4, 4, c1 - 8, h - 8))
    _column_escape(surface, track, timeline, tick, since, (c1, 4, c2 - c1 - 4, h - 8))
    _column_rest(surface, track, tick, since, (c2, 4, w - c2 - 4, h - 8))
    if track.stuck_since(tick):
        _stuck_banner(surface, w)
