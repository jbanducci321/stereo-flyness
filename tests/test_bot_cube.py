"""Search bot on hand-made cube levels: beats what's beatable, pinpoints what isn't."""

from stereo_flyness.game.bot import replay, search
from stereo_flyness.game.level import Box, Level
from stereo_flyness.game.objects import hitbox


def obj(kind, x, y):
    return Box(kind, *hitbox(kind, x, y))


def level(*boxes, length=2500):
    return Level("test", "hand-made", length, list(boxes))


def assert_beaten(lv):
    result = search(lv)
    assert result.success, f"stuck at x={result.farthest_x:.0f}: {result.stuck.most_common(3)}"
    log = replay(lv, result)
    assert log.summary.completed  # the winning inputs really do finish the level
    return result, log


def test_empty_level_needs_no_presses():
    result, log = assert_beaten(level())
    assert not any(result.frame_inputs) and log.summary.jumps == 0


def test_single_spike():
    _, log = assert_beaten(level(obj("spike", 615, 15)))
    assert log.summary.jumps == 1  # prefers not pressing: exactly one jump


def test_triple_spike():
    assert_beaten(level(*[obj("spike", 615 + 30 * k, 15) for k in range(3)]))


def test_spikes_spread_along_the_level():
    assert_beaten(level(*[obj("spike", x, 15) for x in (500, 800, 860, 1200, 1700, 1730, 1760)]))


def test_block_staircase():
    steps = [obj("block", 600 + 120 * k, 15 + 30 * j) for k in range(4) for j in range(k + 1)]
    assert_beaten(level(*steps))


def test_slab_bridge_over_a_pit_field():
    pits = [obj("pit", 615 + 30 * k, 2) for k in range(12)]  # ground hazards from x 600 to 960
    slabs = [obj("slab", 615 + 30 * k, 53) for k in range(12)]  # walkway above them
    assert_beaten(level(*pits, *slabs))


def test_wall_too_high_is_reported():
    wall = [obj("block", 915, 15 + 30 * j) for j in range(5)]  # 150 units tall, jump peaks at 64
    result = search(level(*wall))
    assert not result.success and not result.budget_exhausted
    assert 850 < result.farthest_x < 930
    (kind, _, x), _ = result.stuck.most_common(1)[0]
    assert kind == "block" and 880 <= x <= 900


def test_spike_run_too_long_is_reported():
    run = [obj("spike", 615 + 30 * k, 15) for k in range(10)]  # 300 units of spikes; a jump covers 134
    result = search(level(*run))
    assert not result.success
    kinds = {kind for kind, _, _ in result.stuck}
    assert kinds == {"spike"}
    assert 600 < result.farthest_x < 900
