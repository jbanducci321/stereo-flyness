"""The player's state. Positions are the centre of the 30 x 30 hitbox, in level units (ground y = 0)."""

from dataclasses import dataclass

from stereo_flyness.game.physics import HALF_PLAYER


@dataclass
class Player:
    x: float = 0.0
    y: float = HALF_PLAYER  # resting on the ground
    vy: float = 0.0  # units per 1/60-s frame, up is positive
    mode: str = "cube"
    on_ground: bool = True
    alive: bool = True

    @property
    def bottom(self) -> float:
        return self.y - HALF_PLAYER

    @property
    def top(self) -> float:
        return self.y + HALF_PLAYER
