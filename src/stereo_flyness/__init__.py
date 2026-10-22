"""stereo-flyness: a FlyWire connectome model driving a minimal Geometry Dash-style game.

The package is split so that what the fly's wiring does and what our code does stay apart:

- ``brain``: loads the connectome and runs the simulation. Synaptic weights are frozen.
- ``game``: deterministic game physics and levels. Knows nothing about the brain.
- ``interface``: every design choice that connects the two (input encoding, output
  readout, mode switching, tunable dials). Anything here is ours, not the fly's.
"""
