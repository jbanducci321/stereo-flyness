"""The go/no-go rule logic (D29-D32) on made-up trial summaries with known answers."""

import math

import numpy as np
import pandas as pd
import pytest

from stereo_flyness.experiments.pathway_analysis import (
    escape_rules, first_spike_ms, horizontal_rule, latency_rule, onoff_cycles, pick_e2_rate,
    pick_half_max, pooled_sd, reliable, steering_rules, trial_row,
)


def e1_trials(right, left, fires=10, first_ms=20.0, n=10, spread=2.0):
    """Ten trials per rate: right/left Giant Fiber means per rate, `fires` of them spiking."""
    rows = []
    for rate in right:
        for t in range(n):
            jitter = spread * (t - (n - 1) / 2) / n
            f = t < fires[rate] if isinstance(fires, dict) else t < fires
            rows.append({"rate": rate, "trial": t, "rate:GF_R": right[rate] + jitter if f else 0.0,
                         "rate:GF_L": left[rate] + jitter, "fires:GF_R": f,
                         "gf_first_ms": (first_ms[rate] if isinstance(first_ms, dict) else first_ms) if f else math.nan})
    return pd.DataFrame(rows)


def test_reliable_and_pooled_sd():
    assert reliable([True] * 9 + [False]) and not reliable([True] * 8 + [False] * 2)
    assert not reliable([])
    assert pooled_sd([1, 3], [1, 3]) == pytest.approx(math.sqrt(2))


def test_escape_rules_pass():
    right = {25: 20, 50: 60, 100: 120, 150: 150, 200: 180}
    left = {r: v / 3 for r, v in right.items()}
    res = escape_rules(e1_trials(right, left))
    assert res["rule0"] and res["rule1"] and res["rule2"]
    assert res["reliable_rates"] == [25, 50, 100, 150, 200]


def test_rule0_guards_rule2_when_never_reliable():
    right = {25: 5, 200: 5}
    res = escape_rules(e1_trials(right, {25: 0, 200: 0}, fires=3))
    assert not res["rule0"] and not res["rule2"]  # rule 2 can't pass by default


def test_rule2_fails_when_left_close_to_right():
    right = {25: 100, 200: 200}
    res = escape_rules(e1_trials(right, {25: 99, 200: 199}, spread=20))
    assert res["rule1"] and not res["rule2"]


def test_pick_e2_rate():
    df = e1_trials({25: 10, 50: 50, 100: 100}, {25: 0, 50: 0, 100: 0},
                   fires={25: 10, 50: 10, 100: 10}, first_ms={25: 150.0, 50: 80.0, 100: 30.0})
    assert pick_e2_rate(df) == (50, True)
    late = e1_trials({25: 10, 200: 10}, {25: 0, 200: 0}, first_ms=120.0)
    assert pick_e2_rate(late) == (200, False)


def test_latency_rule():
    ok = pd.DataFrame({"onset_ms": [20.0, 25, 30, 22]})
    assert latency_rule(ok)["pass"]
    jittery = pd.DataFrame({"onset_ms": [5.0, 140, 5, 140]})  # mean 72.5 but SD ~78: 4 x SD > 238
    assert not latency_rule(jittery)["pass"]
    missed = pd.DataFrame({"onset_ms": [20.0, math.nan]})
    assert not latency_rule(missed)["pass"]


def steering_trials(down_vs, up_vs, down_dn, up_dn, rates=(25, 150)):
    rows = []
    for g, vs, dn in (("down_R", down_vs, down_dn), ("up_R", up_vs, up_dn)):
        for r in rates:
            for t in range(10):
                rows.append({"group": g, "rate": r, "rate:VS_R": vs * r / 150, "rate:DNp20_R": dn * r / 150,
                             "fires:VS_R": vs > 0, "fires:DNp20_R": dn > 0})
    return pd.DataFrame(rows)


def test_steering_rules():
    good = steering_rules(steering_trials(200, 0, 140, 0), "down_R", "up_R")
    assert good["rule1"] and good["rule2"]
    leaky = steering_rules(steering_trials(200, 50, 140, 0), "down_R", "up_R")
    assert leaky["rule1"] and not leaky["rule2"]  # up gives VS 25% of down
    dead = steering_rules(steering_trials(200, 0, 0, 0), "down_R", "up_R")
    assert not dead["rule1"] and not dead["rule2"]


def test_pick_half_max():
    down = pd.DataFrame({"rate": [25, 50, 100, 150, 200], "rate:VS_R": [20, 110, 150, 200, 210]})
    assert pick_half_max(down)[0] == 50
    flat = pd.DataFrame({"rate": [25, 50], "rate:VS_R": [180, 200]})
    assert pick_half_max(flat)[0] == 25  # D32 edge case: 25 Hz already qualifies


def test_horizontal_rule():
    down = pd.DataFrame({"rate:VS_R": [200, 202, 198, 201]})
    assert horizontal_rule(down, pd.DataFrame({"rate:VS_R": [100, 102, 98, 101]}))["pass"]
    assert not horizontal_rule(down, pd.DataFrame({"rate:VS_R": [199, 203, 197, 200]}))["pass"]


def fake_trial(gf_counts, schedule):
    gf = np.asarray(gf_counts, dtype=np.uint16).reshape(-1, 1)
    return {"meta": {"key": "x", "trial": 0, "n_frames": len(gf), "frame_ms": 4.2,
                     "condition": {"schedule": schedule}},
            "spikes": {"GF_R": gf, "VS_R": np.zeros((len(gf), 2), dtype=np.uint16)}}


def test_trial_row_and_first_spike():
    tr = fake_trial([0, 0, 1, 2, 0], [[5, {}]])
    row = trial_row(tr)
    assert row["fires:GF_R"] and not row["fires:VS_R"]
    assert row["gf_first_ms"] == pytest.approx(3 * 4.2)
    assert row["rate:GF_R"] == pytest.approx(3 / (5 * 4.2 / 1000))
    assert math.isnan(first_spike_ms(np.zeros(3), 4.2))


def test_onoff_cycles():
    # two cycles of 3 frames on, 3 off; cycle 0 keeps firing 2 frames into "off", cycle 1 stops at once
    counts = [0, 1, 1, 1, 1, 0] + [1, 0, 0, 0, 0, 0]
    tr = fake_trial(counts, [[3, {"a": 1}], [3, {}], [3, {"a": 1}], [3, {}]])
    cyc = onoff_cycles(tr)
    assert cyc["onset_ms"].tolist() == pytest.approx([2 * 4.2, 4.2])
    assert cyc["offset_ms"].tolist() == pytest.approx([2 * 4.2, 0.0])
    assert cyc["spikes_on"].tolist() == [2, 1]
