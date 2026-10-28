"""Pathway-test conditions (config expansion) and the trial runner on a tiny connectome."""

import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stereo_flyness.brain.celltypes import CellTypes, top_partners
from stereo_flyness.experiments.pathway_tests import (
    BaselineError, Condition, build_conditions, frame_steps, load_trial, n_frames, run_trial,
)

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "pathway_tests.toml"
TYPES = ["LC4", "LPLC2", "DNp01", "LC10a", "T4a", "T4b", "T4c", "T4d", "T5a", "T5b", "T5c", "T5d",
         "DNp20", "DNp22", "LPi09", *[f"VS{i}" for i in range(1, 9)],
         "CB3707", "SAD014", "CL038", "PVLP010", "LHAD1g1", "CB0010", "CB0563",
         "DNp70", "PVLP122b", "PVLP062", "PVLP151"]


@pytest.fixture
def cells():
    """A fake annotation table: 2 neurons of each type per side (50 for LC4)."""
    rows, nid = [], 1
    for t in TYPES:
        for side in ("left", "right"):
            for _ in range(50 if t == "LC4" else 2):
                rows.append((nid, t, side))
                nid += 1
    ann = pd.DataFrame(rows, columns=["root_id", "cell_type", "side"])
    return CellTypes(ann, ann["root_id"])


@pytest.fixture
def cfg():
    return tomllib.loads(CONFIG.read_text())


def build(cfg, cells):
    return build_conditions(cfg, cells, {"R": [1, 2], "L": [3, 4]}, sugar_ids=[1000, 1001])


def test_cell_lookup_checks_types_sides_and_model_ids(cells):
    assert len(cells.ids("LC4", side="right")) == 50
    assert len(cells.ids("T4d", "T5d", side="left")) == 4
    assert len(cells.ids("DNp01")) == 4  # both sides
    with pytest.raises(KeyError, match="nope"):
        cells.ids("nope")
    ann = pd.DataFrame({"root_id": [1, 2], "cell_type": ["X", "X"], "side": ["left", "left"]})
    with pytest.raises(KeyError, match="not in the model"):
        CellTypes(ann, [1]).ids("X")


def test_top_partners_ranks_by_synapses():
    con = pd.DataFrame({"Presynaptic_ID": [5, 6, 6, 7, 8], "Postsynaptic_ID": [1, 1, 1, 1, 2],
                        "Connectivity": [10, 4, 4, 9, 99]})
    assert top_partners(con, 1, 2) == [5, 7]


def test_condition_counts_and_sign_versions(cfg, cells):
    conds = build(cfg, cells)
    by_exp = pd.Series([c.experiment for c in conds]).value_counts()
    n_rates = len(cfg["rates_hz"])
    assert by_exp["E1"] == 3 * n_rates
    assert by_exp["E3"] == 3 * cfg["escape"]["e3"]["subsets"] + 1
    assert by_exp["E4"] == 3 and by_exp["E5b"] == 1 and by_exp["E5c"] == 1
    assert "E5a" not in by_exp  # dropped (D35)
    assert by_exp["S1"] == 2 * n_rates * 2  # down and up, both sign versions
    assert "S2" not in by_exp and by_exp["S3"] == 2  # round 2 rate not picked yet
    assert {c.sign for c in conds if c.experiment.startswith("E")} == {"original"}
    assert {c.sign for c in conds if c.experiment.startswith("S")} == {"original", "corrected"}

    cfg["steering"]["half_max_rate_hz"] = {"original": 50, "corrected": 100}  # round 2 (D32)
    round2 = build(cfg, cells)
    s2 = [c for c in round2 if c.experiment == "S2"]
    assert len(s2) == 2 * (n_rates + 1)
    s3 = {c.key for c in round2 if c.experiment == "S3"}
    assert {"original/S3/horizontal_R/50Hz", "corrected/S3/horizontal_R/100Hz"} <= s3
    assert len(s3) == 4  # 150 Hz plus the half-max rate, per sign version


