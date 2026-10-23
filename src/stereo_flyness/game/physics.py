"""Geometry Dash 2.2 physics constants (normal speed, normal size, normal gravity).

Every value comes from docs/game_physics.md (section in brackets), which cites its source.
Velocities are in GD units per 1/60 s ("per frame"), as in the game.
"""

# Time [§1]
TICKS_PER_SECOND = 240
TICK_DT = 0.25  # 1/60-s frames per tick; the game's per-tick `dt`
VERTICAL_TIME_SCALE = 0.9  # vertical motion runs at 0.9 x dt
TICK_DT_Y = TICK_DT * VERTICAL_TIME_SCALE

# Horizontal speed [§1]
PLAYER_SPEED = 0.9
SPEED_MULTIPLIER = 5.77000189
X_PER_TICK = TICK_DT * SPEED_MULTIPLIER * PLAYER_SPEED  # 1.29825 units -> 311.58 units/s

# Player [§5]
PLAYER_SIZE = 30.0  # outer hitbox, square, centred on the player
HALF_PLAYER = PLAYER_SIZE / 2

# Cube [§3]
CUBE_JUMP_VELOCITY = 11.1800318
CUBE_GRAVITY = 0.958199024
MAX_FALL_SPEED = 15.0  # vy is clamped to >= -15 while falling
