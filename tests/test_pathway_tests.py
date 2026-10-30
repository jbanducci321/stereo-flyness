"""Pathway-test conditions (config expansion) and the trial runner on a tiny connectome."""

import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stereo_flyness.brain.celltypes import CellTypes, grow_order, input_similarity, top_partners
from stereo_flyness.experiments.pathway_tests import (
    BaselineError, Condition, build_conditions, frame_steps, load_trial, n_frames, patch_steps, run_trial,
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
    """The real config, reset to its round 1 state (round 2 rates not picked yet, no
    recruitment sides or probes)."""
    cfg = tomllib.loads(CONFIG.read_text())
    cfg["escape"]["e2"]["rates_hz"] = [150]
    cfg["steering"]["half_max_rate_hz"] = {}
    cfg.pop("recruitment", None)
    cfg.pop("probes", None)
    return cfg


def build(cfg, cells):
    patches = {sd: {t: cells.ids(t, side=sd) for t in ("LC4", "LPLC2")} for sd in ("right", "left")}
    return build_conditions(cfg, cells, {"R": [1, 2], "L": [3, 4]}, sugar_ids=[1000, 1001], patches=patches)


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


def test_patches_grow_through_shared_inputs():
    # 1 and 2 share input 10; 3 and 4 share input 20; 2 and 3 share a little of input 30
    con = pd.DataFrame({"Presynaptic_ID": [10, 10, 20, 20, 30, 30],
                        "Postsynaptic_ID": [1, 2, 3, 4, 2, 3], "Connectivity": [9, 9, 9, 9, 1, 1]})
    sim = input_similarity(con, [1, 2, 3, 4, 5])  # 5 has no inputs
    assert sim[0, 1] > sim[1, 2] > 0 and sim[0, 3] == 0 and not sim[4].any()
    assert grow_order(sim, 0) == [0, 1, 2, 3, 4]
    assert grow_order(sim, 3) == [3, 2, 1, 0, 4]


def test_patch_steps():
    assert patch_steps(50, 19, 152, 8)[0] == 6 and patch_steps(102, 19, 152, 8)[0] == 13  # 19 in all
    for n in (1, 2, 50, 102):
        c = patch_steps(n, 19, 152, 8)
        assert len(c) == 8 and c[-1] == n and c[0] >= 1
        assert all(b >= a for a, b in zip(c, c[1:]))
    c = patch_steps(102, 19, 152, 8)
    assert all(b > a for a, b in zip(c, c[1:]))  # every step adds neurons


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


def test_recruitment_and_probe_conditions(cells):
    cfg = tomllib.loads(CONFIG.read_text())
    conds = build(cfg, cells)
    by = {c.key: c for c in conds}
    from stereo_flyness.experiments.pathway_tests import judged

    # Recruitment: game-input experiments repeated on the left and on both sides, fewer trials
    left = [c for c in conds if c.side == "left" and not c.experiment.startswith("P")]
    assert {c.experiment for c in left} == set(cfg["recruitment"]["experiments"])
    assert all(c.trials <= cfg["recruitment"]["trials"] for c in left)
    assert by["original/E1/LC4_L+LPLC2_L/150Hz"].inputs["LC4_L"] == cells.ids("LC4", side="left")
    both = by["original/E1/LC4_B+LPLC2_B/150Hz"].inputs["LC4_B"]
    assert both == sorted(cells.ids("LC4", side="left") + cells.ids("LC4", side="right"))
    assert not any(c.experiment in ("E4", "S0") and c.side != "right" for c in conds)  # main side only
    assert all(not judged(c, cfg) for c in left)
    assert judged(by["original/E1/LC4_R+LPLC2_R/150Hz"], cfg)

    # P1: chunks partition the side's looming neurons and switch on one after another
    p1 = by["original/P1/loom_R/expanding/150Hz"]
    chunks = list(p1.inputs.values())
    assert sorted(i for c in chunks for i in c) == cells.ids("LC4", "LPLC2", side="right")
    r = p1.rates()
    step = n_frames(75, cfg["frame_ms"])
    assert (r[:step] > 0).sum(axis=1).max() == 1 and (r[3 * step:4 * step] > 0).all()
    assert not judged(p1, cfg)

    # P2: a rising ramp, then off; P3/P4 on both sign versions
    ramp = by["original/P2/loom_R/ramp/200Hz"].rates()[:, 0]
    n_ramp = n_frames(300, cfg["frame_ms"])
    assert (np.diff(ramp[:n_ramp]) > 0).all() and ramp[n_ramp - 1] == pytest.approx(200)
    assert ramp[n_ramp] == 0
    for sign in ("original", "corrected"):
        assert f"{sign}/P3/down_B+up_B/switching/100Hz" in by
        assert f"{sign}/P4/horizontal_B_50Hz+down_B/onoff/100Hz" in by

    # P5: a patch growing step by step to all of a side's looming neurons (each side, for both)
    p5 = by["original/P5/patch_R/growing/150Hz"]
    steps = list(p5.inputs.values())
    assert len(steps) == cfg["probes"]["p5"]["steps"] and all(steps)
    assert sorted(i for c in steps for i in c) == cells.ids("LC4", "LPLC2", side="right")
    assert len(steps[0]) == 19 and steps[0][:18] == cells.ids("LC4", side="right")[:18]  # patch order
    r = p5.rates()
    step = n_frames(cfg["probes"]["p5"]["step_ms"], cfg["frame_ms"])
    assert (r[:step] > 0).sum(axis=1).max() == 1 and (r[7 * step:8 * step] > 0).all()
    both = by["original/P5/patch_B/growing/150Hz"].inputs
    assert sorted(i for c in both.values() for i in c) == sorted(cells.ids("LC4", "LPLC2"))
    assert len(next(iter(both.values()))) == 38  # each side's first step
    with pytest.raises(ValueError, match="P5 needs"):
        build_conditions(cfg, cells, {"R": [1, 2], "L": [3, 4]}, sugar_ids=[1000])

    # P6: P1's looming plus constant front-to-back motion, both sign versions, escape + steering watched
    for sign in ("original", "corrected"):
        p6 = by[f"{sign}/P6/loom_R+front_to_back_R_50Hz/expanding/150Hz"]
        assert p6.inputs["front_to_back_R"] == cells.ids("T4a", "T5a", side="right")
        assert {k: v for k, v in p6.inputs.items() if k.startswith("loom")} == p1.inputs
        assert {"GF_R", "GF_L", "VS_R", "LPi09_L"} <= set(p6.watch)
        r = p6.rates()
        assert (r[:, list(p6.inputs).index("front_to_back_R")] == 50).all()
        assert (r[:, :4] == p1.rates()).all()

    # P7: all of a side's looming neurons in short bursts
    r = by["original/P7/loom_L/bursts/150Hz"].rates()[:, 0]
    on, off = n_frames(100, cfg["frame_ms"]), n_frames(50, cfg["frame_ms"])
    assert len(r) == 4 * (on + off) and (r[:on] == 150).all() and (r[on:on + off] == 0).all()
    assert len([c for c in conds if c.experiment in ("P5", "P6", "P7")]) == 3 + 6 + 3
