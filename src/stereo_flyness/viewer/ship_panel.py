"""The brain panel in ship mode (D53): Shannyn's draft, docs/notes/brain_panel_design.md "Ship mode".

Same three columns and rules as the cube (recorded activity unaltered; our input separate, white and
outlined; the model's spikes amber). What changes in ship mode:
- **On the game:** an outlined white bracket on the target opening, labelled "target (our code)",
  with a thin line from the ship's eye to its centre (B and C only; self-motion only has no target).
- **Column 1, our input:** the variant tag; our steering (Δy, dx, and a gauge of vy against v_req);
  the motion we drive as one bar per eye and group ("down" T4d+T5d, "up" T4c+T5c), brightness = the
  rate we send; ω, f and the rate, with a gauge marking ω_full.
- **Column 2, the model's flight neurons:** DNp22 left and right (the readout) as the Giant Fibers
  are for the cube, with 1 s rasters; holds and releases on the same axis; VS1-VS8 per side and
  DNp20 (recorded, not read by the game), all from spikes.npz.

**The target is recomputed, then checked:** the runs log Δy and dx to the target but not the opening
itself, so `ship_targets` recomputes it from the level with the run's own opening finder and checks
it against the logged Δy and dx on every ship tick. Any mismatch raises `TargetMismatch`, so a
replay can never show a target the run didn't use.
"""

from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pygame

from stereo_flyness.game import physics as P
from stereo_flyness.interface.encoding import EYE_AHEAD
from stereo_flyness.interface.ship_opening import Opening, OpeningFinder

ROOT = Path(__file__).resolve().parents[3]
SHIP_NEURONS = ROOT / "configs" / "ship_neurons_783.csv"
GROUP_TYPES = {"down": ("T4d", "T5d"), "up": ("T4c", "T5c")}
VS = tuple(f"VS{i}" for i in range(1, 9))
SIDES = ("left", "right")
V_MAX_UP, V_MAX_DOWN = P.SHIP_MAX_UP * 54, P.SHIP_MAX_DOWN * 54  # units/s, as v_req is clipped (D53)
TOL = 1e-6


class TargetMismatch(ValueError):
    """The recomputed target doesn't match what the run logged."""


@lru_cache(maxsize=1)
def ship_neurons(path=SHIP_NEURONS) -> pd.DataFrame:
    return pd.read_csv(path)


def ids(*types: str, side: str | None = None) -> np.ndarray:
    t = ship_neurons()
    sel = t["cell_type"].isin(types) & ((t["side"] == side) if side else True)
    return t.loc[sel, "flywire_id"].to_numpy(np.int64)


def group_counts() -> dict[tuple[str, str], int]:
    """Neurons per (group, side) we drive: "down" T4d+T5d, "up" T4c+T5c."""
    return {(g, s): len(ids(*types, side=s)) for g, types in GROUP_TYPES.items() for s in SIDES}


def variant_tag(run: dict) -> str:
    """B, C, self-motion only, B90 or corrected signs, from run.json, so no replay is mistaken for another."""
    ship = (run.get("modes") or {}).get("ship") or {}
    design = run.get("ship_design") or {"B": "B", "C": "C", "self": "self-motion only"}.get(ship.get("terms"), "?")
    if ship.get("omega_full_deg") not in (None, 30.0) and design == "B":
        design = f"B, {ship['omega_full_deg']:g}°/s"
    if run.get("signs", "original") != "original":
        design += f", {run['signs']} signs"
    return design


