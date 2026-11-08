"""No-brain players, the references real runs are read against (D48; always press: Step 4 draft).

- **Never press:** the floor.
- **Random presses:** each tick a press with probability p (chance).
- **Always press:** a press on every tick, so the cube jumps again each time it lands. Added for
  Step 4 (docs/notes/step4_proposal.md, section 5): a control brain whose Giant Fiber fires
  nonstop plays like this, so its result can be read against it, not against the floor.

`play` is the game loop scripts/reference_flies.py uses. A press only counts in the listed modes
(the cube, by default, as in Step 2), and the decision after tick i holds tick i + 1, as for the
fly (D40/D42).

Ship (Step 5, before any ship design; docs/notes/ship_brief.md): `play(..., modes=("ship",))`
with `never` (never hold: the ship falls to the floor and slides) and `always` (always hold: it
climbs to the ceiling and slides). Random holds need a rate, which D48 took from the fly's own
presses, so the ship's random reference waits for the ship baseline.
"""

from collections.abc import Callable

from stereo_flyness.game.engine import Game


def play(level, press: Callable[[Game], bool], modes: tuple[str, ...] = ("cube",)) -> dict:
    """One game where `press(game)` decides, after each tick, whether the next tick is held.

    `press` is only asked while the player is in one of `modes`; otherwise the tick isn't held.
    """
    game, held = Game(level), False
    while not game.over:
        game.tick(held)
        held = game.player.mode in modes and press(game)
    d = game.death
    return {"completed": game.finished, "progress": game.progress, "ticks": game.ticks,
            "death": None if d is None else f"{d.kind} at x {d.x:.0f}"}


def never(game: Game) -> bool:
    return False


def always(game: Game) -> bool:
    return True


def random_presses(p: float, rng) -> Callable[[Game], bool]:
    """Presses with probability p on each tick, from `rng` (a numpy Generator with a fixed seed)."""
    return lambda game: rng.random() < p
