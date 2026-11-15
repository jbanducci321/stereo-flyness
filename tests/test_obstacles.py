"""Obstacle groups (iteration 2): each generator chunk becomes one group with the right type."""

import random

import pytest

from stereo_flyness.experiments import obstacles as O
from stereo_flyness.game import generator as G
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox

BASE = {"spike1": "spike1", "spike2": "spike2", "spike3": "spike3", "block": "block", "stairs": "stairs",
        "platform": "platform", "slab_bridge": "slab_bridge", "slab_hops": "slab_hops"}


def _level(objs, x=600.0):
    return Level("t", "test", x + 1200, [Box(k, *hitbox(k, x + ox, oy)) for k, ox, oy in objs])


@pytest.mark.parametrize("name", list(G.CUBE_CHUNKS))
def test_each_cube_chunk_is_one_group_of_its_type(name):
    for difficulty, tier in G.CUBE_TIERS.items():
        for seed in range(20):
            objs, _ = G.CUBE_CHUNKS[name](random.Random(seed), tier)
            gs = O.groups(_level(objs))
            assert len(gs) == 1 and gs[0].type.startswith(BASE[name]), (difficulty, seed, gs[0].type)


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_generated_levels_split_into_their_chunks(monkeypatch, difficulty):
    for seed in range(5):
        placed = []
        wrapped = {n: (lambda n, f: lambda rng, tier: (placed.append(n), f(rng, tier))[1])(n, f)
                   for n, f in G.CUBE_CHUNKS.items()}
        monkeypatch.setattr(G, "CUBE_CHUNKS", wrapped)
        level = G.build_cube(seed, difficulty)
        monkeypatch.undo()
        types = [g.type for g in O.groups(level)]
        assert len(types) == len(placed)
        assert all(t.startswith(BASE[n]) for t, n in zip(types, placed)), list(zip(types, placed))


def test_spaced_pairs_and_stair_widths():
    assert O.classify(_level([("spike", 15, 15), ("spike", 105, 15)]).boxes) == "spaced_pair (gap 2)"
    assert O.classify(_level([("spike", 15, 15), ("block", 75, 15)]).boxes) == "spaced_pair (gap 1, block)"
    stairs = [("block", 15, 15), ("block", 135, 15), ("block", 135, 45)]
    assert O.classify(_level(stairs).boxes) == "stairs (1-wide)"


def test_outcomes_mark_the_group_the_cube_died_at():
    gs = O.groups(_level([("spike", 15, 15), ("spike", 315, 15), ("spike", 615, 15)]))
    assert O.outcomes(gs, False, 600 + 315 + 3) == ["cleared", "died", "not reached"]
    assert O.outcomes(gs, True, None) == ["cleared"] * 3


def test_isolated_keeps_the_shape_on_the_grid():
    g = O.groups(_level([("block", 15, 15), ("spike", 45, 15)], x=1830))[0]
    lone = O.isolated(g)
    assert O.groups(lone)[0].type == g.type and O.shape_key(O.groups(lone)[0]) == O.shape_key(g)
    assert lone.boxes[0].x0 == 600
