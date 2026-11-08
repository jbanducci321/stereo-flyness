"""Step 4's judging rules (D51) on hand-made runs."""

import pytest

from stereo_flyness.experiments.step4_analysis import (
    Paired, d1_share, holm, median_runs, paired, pooled_median, relay_reading, seed_range, specific)


def run(level, seed, progress, completed=False, killer=None):
    return {"level": level, "seed": seed, "progress": progress, "completed": completed,
            "killer": killer if killer is not None else (level, round(progress, 3))}


def test_median_run_is_an_actual_run():
    runs = [run("a", 0, 0.5), run("a", 1, 0.2), run("a", 2, 0.9)]
    assert median_runs(runs)["a"]["seed"] == 0
    tie = [run("b", 2, 0.3), run("b", 0, 0.3), run("b", 1, 0.8)]
    assert median_runs(tie)["b"]["seed"] == 2  # sorted (0.3, 0), (0.3, 2), (0.8, 1): the middle one


def test_paired_counts_and_sign_test():
    ref = [run(f"l{i}", s, 0.2, killer=("x", i)) for i in range(12) for s in range(3)]
    better = [run(f"l{i}", s, 0.9, killer=("y", i)) for i in range(12) for s in range(3)]
    res = paired(better, ref)
    assert (res.better, res.worse, res.equal) == (12, 0, 0)
    assert res.p < 0.001 and res.reading == "better"
    same = paired(ref, ref)
    assert (same.equal, same.p, same.reading) == (12, 1.0, "no clear difference")


def test_paired_refuses_different_levels():
    with pytest.raises(ValueError):
        paired([run("a", 0, 0.1)], [run("b", 0, 0.1)])


def test_holm_step_down():
    p = {"a": 0.001, "b": 0.02, "c": 0.04, "d": 0.5}
    out = holm(p)
    assert out["a"] == (pytest.approx(0.004), True)
    assert out["b"] == (pytest.approx(0.06), False)  # 3 x 0.02 >= 0.05: stops here
    assert out["c"][1] is False and out["c"][0] == pytest.approx(0.08)
    assert out["d"][0] == pytest.approx(0.5) and out["d"][1] is False


def test_holm_adjusted_values_never_decrease():
    out = holm({"a": 0.01, "b": 0.011, "c": 0.9})
    assert out["a"][0] <= out["b"][0] <= out["c"][0]


def test_seed_range_and_d1_share():
    assert seed_range([36.0, 38.5, 37.0]) == pytest.approx(2.5)
    assert seed_range([1.0]) == 0.0
    assert d1_share(["d1", "b", None, "d1"]) == pytest.approx(2 / 3)
    assert d1_share([None, None]) == 0.0  # no deaths -> 0 (D51)
    assert pooled_median([]) is None


def test_relay_reading_all_bars():
    same = Paired(2, 2, 16, 1.0)
    intact_theta = [[36, 37, 38], [37, 38, 39], [35, 36, 37]]  # seed medians 37, 38, 36: range 2
    intact_classes = [["d1", "b"], ["d1", "d1"], ["b", "b"]]  # shares 0.5, 1, 0: range 1
    r = relay_reading(same, [37, 37, 38], intact_theta, ["d1", "b"], intact_classes)
    assert r.theta_ok and r.d1_ok and r.verdict == "relay: all three bars pass"


def test_relay_reading_fails_on_theta_or_silence():
    same = Paired(2, 2, 16, 1.0)
    intact_theta = [[37, 37], [38, 38], [36, 36]]
    intact_classes = [["d1"], ["d1"], ["d1"]]  # range 0: any change in the (d1) share fails
    early = relay_reading(same, [30, 30, 31], intact_theta, ["d1"], intact_classes)
    assert not early.theta_ok and early.verdict == "plays about as far, but not the same way"
    silent = relay_reading(same, [], intact_theta, ["d1"], intact_classes)
    assert silent.theta_diff is None and not silent.theta_ok  # never fired: fails (D51)
    worse = relay_reading(Paired(0, 12, 8, 0.0005), [37], intact_theta, ["d1"], intact_classes)
    assert worse.verdict == "plays differently from intact"


def test_specific_needs_both_in_the_same_direction():
    worse, better, none = Paired(0, 12, 8, 0.0005), Paired(12, 0, 8, 0.0005), Paired(3, 4, 13, 1.0)
    assert specific(worse, worse)
    assert not specific(worse, none)
    assert not specific(worse, better)
    assert not specific(none, none)
