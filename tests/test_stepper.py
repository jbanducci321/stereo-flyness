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


def test_run_frames_matches_step_loop(connectome):
    """The fast single-run path gives frame-by-frame results identical to calling step(),
    including rate changes made from the callback."""
    schedule = [100, 100, 0, 0, 200, 200, 0, 100]  # Hz for each frame

    looped = make_stepper(connectome)
    expected = []
    for rate in schedule:
        looped.set_rate("drive", rate * Hz)
        expected.append(looped.step(20 * ms))

    fast = make_stepper(connectome)
    fast.set_rate("drive", schedule[0] * Hz)
    got = []

    def on_frame(i, counts):
        got.append(counts)
        if i + 1 < len(schedule):
            fast.set_rate("drive", schedule[i + 1] * Hz)

    fast.run_frames(len(schedule), 20 * ms, on_frame)

    assert len(got) == len(schedule)
    for i, (e, g) in enumerate(zip(expected, got)):
        for name in WATCH:
            assert e[name].sum() == g[name].sum(), (i, name)
    assert float(fast.t) == pytest.approx(float(looped.t))


TICK = 1000 / 240 * ms  # one game physics tick (D40)


def frame_steps_seen(stepper, n, frame, rates=None, split=None):
    """Run `n` exact frames; return the time steps each frame lasted and its counts."""
    ends, counts = [], []
    rates = rates or [100] * n
    stepper.set_rate("drive", rates[0] * Hz)

    def on_frame(i, c):
        ends.append(int(round(float(stepper.neurons.t / (0.1 * ms)))))  # neuron steps run so far
        counts.append(c)
        if i + 1 < len(rates):
            stepper.set_rate("drive", rates[(len(counts)) % len(rates)] * Hz)

    for part in split or [n]:
        stepper.run_frames(part, frame, on_frame, exact=True)
    steps = np.diff([0, *ends]).tolist()
    return steps, counts


def test_exact_frames_alternate_42_42_41_without_drift(connectome):
    """D40: 240 frames of one game tick take exactly 1 s of brain time."""
    st = make_stepper(connectome)
    steps, counts = frame_steps_seen(st, 240, TICK)
    assert len(counts) == 240
    assert set(steps) == {41, 42} and steps[:6] == [42, 42, 41, 42, 42, 41]
    assert all(sum(steps[i:i + 3]) == 125 for i in range(0, 240, 3))  # 12.5 ms per 3 ticks
    assert float(st.t / second) == pytest.approx(1.0)


def test_exact_frames_match_a_step_loop(connectome):
    """Exact frames give the same spikes as step() calls of 42/42/41 steps, rate changes included."""
    rates = [100, 100, 0, 200, 200, 0, 100, 150, 0, 100]
    fast = make_stepper(connectome)
    steps, got = frame_steps_seen(fast, len(rates), TICK, rates=rates)

    looped = make_stepper(connectome)
    for i, (n, r) in enumerate(zip(steps, rates)):
        looped.set_rate("drive", r * Hz)
        e = looped.step(n * 0.1 * ms)
        for name in WATCH:
            assert e[name].sum() == got[i][name].sum(), (i, name)


def test_exact_frames_can_be_split_across_calls(connectome):
    """Several run_frames calls continue the same frame grid as one long call."""
    one_steps, one = frame_steps_seen(make_stepper(connectome), 12, TICK)
    split_steps, split = frame_steps_seen(make_stepper(connectome), 12, TICK, split=[5, 7])
    assert split_steps == one_steps
    assert [total([c], "relay") for c in split] == [total([c], "relay") for c in one]


def test_exact_frames_must_start_on_a_frame_boundary(connectome):
    st = make_stepper(connectome)
    st.step(1 * ms)  # 10 steps: not a multiple of 41.667
    with pytest.raises(ValueError, match="frame boundary"):
        st.run_frames(3, TICK, lambda i, c: None, exact=True)


def test_exact_and_rounded_agree_for_whole_step_frames(connectome):
    ga, gb = [], []
    a = make_stepper(connectome)  # build and run one at a time: they share Brian2's RNG
    a.set_rate("drive", 150 * Hz)
    a.run_frames(6, 20 * ms, lambda i, c: ga.append(c), exact=True)
    b = make_stepper(connectome)
    b.set_rate("drive", 150 * Hz)
    b.run_frames(6, 20 * ms, lambda i, c: gb.append(c))
    assert [total([c], "relay") for c in ga] == [total([c], "relay") for c in gb]
    assert float(a.t) == pytest.approx(float(b.t))


def test_unknown_ids_raise(connectome):
    with pytest.raises(KeyError, match="999"):
        BrainStepper(*connectome, inputs={"drive": [999]}, watch=WATCH)


def test_silencing_relay_cuts_downstream_only(connectome):
    """Silencing zeroes a neuron's outgoing synapses (Shiu's silence()): the relay still fires,
    but the neuron it inhibits no longer feels it."""
    silenced = BrainStepper(*connectome, inputs={"drive": [INPUT]}, watch=WATCH, seed=1,
                            silence=[RELAY])
    silenced.set_rate("drive", 200 * Hz)
    counts = silenced.step(100 * ms)
    assert counts["input"].sum() > 0 and counts["relay"].sum() > 0

    i_inhibited = silenced._indices([INHIBITED])[0]
    assert float(silenced.neurons.v[i_inhibited]) == pytest.approx(float(default_params["v_0"]))

    intact = make_stepper(connectome)
    intact.set_rate("drive", 200 * Hz)
    intact.step(100 * ms)
    assert float(intact.neurons.v[i_inhibited]) < float(default_params["v_0"])


def test_silencing_input_stops_relay(connectome):
    stepper = BrainStepper(*connectome, inputs={"drive": [INPUT]}, watch=WATCH, seed=1,
                           silence=[INPUT])
    stepper.set_rate("drive", 200 * Hz)
    counts = stepper.step(200 * ms)
    assert counts["input"].sum() > 10  # external drive still reaches a silenced neuron
    assert counts["relay"].sum() == 0


def test_unknown_silence_ids_raise(connectome):
    with pytest.raises(KeyError, match="999"):
        BrainStepper(*connectome, inputs={"drive": [INPUT]}, watch=WATCH, silence=[999])
