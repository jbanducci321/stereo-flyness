"""Cube level generator: seeded, physics-based, always bot-beatable (D26)."""

import pytest

from stereo_flyness.game.bot import BotResult, replay, solve
from stereo_flyness.game.generator import (
    CUBE_TIERS, END_RUNWAY, GRID, START_RUNWAY, UNITS_PER_SECOND, build_cube, generate_cube,
)
from stereo_flyness.game.objects import KIND_SIZES

STEREO_MADNESS_KINDS = set(KIND_SIZES)  # block, slab, spike, small_spike, half_spike, pit (D6)


def test_same_seed_same_level_and_different_seeds_differ():
    a, b = build_cube(7, "medium"), build_cube(7, "medium")
    assert a.to_dict() == b.to_dict()
    assert build_cube(8, "medium").to_dict() != a.to_dict()
    assert build_cube(7, "medium", attempt=1).to_dict() != a.to_dict()  # re-rolls change the level


@pytest.mark.parametrize("difficulty", list(CUBE_TIERS))
def test_levels_are_bot_beatable_and_well_formed(difficulty):
    for seed in range(8):
        g = generate_cube(seed, difficulty)
        lv = g.level
        assert replay(lv, g.bot).summary.completed  # the bot's winning inputs really finish
        assert {b.kind for b in lv.boxes} <= STEREO_MADNESS_KINDS
        assert min(b.x0 for b in lv.boxes) >= START_RUNWAY - GRID  # nothing in the start runway
        assert max(b.x1 for b in lv.boxes) <= lv.length - END_RUNWAY + GRID
        assert 29 <= lv.length / UNITS_PER_SECOND <= 33  # ~30 s
        assert all(((b.x0 + b.x1) / 2 - GRID / 2) % GRID == pytest.approx(0) for b in lv.boxes)  # on the grid
        assert lv.portals == [] and lv.start_mode == "cube"


def test_harder_tiers_pack_more_obstacles():
    counts = {d: sum(len(build_cube(s, d).boxes) for s in range(10)) for d in CUBE_TIERS}
    assert counts["easy"] < counts["medium"] < counts["hard"]


def test_unbeatable_candidates_are_rerolled():
    calls = []

    def fails_twice(level):
        calls.append(level.source)
        return BotResult(success=len(calls) > 2, frame_inputs=[], frame_ticks=4, nodes=1, farthest_x=0)

    g = generate_cube(3, "hard", validate=fails_twice)
    assert g.attempts == 3 and "attempt 2" in g.level.source
    assert g.level.to_dict() == build_cube(3, "hard", attempt=2).to_dict()


def test_level_records_how_it_was_made():
    lv = generate_cube(5, "easy").level
    assert lv.name == "cube-easy-5" and "seed 5" in lv.source and "easy" in lv.source