def ship_targets(level, timeline, brain: pd.DataFrame) -> dict[int, Opening]:
    """{brain row: target opening} for every ship row with a target, recomputed from the level and
    checked against the row's logged target_dy and target_dx. Raises TargetMismatch on any difference."""
    if "target_dy" not in brain:
        return {}
    finder, out = OpeningFinder(level), {}
    for k, r in enumerate(brain.itertuples(index=False)):
        if r.mode != "ship":
            continue
        view = timeline.at_tick(int(r.tick_seen))
        logged = (r.target_dy, r.target_dx)
        if view.bounds is None:
            raise TargetMismatch(f"row {k}: logged in ship mode, but the replay has no ship area at tick {r.tick_seen}")
        opening, dy = finder.find(SimpleNamespace(x=view.x, y=view.y), view.bounds)
        if opening is None:
            if not pd.isna(logged[0]):
                raise TargetMismatch(f"row {k}: the run logged a target (Δy {logged[0]:.3f}); the replay finds none")
            continue
        dx = max(opening.x0 - (view.x + EYE_AHEAD), P.PLAYER_SIZE)
        if pd.isna(logged[0]) or abs(dy - logged[0]) > TOL or abs(dx - logged[1]) > TOL:
            raise TargetMismatch(f"row {k} (tick {r.tick_seen}): the replay's target gives Δy {dy:.6f}, dx {dx:.6f}; "
                                 f"the run logged Δy {logged[0]}, dx {logged[1]}")
        out[k] = opening
    return out


def draw_target(surface, cam, timeline, tick: int) -> None:
    """The target opening on the game: an outlined white bracket and a line from the ship's eye."""
    from stereo_flyness.viewer.render import font

    brain = getattr(timeline, "brain", None)
    targets = getattr(brain, "targets", None)
    if not targets:
        return
    row = brain.row(tick)
    o = targets.get(row)
    if o is None:
        return
    view = timeline.at_tick(int(brain.brain["tick_seen"].iloc[row]))
    x, top = cam.to_screen(o.x0, o.top)
    _, bottom = cam.to_screen(o.x0, o.bottom)
    arm = 10
    pygame.draw.lines(surface, (255, 255, 255), False, [(x + arm, top), (x, top), (x, bottom), (x + arm, bottom)], 2)
    ex, ey = cam.to_screen(view.x + EYE_AHEAD, view.y)
    _, cy = cam.to_screen(o.x0, o.centre)
    pygame.draw.line(surface, (200, 200, 210), (ex, ey), (x, cy), 1)
    label = font(13).render("target (our code)", True, (255, 255, 255))
    lx = x + 4 if x + 4 + label.get_width() < surface.get_width() else x - 4 - label.get_width()
    surface.blit(label, (lx, top - 18))


# ---- drawing (column helpers come from brain_panel, imported late: brain_panel imports this module)

def _bp():
    from stereo_flyness.viewer import brain_panel
    return brain_panel


def _bar(surface, rect, frac, lit, label):
    bp = _bp()
    if lit:
        level = int(90 + 165 * max(0.0, min(1.0, frac)))
        pygame.draw.rect(surface, (level, level, level), rect)
    pygame.draw.rect(surface, bp.INPUT if lit else bp.INPUT_DIM, rect, width=1)
    text = bp.font(11).render(label, True, bp.COLOURS["outline"] if lit and frac > 0.4 else bp.SMALL)
    surface.blit(text, (rect[0] + rect[2] - text.get_width() - 4, rect[1] + 1))


def _speed_gauge(surface, x, y, h, vy, v_req, used_vy: bool):
    """vy (solid tick) against v_req (hollow diamond), units/s, down to up."""
    bp = _bp()
    span = V_MAX_UP + V_MAX_DOWN

    def at(v):
        return y + h - round(h * (min(max(v, -V_MAX_DOWN), V_MAX_UP) + V_MAX_DOWN) / span)

    pygame.draw.line(surface, bp.INPUT_DIM, (x, y), (x, y + h), 1)
    pygame.draw.line(surface, bp.INPUT_DIM, (x - 5, at(0)), (x + 5, at(0)), 1)
    bp._text(surface, "0", (x + 8, at(0) - 6), bp.SMALL, 10)
    if v_req is not None and not pd.isna(v_req):
        cy = at(v_req)
        pygame.draw.polygon(surface, bp.INPUT, [(x, cy - 6), (x + 6, cy), (x, cy + 6), (x - 6, cy)], width=1)
    if vy is not None and not pd.isna(vy):
        pygame.draw.line(surface, bp.INPUT if used_vy else bp.INPUT_DIM, (x - 9, at(vy)), (x + 9, at(vy)), 3)
    lx = x - 112
    pygame.draw.line(surface, bp.INPUT if used_vy else bp.INPUT_DIM, (lx, y + 16), (lx + 12, y + 16), 3)
    bp._text(surface, "vy" if used_vy else "vy: not in C", (lx + 16, y + 10), bp.INPUT if used_vy else bp.SMALL, 11)
    pygame.draw.polygon(surface, bp.INPUT, [(lx + 6, y + 26), (lx + 11, y + 31), (lx + 6, y + 36), (lx + 1, y + 31)], width=1)
    bp._text(surface, "v_req", (lx + 16, y + 25), bp.INPUT, 11)
    bp._text(surface, "units/s", (lx + 16, y + 40), bp.SMALL, 10)


