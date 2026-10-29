"""Subcircuit extraction (J5) on a tiny hand-made connectome.

Wiring (synapses, sign):
    1 --200 (+)--> 2 --200 (+)--> 3 --200 (+)--> 4
    5 --2 (-)--> 3        3 --200 (+)--> 6        7 is unconnected
"""

import json

import numpy as np
import pandas as pd
import pytest
from brian2 import Hz, ms

from stereo_flyness.brain.stepper import BrainStepper
from stereo_flyness.brain.subcircuit import active_neurons, hops, retained_input, write_subcircuit
from stereo_flyness.experiments.pathway_tests import Condition, run_trial

IDS = [1, 2, 3, 4, 5, 6, 7]
EDGES = [(1, 2, 200, 1), (2, 3, 200, 1), (3, 4, 200, 1), (5, 3, 2, -1), (3, 6, 200, 1)]


@pytest.fixture
def con():
    index = {f: i for i, f in enumerate(IDS)}
    return pd.DataFrame({
        "Presynaptic_ID": [e[0] for e in EDGES], "Postsynaptic_ID": [e[1] for e in EDGES],
        "Presynaptic_Index": [index[e[0]] for e in EDGES], "Postsynaptic_Index": [index[e[1]] for e in EDGES],
        "Connectivity": [e[2] for e in EDGES], "Excitatory": [e[3] for e in EDGES],
        "Excitatory x Connectivity": [e[2] * e[3] for e in EDGES],
    })


@pytest.fixture
def files(tmp_path, con):
    pd.DataFrame({"Completed": True}, index=pd.Index(IDS)).to_csv(tmp_path / "comp.csv")
    con.to_parquet(tmp_path / "con.parquet")
    return tmp_path / "comp.csv", tmp_path / "con.parquet"


def test_hops_directions_and_threshold(con):
    assert hops(con, [3], 1, "in") == {2, 3, 5}
    assert hops(con, [3], 1, "in", min_synapses=3) == {2, 3}
    assert hops(con, [3], 2, "in") == {1, 2, 3, 5}
    assert hops(con, [3], 1, "out") == {3, 4, 6}
    assert hops(con, [3], 1, "both") == {2, 3, 4, 5, 6}
    assert hops(con, [3], 0) == {3}
    with pytest.raises(ValueError):
        hops(con, [3], 1, "sideways")


def test_write_subcircuit_reindexes_and_keeps_only_internal_connections(files, tmp_path):
    m = write_subcircuit(*files, [4, 2, 3], tmp_path / "sub", spec={"name": "t"})
    comp = pd.read_csv(tmp_path / "sub" / "comp.csv", index_col=0)
    sub = pd.read_parquet(tmp_path / "sub" / "con.parquet")

    assert list(comp.index) == [2, 3, 4]  # whole-brain order
    assert sorted(zip(sub["Presynaptic_ID"], sub["Postsynaptic_ID"])) == [(2, 3), (3, 4)]
    assert sorted(zip(sub["Presynaptic_Index"], sub["Postsynaptic_Index"])) == [(0, 1), (1, 2)]
    assert (sub["Excitatory x Connectivity"] == [200, 200]).all()  # weights unchanged (D5)
    assert m["neurons"] == 3 and m["connections"] == 2 and m["synapses"] == 400
    assert m["whole_brain"]["neurons"] == 7
    assert json.loads((tmp_path / "sub" / "manifest.json").read_text())["spec"] == {"name": "t"}

    with pytest.raises(KeyError, match="99"):
        write_subcircuit(*files, [2, 99], tmp_path / "bad")


def test_retained_input(con):
    kept = retained_input(con, [2, 3], [3]).iloc[0]
    assert kept["input_synapses"] == 202
    assert kept["kept"] == pytest.approx(200 / 202)
    assert kept["kept_excitatory"] == 1.0 and kept["kept_inhibitory"] == 0.0


def run(comp, conp, seed=3):
    stepper = BrainStepper(comp, conp, inputs={"drive": [1]}, watch={"out": [4], "relay": [2, 3]}, seed=seed)
    stepper.set_rate("drive", 200 * Hz)
    return stepper.step(300 * ms)


def test_closed_subcircuit_reproduces_whole_brain_exactly(files, tmp_path, con):
    """Keeping everything upstream of the watched neuron gives identical spikes (same seed)."""
    upstream = hops(con, [4], 10, "in")
    assert upstream == {1, 2, 3, 4, 5}
    write_subcircuit(*files, upstream, tmp_path / "sub")
    whole, sub = run(*files), run(tmp_path / "sub" / "comp.csv", tmp_path / "sub" / "con.parquet")
    assert whole["out"].sum() > 0
    for g in whole:
        assert (whole[g] == sub[g]).all(), g


def test_active_neurons_from_saved_trials(files, tmp_path):
    cond = Condition("E1", "E1/t", "original", inputs={"drive": [1]}, schedule=[(48, {"drive": 200})],
                     watch={"out": [4]}, trials=1)
    path = run_trial(cond, 0, tmp_path / "res", *files, base_seed=0, frame_ms=1000 / 240)
    assert active_neurons([path]) == {1, 2, 3, 4, 6}  # 5 and 7 get no input
    assert active_neurons([path], min_rate_hz=1e6) == set()
    assert active_neurons([]) == set()


def test_corrected_copy_is_cut_the_same_way(files, tmp_path, con):
    corrected = con.copy()
    corrected.loc[corrected["Presynaptic_ID"] == 5, ["Excitatory", "Excitatory x Connectivity"]] = [1, 2]
    corrected.to_parquet(tmp_path / "con_corr.parquet")
    m = write_subcircuit(*files, [2, 3, 5], tmp_path / "sub", path_con_corrected=tmp_path / "con_corr.parquet")
    orig = pd.read_parquet(tmp_path / "sub" / "con.parquet")
    corr = pd.read_parquet(tmp_path / "sub" / "con_corrected.parquet")
    cols = ["Presynaptic_ID", "Postsynaptic_ID", "Presynaptic_Index", "Postsynaptic_Index", "Connectivity"]
    pd.testing.assert_frame_equal(orig[cols], corr[cols])
    assert corr.loc[corr["Presynaptic_ID"] == 5, "Excitatory"].tolist() == [1]
    assert "con_corr.parquet" in m["source"]