def test_schedules_rates_and_seeds(cfg, cells):
    conds = {c.key: c for c in build(cfg, cells)}
    e2 = next(c for c in conds.values() if c.experiment == "E2")
    on = n_frames(300, cfg["frame_ms"])
    assert e2.n_frames == 6 * on
    r = e2.rates()
    assert r.shape == (6 * on, 2)
    assert (r[:on] == 150).all() and (r[on:2 * on] == 0).all()

    orig = conds["original/S1/down_R/150Hz"]
    corr = conds["corrected/S1/down_R/150Hz"]
    assert orig.seed(0, 3) == corr.seed(0, 3)  # paired across sign versions
    assert orig.seed(0, 3) != orig.seed(0, 4) != orig.seed(1, 3)
    assert orig.path("out", 0) != corr.path("out", 0)

    e3 = [c for c in conds.values() if c.experiment == "E3" and "10%" in c.name]
    assert all(len(c.inputs["LC4_R"]) == 5 for c in e3)
    assert len({tuple(c.inputs["LC4_R"]) for c in e3}) == len(e3)  # different subsets

    lesion = conds["original/E5c/LC4_R+LPLC2_R/excitatory_partners_silenced/150Hz"]
    assert lesion.silence == cells.ids("DNp70", "PVLP122b", "PVLP062", "PVLP151")
    assert "GF_partners_R" in lesion.watch and "LC4_R" in lesion.watch


def test_frame_rounding():
    assert frame_steps(1000 / 240) == 42
    assert n_frames(1000, 1000 / 240) == 238


@pytest.fixture
def connectome(tmp_path):
    ids = [101, 102, 103]
    pd.DataFrame({"Completed": True}, index=pd.Index(ids)).to_csv(tmp_path / "comp.csv")
    pd.DataFrame({
        "Presynaptic_ID": [101], "Postsynaptic_ID": [102], "Presynaptic_Index": [0],
        "Postsynaptic_Index": [1], "Connectivity": [200], "Excitatory": [1],
        "Excitatory x Connectivity": [200],
    }).to_parquet(tmp_path / "con.parquet")
    return tmp_path / "comp.csv", tmp_path / "con.parquet"


def test_run_trial_saves_frames_and_resumes(connectome, tmp_path):
    cond = Condition("E2", "E2/test", "original", inputs={"drive": [101]},
                     schedule=[(20, {"drive": 300}), (20, {})],
                     watch={"relay": [102], "drive": [101], "quiet": [103]}, trials=1)
    out = tmp_path / "res"
    path = run_trial(cond, 0, out, *connectome, base_seed=0, frame_ms=1000 / 240, meta={"commit": "x"})
    tr = load_trial(path)

    assert tr["spikes"]["drive"].shape == (40, 1)
    assert tr["spikes"]["drive"][:20].sum() > 5
    assert tr["spikes"]["relay"][:20].sum() > 0
    assert tr["spikes"]["drive"][25:].sum() == 0  # input off
    assert tr["spikes"]["quiet"].sum() == 0
    assert tr["input_names"] == ["drive"] and (tr["rates"][:20] == 300).all()
    assert tr["meta"]["commit"] == "x" and tr["meta"]["frame_ms"] == pytest.approx(4.2)
    assert tr["meta"]["seed"] == cond.seed(0, 0)
    assert list(tr["ids"]["relay"]) == [102]

    # D34: every neuron that fired is recorded per frame, matching the watched groups exactly
    assert list(tr["all_ids"]) == [101, 102]  # 103 never fires
    assert tr["all_spikes"].shape == (40, 2)
    assert (tr["all_spikes"][:, 0] == tr["spikes"]["drive"][:, 0]).all()
    assert (tr["all_spikes"][:, 1] == tr["spikes"]["relay"][:, 0]).all()

    mtime = path.stat().st_mtime_ns
    assert run_trial(cond, 0, out, *connectome, base_seed=0, frame_ms=1000 / 240) == path
    assert path.stat().st_mtime_ns == mtime  # finished trials are skipped


def test_zero_input_baseline_must_be_silent(connectome, tmp_path, monkeypatch):
    """D30: a trial with no input that produces spikes stops the round and saves nothing."""
    from brian2 import mV

    from stereo_flyness.brain.stepper import BrainStepper

    quiet = Condition("S0", "S0/none", "original", inputs={"drive": [101]},
                      schedule=[(10, {})], watch={"relay": [102]}, trials=1)
    path = run_trial(quiet, 0, tmp_path, *connectome, base_seed=0, frame_ms=1000 / 240)
    assert load_trial(path)["all_ids"].size == 0

    # A broken model: one neuron starts above threshold, so it spikes with no input
    build = BrainStepper.__init__

    def broken(self, *args, **kwargs):
        build(self, *args, **kwargs)
        self.neurons.v[0] = self.params["v_th"] + 10 * mV

    monkeypatch.setattr(BrainStepper, "__init__", broken)
    bad = Condition("S0", "S0/broken", "original", inputs={"drive": [101]},
                    schedule=[(10, {})], watch={"relay": [102]}, trials=1)
    with pytest.raises(BaselineError, match="no input"):
        run_trial(bad, 0, tmp_path, *connectome, base_seed=0, frame_ms=1000 / 240)
    assert not bad.path(tmp_path, 0).exists()
