"""The closed loop for cube mode: the fly's brain plays the game, one 240 Hz tick at a time.

Order within a tick (D40), for tick i = 0, 1, 2, ...:
  1. the game state after i ticks is encoded (D41) and sets the input rates of brain frame i;
  2. the brain runs frame i, exactly one game tick long (`run_frames(..., exact=True)`);
  3. the jump rule (D42) turns frame i's spikes into `held`, and the game advances one tick.
So the brain's response to what it saw reaches the game one tick later, the same for every press.

With a `policy` (e.g. the bot's winning inputs), the brain still sees everything and is
recorded, but the policy drives the cube, not the fly. Such runs are labelled "bot" and can
never be shown as the fly playing (D43 recruitment runs; hard rule 10, D19).

Every choice here is ours, not the fly's: the encoding (D41) and the jump rule (D42).
"""

from brian2 import Hz, ms

from stereo_flyness.game.physics import TICKS_PER_SECOND, X_PER_TICK
from stereo_flyness.interface.fly_log import FlyRecorder

TICK = 1000 / TICKS_PER_SECOND * ms  # one game tick of brain time (D40)
GF_GROUPS = ("GF_R", "GF_L")


def jump_rule(counts: dict) -> bool:
    """D42: press on the next tick if either Giant Fiber spiked in this frame."""
    return any(int(counts[g].sum()) > 0 for g in GF_GROUPS)


def play(game, stepper, encoder, policy=None, stuck_ids=(), meta: dict | None = None,
         chunk_frames: int = 120, max_ticks: int | None = None, **flag_settings) -> FlyRecorder:
    """Play `game` to the end. `stepper` is a `BrainStepper` with one input group "loom"
    (`encoder.ids`) and watch groups including "GF_R" and "GF_L".

    Without `policy`, the fly drives (D42). With `policy` (a function of the game returning
    `held`), the policy drives and the brain only watches. Returns the `FlyRecorder`, finished,
    ready to `save`. The brain runs in chunks of `chunk_frames` ticks (exact frames continue
    across chunks), so it stops at most one chunk after the game ends.
    """
    max_ticks = max_ticks or int(game.level.length / X_PER_TICK) + 10 * TICKS_PER_SECOND
    rec = FlyRecorder(game, stepper.flyids, "fly" if policy is None else "bot", stuck_ids, meta, **flag_settings)
    state = {"row": None, "done": False}

    def see():
        p = game.player
        loom = encoder.encode(p)
        stepper.set_rate("loom", encoder.rates(loom) * Hz)
        held_next = None if policy is None else bool(policy(game))
        state["row"] = {"tick_seen": game.ticks, "theta_deg": loom.theta_deg, "gap": loom.gap, "f": loom.f,
                        "rate_hz": loom.rate_hz, **{f"driven_{s}_{t}": n for (s, t), n in loom.driven.items()}}
        state["policy_held"] = held_next

    def on_frame(i, counts):
        if state["done"]:
            return
        fly_press = jump_rule(counts)
        held = fly_press if policy is None else state["policy_held"]
        row = {**state["row"], **{f"spikes_{g}": int(c.sum()) for g, c in counts.items()}, "fly_press": fly_press}
        game.tick(held)
        rec.frame(game, held, row, stepper.last_counts)
        if game.over or game.ticks >= max_ticks:
            state["done"] = True
        else:
            see()

    see()
    while not state["done"]:
        stepper.run_frames(chunk_frames, TICK, on_frame, exact=True)
    rec.finish(game, {"theta_full_deg": encoder.theta_full_deg, "rate_hz": encoder.rate_hz, "mode": encoder.mode,
                      "presses": int(sum(r["held"] for r in rec.rows))})
    return rec
