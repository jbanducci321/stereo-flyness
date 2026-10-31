"""The closed loop for cube mode: the fly's brain plays the game, one 240 Hz tick at a time.

Order within a tick (D40), for tick i = 0, 1, 2, ...:
  1. the game state after i ticks is encoded (D41) and sets the input rates of brain frame i;
  2. the brain runs frame i, exactly one game tick long (`run_frames(..., exact=True)`);
  3. the jump rule (D42) turns frame i's spikes into `held`, and the game advances one tick.
So the brain's response to what it saw reaches the game one tick later, the same for every press.

Every choice here is ours, not the fly's: the encoding (D41) and the jump rule (D42).
"""

from dataclasses import dataclass, field

import numpy as np
from brian2 import Hz, ms

from stereo_flyness.game.physics import TICKS_PER_SECOND, X_PER_TICK

TICK = 1000 / TICKS_PER_SECOND * ms  # one game tick of brain time (D40)
GF_GROUPS = ("GF_R", "GF_L")


def jump_rule(counts: dict) -> bool:
    """D42: press on the next tick if either Giant Fiber spiked in this frame."""
    return any(int(counts[g].sum()) > 0 for g in GF_GROUPS)


@dataclass
class ClosedLoopRun:
    """One closed-loop run: a row per tick (game state, our input, the fly's spikes) and a summary."""
    ticks: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def play(game, stepper, encoder, chunk_frames: int = 120, max_ticks: int | None = None,
         log_active: bool = True) -> ClosedLoopRun:
    """Play `game` to the end with the fly's brain: `stepper` is a `BrainStepper` built with one
    input group "loom" (`encoder.ids`) and watch groups including "GF_R" and "GF_L".

    The brain runs in chunks of `chunk_frames` ticks (exact frames continue across chunks), so
    a run stops at most one chunk after the game ends. Each tick's row records the game state
    the brain saw, the encoding (θ, f, driven counts: our input, kept apart from the fly's
    spikes, hard rule 10), every watched group's spike count, the press, and the game's events.
    """
    max_ticks = max_ticks or int(game.level.length / X_PER_TICK) + 10 * TICKS_PER_SECOND
    run = ClosedLoopRun()
    state = {"loom": None, "row": None, "done": False}

    def see():
        p = game.player
        loom = encoder.encode(p)
        stepper.set_rate("loom", encoder.rates(loom) * Hz)
        state["loom"] = loom
        state["row"] = {"tick": game.ticks, "x": p.x, "y": p.y, "vy": p.vy, "mode": p.mode,
                        "on_ground": p.on_ground, "theta_deg": loom.theta_deg, "gap": loom.gap, "f": loom.f,
                        "rate_hz": loom.rate_hz,
                        **{f"driven_{s}_{t}": n for (s, t), n in loom.driven.items()}}

    def on_frame(i, counts):
        if state["done"]:
            return
        held = jump_rule(counts)
        row = state["row"]
        row.update({f"spikes_{g}": int(c.sum()) for g, c in counts.items()})
        if log_active:
            row["active_neurons"] = int(np.count_nonzero(stepper.last_counts))
        row["held"] = held
        game.tick(held)
        row["events"] = ";".join(game.events)
        run.ticks.append(row)
        if game.over or game.ticks >= max_ticks:
            state["done"] = True
        else:
            see()

    see()
    while not state["done"]:
        stepper.run_frames(chunk_frames, TICK, on_frame, exact=True)

    d = game.death
    run.summary = {
        "driver": "fly",  # the brain controlled the cube (bot-driven runs say "bot")
        "level": game.level.name, "completed": game.finished, "progress": game.progress,
        "ticks": game.ticks, "seconds": game.ticks / TICKS_PER_SECOND,
        "presses": int(sum(r["held"] for r in run.ticks)),
        "jumps": int(sum("jump" in r["events"].split(";") for r in run.ticks)),
        "death": None if d is None else {"kind": d.kind, "x": d.x, "y": d.y, "tick": d.tick},
        "theta_full_deg": encoder.theta_full_deg, "rate_hz": encoder.rate_hz, "mode": encoder.mode,
    }
    return run