def draw_ship_input(surface, track, tick, rect) -> None:
    """Column 1 in ship mode: our steering and the motion we drive (our input, never the fly's activity)."""
    bp = _bp()
    x0, y0, w, h = rect
    r = track.brain.iloc[track.row(tick)]
    ship = (track.run.get("modes") or {}).get("ship") or {}
    r_ship = float(ship.get("ship_rate_hz") or 150.0)
    omega_full = float(ship.get("omega_full_deg") or 30.0)
    terms = ship.get("terms", "B")
    eyes = tuple(ship.get("eyes") or SIDES)
    tag = bp.font(13).render(f"[{variant_tag(track.run)}]", True, bp.INPUT)
    surface.blit(tag, (x0 + w - tag.get_width() - 10, y0 + 6))

    bp._text(surface, "OUR STEERING", (x0 + 10, y0 + 26), bp.SMALL, 11)
    dy, dx = r.get("target_dy"), r.get("target_dx")
    target = "no target in range" if dy is None or pd.isna(dy) else f"target Δy {dy:+.1f}   dx {dx:.0f}"
    bp._text(surface, target if terms != "self" else "no target (self-motion only)", (x0 + 10, y0 + 40), bp.INPUT, 14)
    _speed_gauge(surface, x0 + w - 30, y0 + 30, 110, r.get("vy"), r.get("v_req"), used_vy=terms != "C")

    bp._text(surface, "MOTION WE DRIVE", (x0 + 10, y0 + 62), bp.SMALL, 11)
    counts = group_counts()
    group, rate = str(r.get("driven_group") or "none"), float(r.get("rate_hz") or 0.0)
    bx = {"left": x0 + 60, "right": x0 + 192}
    for s in SIDES:
        bp._text(surface, f"{s} eye", (bx[s], y0 + 76), bp.INPUT, 11)
    for i, g in enumerate(("down", "up")):
        y = y0 + 90 + 20 * i
        bp._text(surface, g, (x0 + 10, y), bp.INPUT, 13)
        for s in SIDES:
            lit = g == group and s in eyes and rate > 0
            _bar(surface, (bx[s], y, 124, 15), rate / r_ship if r_ship else 0.0, lit, f"{counts[(g, s)]:,}")

    omega, f = float(r.get("omega_deg") or 0.0), float(r.get("f") or 0.0)
    arrow = {"down": "↓", "up": "↑"}.get(group, " ")
    bp._text(surface, f"ω {arrow} {abs(omega):5.1f}°/s   f {f:.0%}   {rate:.0f} Hz per neuron", (x0 + 10, y0 + 132), bp.INPUT, 14)
    gx, gy, gw = x0 + 10, y0 + 154, w - 90
    pygame.draw.rect(surface, bp.INPUT_DIM, (gx, gy, gw, 6), width=1)
    pygame.draw.rect(surface, bp.INPUT, (gx, gy, round(gw * min(abs(omega), 2 * omega_full) / (2 * omega_full)), 6))
    mx = gx + gw // 2
    pygame.draw.line(surface, bp.AMBER_DIM, (mx, gy - 3), (mx, gy + 9), 2)
    bp._text(surface, f"ω_full {omega_full:g}°/s: f = 100%", (mx + 4, gy + 8), bp.SMALL, 11)
    bp._text(surface, "Image motion from the level's geometry and our target speed,", (x0 + 10, y0 + h - 30), bp.SMALL, 11)
    bp._text(surface, "not from pixels. Our input, computed by our code from the game.", (x0 + 10, y0 + h - 16), bp.SMALL, 11)


