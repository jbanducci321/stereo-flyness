"""BrainStepper tests on a tiny hand-made connectome in Shiu's file format.

Wiring (FlyWire-style IDs):
    101 (input) --200 excitatory synapses--> 102 (relay) --200 inhibitory synapses--> 103
    104 is unconnected
"""

import numpy as np
import pandas as pd
import pytest
from brian2 import Hz, ms, second

from stereo_flyness.brain.shiu_model import default_params, run_trial
from stereo_flyness.brain.stepper import BrainStepper

INPUT, RELAY, INHIBITED, ISOLATED = 101, 102, 103, 104
WATCH = {"input": [INPUT], "relay": [RELAY], "inhibited": [INHIBITED], "isolated": [ISOLATED]}


@pytest.fixture
def connectome(tmp_path):
    ids = [INPUT, RELAY, INHIBITED, ISOLATED]
    index = {f: i for i, f in enumerate(ids)}
    pd.DataFrame({"Completed": True}, index=pd.Index(ids)).to_csv(tmp_path / "comp.csv")

    edges = [(INPUT, RELAY, 200, 1), (RELAY, INHIBITED, 200, -1)]
    pd.DataFrame({
        "Presynaptic_ID": [e[0] for e in edges],
        "Postsynaptic_ID": [e[1] for e in edges],
        "Presynaptic_Index": [index[e[0]] for e in edges],
        "Postsynaptic_Index": [index[e[1]] for e in edges],
        "Connectivity": [e[2] for e in edges],
        "Excitatory": [e[3] for e in edges],
        "Excitatory x Connectivity": [e[2] * e[3] for e in edges],
    }).to_parquet(tmp_path / "con.parquet")
    return tmp_path / "comp.csv", tmp_path / "con.parquet"


def make_stepper(connectome, seed=1):
    return BrainStepper(*connectome, inputs={"drive": [INPUT]}, watch=WATCH, seed=seed)


def total(counts_list, name):
    return int(sum(c[name].sum() for c in counts_list))


def test_split_steps_match_one_long_run(connectome):
    one = make_stepper(connectome)
    one.set_rate("drive", 100 * Hz)
    long_run = one.step(200 * ms)

    many = make_stepper(connectome)
    many.set_rate("drive", 100 * Hz)
    short_runs = [many.step(20 * ms) for _ in range(10)]

    for name in WATCH:
        assert long_run[name].sum() == total(short_runs, name), name
    assert float(one.t) == pytest.approx(float(many.t))


def test_rate_changes_take_effect_between_steps(connectome):
    stepper = make_stepper(connectome)

    off = stepper.step(50 * ms)
    assert off["input"].sum() == 0 and off["relay"].sum() == 0

    stepper.set_rate("drive", 200 * Hz)
    on = stepper.step(200 * ms)
    assert on["input"].sum() > 10
    assert on["relay"].sum() > 0

    stepper.set_rate("drive", 0 * Hz)
    stepper.step(20 * ms)  # let in-flight synaptic events (1.8 ms delay) finish
    after = stepper.step(50 * ms)
    assert after["input"].sum() == 0 and after["relay"].sum() == 0

    for counts in (off, on, after):
        assert counts["inhibited"].sum() == 0  # only inhibitory input
        assert counts["isolated"].sum() == 0


def test_state_carries_over_between_steps(connectome):
    stepper = make_stepper(connectome)
    stepper.set_rate("drive", 200 * Hz)
    stepper.step(100 * ms)
    stepper.set_rate("drive", 0 * Hz)
    stepper.step(1 * ms)

    # The inhibited neuron never spikes (so is never reset), and its membrane recovers from
    # inhibition over ~20 ms. If each step restarted from rest, it would be exactly at rest.
    i_inhibited = stepper._indices([INHIBITED])[0]
    assert float(stepper.neurons.v[i_inhibited]) < float(default_params["v_0"])
    assert float(stepper.t) == pytest.approx(0.101)


def test_input_matches_shiu_poisson_input(connectome):
    """Our changeable input gives the same input-neuron rate as Shiu's own PoissonInput."""
    params = dict(default_params)
    params["t_run"] = 2 * second
    params["r_poi"] = 100 * Hz
    shiu_spikes = run_trial([0], [], [], *connectome, params)  # index 0 is INPUT
    shiu_count = len(shiu_spikes.get(0, []))

    stepper = make_stepper(connectome, seed=2)
    stepper.set_rate("drive", 100 * Hz)
    ours = stepper.step(2 * second)["input"].sum()

    # Expected about 200 spikes each. Poisson SD is about 14, so allow 4 SD between them.
    assert 140 < shiu_count < 260
    assert 140 < ours < 260
    assert abs(ours - shiu_count) < 4 * np.sqrt(2 * 200)


def test_unknown_ids_raise(connectome):
    with pytest.raises(KeyError, match="999"):
        BrainStepper(*connectome, inputs={"drive": [999]}, watch=WATCH)
