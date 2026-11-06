"""The closed loop in any mode: each game mode has its own input encoding and output rule (Step 5/6).

`closed_loop.play` is the cube loop every Step 2-4 run used, and stays exactly as it is. This is
the general version for ship levels, mixed levels and Stereo Madness: a *controller* per mode says
which neurons its encoding drives, what it drives them with, and how spikes become `held`.

Order within a tick is D40's, for tick i:
  1. the controller of the mode the player is in after i ticks encodes the game state and sets its
     input rates for brain frame i; every other mode's inputs are set to 0;
  2. the brain runs frame i, exactly one game tick long;
  3. **that same controller's output rule** turns frame i's spikes into `held` for tick i + 1.
So the rule that reads the spikes is always the one for the mode the brain was shown. If a portal
switches the mode on tick i + 1, that one tick is still decided by the previous mode's rule, the
same one-tick delay as every press (D40).

The ship's encoding and output rule are Shannyn's design (docs/notes/ship_brief.md). Until it's
logged, `ShipNotDesigned` stands in for it and stops any run that reaches ship mode, so no ship
behaviour is ever invented here.
"""

from dataclasses import dataclass, field

import numpy as np
from brian2 import Hz

from stereo_flyness.game.physics import TICKS_PER_SECOND, X_PER_TICK
from stereo_flyness.interface.closed_loop import TICK, jump_rule
from stereo_flyness.interface.fly_log import FlyRecorder


class Controller:
    """One game mode's encoding and output rule. Subclasses fill in all four."""

    mode: str = ""
    groups: dict[str, list[int]] = {}  # input group name -> FlyWire IDs it drives

    def encode(self, player) -> tuple[dict[str, np.ndarray], dict]:
        """Per-group rates (Hz, in `groups` order) and the row logged for this tick (hard rule 10)."""
        raise NotImplementedError

    def output(self, counts: dict) -> bool:
        """`held` for the next tick, from this frame's watched spike counts."""
        raise NotImplementedError

    def settings(self) -> dict:
        """What the run summary records about this mode's encoding and rule."""
        return {}


class CubeController(Controller):
    """The cube as in Steps 2-4: D41's looming encoding (CubeEncoder) and D42's jump rule."""

    mode = "cube"

    def __init__(self, encoder):
        self.encoder = encoder
        self.groups = {"loom": list(encoder.ids)}

    def encode(self, player):
        loom = self.encoder.encode(player)
        row = {"theta_deg": loom.theta_deg, "gap": loom.gap, "f": loom.f, "rate_hz": loom.rate_hz,
               **{f"driven_{s}_{t}": n for (s, t), n in loom.driven.items()}}
        return {"loom": self.encoder.rates(loom)}, row

    def output(self, counts):
        return jump_rule(counts)

    def settings(self):
        e = self.encoder
        return {"theta_full_deg": e.theta_full_deg, "rate_hz": e.rate_hz, "mode": e.mode, "rate_scaling": e.rate_scaling}


class ShipNotDesigned(Controller):
    """Stands in for the ship until its design is logged (Step 5). Any run that reaches ship mode stops."""

    mode = "ship"
    groups = {}
    MESSAGE = ("The ship's encoding and output rule aren't designed yet (Step 5, docs/notes/ship_brief.md). "
               "This run reached ship mode, so it stops rather than invent ship behaviour.")

    def encode(self, player):
        raise NotImplementedError(self.MESSAGE)

    def output(self, counts):
        raise NotImplementedError(self.MESSAGE)


@dataclass
class _State:
    row: dict | None = None
    controller: Controller | None = None
    policy_held: bool | None = None
    done: bool = False
    active_groups: set = field(default_factory=set)


def play_modes(game, stepper, controllers: dict[str, Controller], policy=None, stuck_ids=(), meta: dict | None = None,
               chunk_frames: int = 120, max_ticks: int | None = None, **flag_settings) -> FlyRecorder:
    """Play `game` to the end with one controller per mode (`{"cube": ..., "ship": ...}`).

    `stepper` must have an input group for every controller group, and the watch groups the output
    rules read. As in `closed_loop.play`, a `policy` drives instead of the fly (labelled "bot"),
    while the brain still sees everything and is recorded.
    """
    for mode, c in controllers.items():
        if c.mode != mode:
            raise ValueError(f"controller for {mode!r} says it's for {c.mode!r}")
    sizes = {g: len(ids) for c in controllers.values() for g, ids in c.groups.items()}
    groups = [g for c in controllers.values() for g in c.groups]
    if len(groups) != len(sizes):
        raise ValueError("two modes share an input group name")
    max_ticks = max_ticks or int(game.level.length / X_PER_TICK) + 10 * TICKS_PER_SECOND
    stimulated = sorted({i for c in controllers.values() for ids in c.groups.values() for i in ids})
    rec = FlyRecorder(game, stepper.flyids, "fly" if policy is None else "bot", stuck_ids, meta,
                      stimulated_ids=stimulated, **flag_settings)
    state = _State()

    def see():
        p = game.player
        if p.mode not in controllers:
            raise KeyError(f"no controller for mode {p.mode!r} (have {sorted(controllers)})")
        c = controllers[p.mode]
        rates, row = c.encode(p)
        for g in groups:  # the shown mode's inputs; every other mode's inputs off (rates start at 0)
            if g in c.groups:
                stepper.set_rate(g, rates[g] * Hz)
            elif g in state.active_groups:
                stepper.set_rate(g, np.zeros(sizes[g]) * Hz)
        state.active_groups = set(c.groups)
        state.controller = c
        state.row = {"tick_seen": game.ticks, "mode": p.mode, **row}
        state.policy_held = None if policy is None else bool(policy(game))

    def on_frame(i, counts):
        if state.done:
            return
        fly_press = state.controller.output(counts)
        held = fly_press if policy is None else state.policy_held
        row = {**state.row, **{f"spikes_{g}": int(c.sum()) for g, c in counts.items()}, "fly_press": fly_press}
        game.tick(held)
        rec.frame(game, held, row, stepper.last_counts)
        if game.over or game.ticks >= max_ticks:
            state.done = True
        else:
            see()

    see()
    while not state.done:
        stepper.run_frames(chunk_frames, TICK, on_frame, exact=True)
    extra = {"modes": {m: c.settings() for m, c in controllers.items()},
             "presses": int(sum(r["held"] for r in rec.rows))}
    if "cube" in controllers:  # the same top-level fields as cube runs, so the Step 2-4 tools read them
        extra.update(controllers["cube"].settings())
    rec.finish(game, extra)
    return rec