def draw_ship_flight(surface, track, timeline, tick, since, rect) -> None:
    """Column 2 in ship mode: DNp22 (the readout), holds and releases, VS1-VS8 and DNp20 (the model's activity)."""
    bp = _bp()
    x0, y0, w, h = rect
    a, b = track.bin(tick, since)
    dn = [g for g in ("DNp22_L", "DNp22_R") if g in track.groups]
    for i, g in enumerate(dn):
        n = track.bin_spikes(g, tick, since)
        cx = x0 + 60 + i * 150
        if n:
            pygame.draw.circle(surface, bp.AMBER, (cx, y0 + 40), 12)
        pygame.draw.circle(surface, bp.AMBER, (cx, y0 + 40), 12, width=2)
        bp._text(surface, f"{bp.gf_label(g)}  {n}", (cx + 17, y0 + 32), bp.AMBER if n else bp.AMBER_DIM, 14)
    bp._text(surface, f"spikes in the last {b - a} tick{'s' if b - a != 1 else ''}"
             + (" (1/60 s)" if b - a == bp.BIN_TICKS else ""), (x0 + 10, y0 + 56), bp.SMALL, 11)
    lx, lw, y = x0 + 80, w - 92, y0 + 72
    lanes = dn + [g for g in track.groups if g not in dn]
    for g in lanes:
        bp._text(surface, bp.gf_label(g), (x0 + 10, y - 1), bp.AMBER, 11)
        bp._raster(surface, lx, y, lw, 9, track.spike_window(g, tick), bp.AMBER)
        y += 12
    bp.mode_lines(surface, track, tick, lx, y0 + 72, lw, y - (y0 + 72))
    # Holds and releases, at the tick the game applied them (one tick after the spikes that made them).
    bp._text(surface, "hold", (x0 + 10, y + 1), bp.PRESS, 11)
    step = lw / bp.RASTER_TICKS
    first = track.row(tick) - bp.RASTER_TICKS + 1
    for t in range(max(1, first), min(tick, timeline.last_tick) + 1):
        view = timeline.ticks[t]
        if view.mode != "ship":
            continue
        xs = lx + (t - first) * step
        if view.held:
            pygame.draw.line(surface, bp.PRESS, (xs, y + 4), (xs + step, y + 4), 2)
        else:
            pygame.draw.polygon(surface, bp.PRESS, [(xs - 2, y + 7), (xs + 2, y + 7), (xs, y + 11)])
    y += 18
    spikes = track.bin_neurons(tick, since)
    for i, s in enumerate(SIDES):
        yy = y + 14 * i
        bp._text(surface, f"VS1-8 {s[0].upper()}", (x0 + 10, yy - 1), bp.AMBER, 11)
        for j, t in enumerate(VS):
            on = any(spikes.get(int(n), 0) for n in ids(t, side=s))
            sq = (x0 + 80 + 14 * j, yy, 10, 10)
            pygame.draw.rect(surface, bp.AMBER if on else bp.AMBER_DIM, sq, width=0 if on else 1)
    dx0 = x0 + 80 + 14 * 8 + 16
    for i, s in enumerate(SIDES):
        on = any(spikes.get(int(n), 0) for n in ids("DNp20", side=s))
        c = (dx0 + 7 + 22 * i, y + 11)
        if on:
            pygame.draw.circle(surface, bp.AMBER, c, 6)
        pygame.draw.circle(surface, bp.SMALL, c, 7, width=1)
    bp._text(surface, "DNp20 L R", (dx0 + 52, y - 1), bp.SMALL, 11)
    bp._text(surface, "recorded only", (dx0 + 52, y + 12), bp.SMALL, 11)
    bp._text(surface, "VS: motion cells that stabilise flight. Model VS cells spike;", (x0 + 10, y0 + h - 44), bp.SMALL, 11)
    bp._text(surface, "real ones are mostly graded. DNp22: any spike releases.", (x0 + 10, y0 + h - 30), bp.SMALL, 11)
    bp._text(surface, "Last 1 s. ▼ released tick, ─ held tick (silence holds).", (x0 + 10, y0 + h - 16), bp.SMALL, 11)
