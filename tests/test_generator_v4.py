"""Generator v4 (iteration 2, docs/notes/iteration2_levels.md): the new cube chunks and guarantees.

v3 levels are untouched (tests/test_generator_freeze.py rebuilds all 210 of them).
"""

import random

import pytest

from stereo_flyness.experiments import obstacles as O
from stereo_flyness.game import generator as G
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox

NEW = {"platform_drop": "platform_drop", "step_down_pits": "step_down_pits",
       "platform_step_down": "platform", "spaced_pair": "spaced_pair"}


def _level(objs, x=600.0):
    return Level("t", "test", x + 1200, [Box(k, *hitbox(k, x + ox, oy)) for k, ox, oy in objs])


@pytest.mark.parametrize("name", list(NEW))
def test_each_new_chunk_is_one_group_of_its_type(name):
    for difficulty, tier in G.CUBE_TIERS_V4.items():
        if name not in tier.weights:
            continue
        for seed in range(30):
            objs, width = G.CUBE_CHUNKS_V4[name](random.Random(seed), tier)
            gs = O.groups(_level(objs))
            if name == "spaced_pair" and len(gs) == 2:
                # a 4-cell gap looks like two single spikes, as two chunks 4 cells apart would
                assert [g.type for g in gs][0] == "spike1"
                continue
            assert len(gs) == 1 and gs[0].type.startswith(NEW[name]), (difficulty, seed, gs)
            assert max(b.x1 for b in gs[0].boxes) <= 600 + width + 1e-6  # objects stay inside the chunk


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_ranges_follow_the_tier(difficulty):
    tier = G.CUBE_TIERS_V4[difficulty]
    for seed in range(40):
        objs, _ = G.platform_drop(random.Random(seed), tier)
        pits = sum(k == "pit" for k, _, _ in objs)
        heights = {round((y - 15) / 30) + 1 for k, _, y in objs if k == "block"}
        assert tier.pit_widths[0] <= pits <= tier.pit_widths[1]
        assert max(heights) in tier.drop_heights
        objs, _ = G.spaced_pair(random.Random(seed), tier)
        gap = round((objs[1][1] - objs[0][1]) / 30) - 1
        assert tier.pair_gaps[0] <= gap <= tier.pair_gaps[1]
    assert ("step_down_pits" in tier.weights) == (difficulty != "easy")


def test_fix_case_is_decided_by_where_a_walk_off_lands():
    for h in (1, 2):
        cases = [O.groups(_level(G._run(0, 6, h) + [("pit", G._col(6 + k + i), 2) for i in range(3)]))[0].type
                 for k in range(4)]
        # a walk-off's centre lands ~60 (1 block) / ~79 (2 blocks) units out, so k = 0-2 still catch it
        assert cases == ["platform_drop (fix)"] * 3 + ["platform_drop (control)"]


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_every_v4_level_has_a_drop_and_a_spaced_pair(monkeypatch, difficulty):
    for seed in range(8):
        placed = []
        wrapped = {n: (lambda n, f: lambda rng, tier: (placed.append(n), f(rng, tier))[1])(n, f)
                   for n, f in G.CUBE_CHUNKS_V4.items()}
        monkeypatch.setattr(G, "CUBE_CHUNKS_V4", wrapped)
        level = G.build_cube(seed, difficulty, seconds=15, version=4)
        monkeypatch.undo()
        assert {"platform_drop", "step_down_pits"} & set(placed) and "spaced_pair" in placed
        assert level.source.startswith("generator v4")
        types = [g.type for g in O.groups(level)]
        assert any(t.startswith(("platform_drop", "step_down_pits")) for t in types)


def test_v4_is_deterministic_and_differs_from_v3():
    a, b = G.build_cube(5, "medium", version=4), G.build_cube(5, "medium", version=4)
    assert a.to_dict() == b.to_dict()
    assert a.to_dict()["boxes"] != G.build_cube(5, "medium", version=3).to_dict()["boxes"]


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_v4_levels_are_bot_beatable(difficulty):
    g = G.generate("cube", 1, difficulty, seconds=15, version=4)
    assert g.bot.success and g.level.source.startswith("generator v4")


def test_iteration2_config_sizes_seeds_and_version():
    from pathlib import Path

    from stereo_flyness.game import suites

    root = Path(__file__).resolve().parents[1]
    new = suites.load_config(root / "configs" / "iteration2" / "level_suites.toml")
    old = suites.load_config(root / "configs" / "level_suites.toml")
    jobs = suites.jobs(new)
    assert {j.generator_version for j in jobs} == {4} and {j.kind for j in jobs} == {"cube"}
    assert sum(j.suite == "training" for j in jobs) == 50 and sum(j.suite == "held_out" for j in jobs) == 40
    seeds = {(j.difficulty, j.seed) for j in jobs}
    assert not seeds & {(j.difficulty, j.seed) for j in suites.jobs(old)}
    train, held = ({j.seed for j in jobs if j.suite == n} for n in ("training", "held_out"))
    assert not train & held  # training and held-out never share a seed
