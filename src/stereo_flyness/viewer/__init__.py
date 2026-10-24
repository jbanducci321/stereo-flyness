"""Replay viewer (Step 1.3, D19): draws and plays back recorded runs.

Depends on `game/` (levels, run logs); `game/` never depends on the viewer. Drawing uses pygame and
works without a window, so tests and video export run headless.
"""

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
