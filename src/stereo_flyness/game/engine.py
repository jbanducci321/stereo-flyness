"""The game engine: advances a level one 240 Hz tick at a time (docs/game_physics.md).

The only input is whether the button is held during a tick (D23, to be logged). The bot, test
scripts and, later, the brain interface all drive the game through `Game.tick`. The engine is
deterministic: the same inputs always produce the same run.

Per-tick order, as in the game [§2]:
1. update vertical velocity (jump or gravity);
2. move: x by the horizontal speed, y by the new vertical velocity;
3. resolve collisions (so far only the ground).
"""

from stereo_flyness.game import physics as P
from stereo_flyness.game.level import Level
from stereo_flyness.game.player import Player


class Game:
    def __init__(self, level: Level):
        self.level = level
        self.player = Player(mode=level.start_mode)
        self.ticks = 0

    @property
    def time(self) -> float:
        """Seconds of game time elapsed."""
        return self.ticks / P.TICKS_PER_SECOND

    def tick(self, held: bool) -> None:
        """Advance one 240 Hz tick with the button `held` (True) or released (False)."""
        p = self.player
        if not p.alive:
            return
        self._update_velocity(p, held)
        p.x += P.X_PER_TICK
        p.y += p.vy * P.TICK_DT_Y
        self._collide_ground(p)
        self.ticks += 1

    def _update_velocity(self, p: Player, held: bool) -> None:
        """Cube jump and gravity [§3].

        A jump happens on any tick where the cube is on the ground (as of the previous tick's
        collisions) and the button is held.

        Gravity also applies on the jump tick. Read literally, gdp's `updateJump` skips gravity on
        that tick, but that gives a 66.5-unit jump. The community figure (2.133 blocks = 64.0
        units) and Jacob's video (~64) match applying it, which gives 63.97. See §3.
        """
        if p.on_ground and held:
            p.vy = P.CUBE_JUMP_VELOCITY
            p.on_ground = False
        p.vy -= P.CUBE_GRAVITY * P.TICK_DT_Y
        if p.vy < -P.MAX_FALL_SPEED:
            p.vy = -P.MAX_FALL_SPEED

    def _collide_ground(self, p: Player) -> None:
        """The ground surface is y = 0: snap onto it and stop falling."""
        if p.bottom <= 0.0:
            p.y = P.HALF_PLAYER
            p.vy = 0.0
            p.on_ground = True
        else:
            p.on_ground = False
