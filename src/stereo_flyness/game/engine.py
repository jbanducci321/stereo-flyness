"""The game engine: advances a level one 240 Hz tick at a time (docs/game_physics.md).

The only input is whether the button is held during a tick (D23, to be logged). The bot, test
scripts and, later, the brain interface all drive the game through `Game.tick`. The engine is
deterministic: the same inputs always produce the same run.

Per-tick order, as in the game [§2]:
1. update vertical velocity (jump or gravity);
2. move: x by the horizontal speed, y by the new vertical velocity;
3. resolve collisions: the ground or ship floor/ceiling, solids (landing, bumping, death),
   hazards, then portals;
4. check for the end of the level.
"""

import bisect
from dataclasses import dataclass

from stereo_flyness.game import physics as P
from stereo_flyness.game.level import Box, Level, Portal, ship_bounds
from stereo_flyness.game.player import Player

_MAX_BOX_WIDTH = 30.0  # widest object kind; bounds the broad-phase search


@dataclass(frozen=True)
class Death:
    """What killed the player, and where."""

    kind: str
    source_id: int | None
    x: float
    y: float
    tick: int


class Game:
    def __init__(self, level: Level):
        self.level = level
        self.player = Player(mode=level.start_mode)
        self.ticks = 0
        self.death: Death | None = None
        self.finished = False
        # What happened in the last tick: "jump", "land", "portal_ship", "portal_cube", "death",
        # "finish". Used by the run recorder and, later, replay sound effects.
        self.events: list[str] = []
        self._box_x0 = [b.x0 for b in level.boxes]  # level.boxes is sorted by x0
        self._snapped_to: Box | None = None  # last solid landed on, for stair snapping [§6]
        self._snap_offset = 0.0
        self._next_portal = 0  # level.portals is sorted by x; each triggers once
        # Floor and ceiling of the current ship area (None in cube mode)
        self.bounds: tuple[float, float] | None = (
            ship_bounds(self.player.y) if self.player.mode == "ship" else None
        )

    @property
    def time(self) -> float:
        """Seconds of game time elapsed."""
        return self.ticks / P.TICKS_PER_SECOND

    @property
    def over(self) -> bool:
        return self.death is not None or self.finished

    @property
    def progress(self) -> float:
        """Fraction of the level completed (0 to 1)."""
        return min(self.player.x / self.level.length, 1.0)

    def tick(self, held: bool) -> None:
        """Advance one 240 Hz tick with the button `held` (True) or released (False)."""
        if self.over:
            return
        self.events = []
        p = self.player
        last_y, was_on_ground = p.y, p.on_ground
        if p.mode == "cube" and p.on_ground and held:
            self.events.append("jump")
        self._update_velocity(p, held)
        p.x += P.X_PER_TICK
        p.y += p.vy * P.TICK_DT_Y
        self.ticks += 1
        self._collide(p, p.y - last_y)
        if p.alive and p.on_ground and not was_on_ground:
            self.events.append("land")
        if p.alive and p.x >= self.level.length:
            self.finished = True
            self.events.append("finish")

    # -- velocity -----------------------------------------------------------------

    def _update_velocity(self, p: Player, held: bool) -> None:
        if p.mode == "ship":
            self._update_ship_velocity(p, held)
        else:
            self._update_cube_velocity(p, held)

    @staticmethod
    def _update_ship_velocity(p: Player, held: bool) -> None:
        """Ship acceleration [§4, gdp `updateJump` ship branch].

        Held: accelerate up, harder while falling. Released: accelerate down, harder while still
        rising. Then clamp to the speed limits.
        """
        falling = p.vy < 0
        if held:
            factor = P.SHIP_HOLD_FALLING if falling else P.SHIP_HOLD_RISING
            p.vy += P.SHIP_GRAVITY * P.TICK_DT_Y * factor
        else:
            factor = P.SHIP_RELEASE_FALLING if falling else P.SHIP_RELEASE_RISING
            p.vy -= P.SHIP_GRAVITY * P.TICK_DT_Y * factor
        p.vy = min(max(p.vy, -P.SHIP_MAX_DOWN), P.SHIP_MAX_UP)

    @staticmethod
    def _update_cube_velocity(p: Player, held: bool) -> None:
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

    # -- collisions -----------------------------------------------------------------

    def _nearby(self, p: Player) -> list[Box]:
        """Boxes whose x range can overlap the player's (broad phase)."""
        lo = bisect.bisect_left(self._box_x0, p.x - P.HALF_PLAYER - _MAX_BOX_WIDTH)
        hi = bisect.bisect_right(self._box_x0, p.x + P.HALF_PLAYER)
        return self.level.boxes[lo:hi]

    def _collide(self, p: Player, dy: float) -> None:
        p.on_ground = False
        if p.mode == "ship":
            self._collide_ship_bounds(p)
        elif p.bottom <= 0.0:  # the ground surface, y = 0
            p.y, p.vy, p.on_ground = P.HALF_PLAYER, 0.0, True

        nearby = self._nearby(p)
        for b in nearby:
            if b.solid and _overlaps(p, b, P.PLAYER_SIZE):
                self._collide_solid(p, b, dy)
                if not p.alive:
                    return
        for b in nearby:
            if not b.solid and _overlaps(p, b, P.PLAYER_SIZE):
                self._die(p, b)
                return
        self._check_portals(p)

    def _collide_ship_bounds(self, p: Player) -> None:
        """The ship slides along its area's floor and ceiling without dying [§4]."""
        floor, ceiling = self.bounds
        if p.bottom <= floor:
            p.y, p.vy, p.on_ground = floor + P.HALF_PLAYER, 0.0, True
        elif p.top >= ceiling:
            p.y, p.vy = ceiling - P.HALF_PLAYER, 0.0

    def _collide_solid(self, p: Player, b: Box, dy: float) -> None:
        """Player vs a solid [§5, gdp `collidedWithObjectInternal`].

        - Land on top if the player's bottom is within the snap distance of the solid's top
          (10 for the cube, 6 for the ship), now or before this tick's move, unless still rising.
        - Ship only: bump along the underside if the player's top is within 6 of the solid's
          bottom (now or before the move), while not moving down.
        - Otherwise the player dies only if the solid touches the 9 x 9 inner hitbox. The cube
          can graze a block's edge, or clip into its underside, and survive.
        """
        ship = p.mode == "ship"
        snap = P.SNAP_UP_SHIP if ship else P.SNAP_UP_CUBE
        reach = p.bottom + snap
        if reach >= b.y1 or reach - dy >= b.y1:
            if p.vy > 0:
                return  # rising past the top edge: neither lands nor dies
            p.y = b.y1 + P.HALF_PLAYER
            p.vy = max(0.0, p.vy)
            p.on_ground = True
            if not ship:
                self._stair_snap(p, b)
            return
        if ship:
            head = p.top - snap
            if (b.y0 >= head or head - dy <= b.y0) and p.vy >= 0:
                p.y = b.y0 - P.HALF_PLAYER
                p.vy = 0.0
                return
        if _overlaps(p, b, P.INNER_HITBOX):
            self._die(p, b)

    def _check_portals(self, p: Player) -> None:
        """Switch mode when the 30 x 30 hitbox touches the next portal [§4, §5].

        Each portal triggers once. A ship portal sets new ship bounds from its height (even
        when already a ship). Vertical speed carries over unchanged (an assumption; §8).
        """
        portals = self.level.portals
        while self._next_portal < len(portals):
            portal = portals[self._next_portal]
            if p.x + P.HALF_PLAYER < portal.x - P.PORTAL_WIDTH / 2:
                return  # not reached yet
            if _touches_portal(p, portal):
                p.mode = portal.mode
                self.bounds = ship_bounds(portal.y) if portal.mode == "ship" else None
                self.events.append(f"portal_{portal.mode}")
            elif p.x - P.HALF_PLAYER <= portal.x + P.PORTAL_WIDTH / 2:
                return  # within its x range but not touching (yet)
            self._next_portal += 1  # triggered, or passed without touching

    def _stair_snap(self, p: Player, b: Box) -> None:
        """Nudge x so held-jump staircases stay evenly spaced [§6, gdp `checkSnapJumpToObject`].

        If this solid sits one of the standard step offsets from the previous landed solid, x is
        moved towards keeping the same offset from it as from the previous one (by at most
        STAIR_SNAP_TOLERANCE).
        """
        cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
        prev, x_before = self._snapped_to, p.x
        if prev is not None and prev is not b:
            dx = cx - (prev.x0 + prev.x1) / 2
            dyc = cy - (prev.y0 + prev.y1) / 2
            tol = P.STAIR_SNAP_TOLERANCE
            if any(abs(dx - sx) <= tol and abs(dyc - sy) <= tol for sx, sy in P.STAIR_STEPS):
                target = cx + self._snap_offset
                p.x = min(max(target, x_before - tol), x_before + tol)
        self._snapped_to = b
        self._snap_offset = x_before - cx

    def _die(self, p: Player, b: Box) -> None:
        p.alive = False
        self.death = Death(b.kind, b.source_id, p.x, p.y, self.ticks)
        self.events.append("death")


def _touches_portal(p: Player, portal: Portal) -> bool:
    hw, hh = P.PORTAL_WIDTH / 2, P.PORTAL_HEIGHT / 2
    return not (p.x + P.HALF_PLAYER < portal.x - hw or portal.x + hw < p.x - P.HALF_PLAYER
                or p.top < portal.y - hh or portal.y + hh < p.bottom)


def _overlaps(p: Player, b: Box, size: float) -> bool:
    """Does a `size` x `size` square centred on the player touch box `b`? Touching counts."""
    h = size / 2
    return not (p.x + h < b.x0 or b.x1 < p.x - h or p.y + h < b.y0 or b.y1 < p.y - h)
