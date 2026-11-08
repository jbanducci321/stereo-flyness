"""The degree-preserving shuffle (Step 4 control, draft) on small random connectivity tables."""

import numpy as np
import pandas as pd
import pytest

from stereo_flyness.brain.controls import check_shuffle, degree_preserving_shuffle


def table(n_neurons=60, n_edges=900, seed=1):
    """A random table shaped like Connectivity_783: no self-connections or duplicates, one sign per neuron."""
    rng = np.random.default_rng(seed)
    pairs = set()
    while len(pairs) < n_edges:
        a, b = rng.integers(n_neurons, size=2)
        if a != b:
            pairs.add((int(a), int(b)))
    pre, post = np.array(sorted(pairs)).T
    sign = rng.choice([-1, 1], size=n_neurons)
    syn = rng.integers(1, 30, size=n_edges)
    ids = 720575940000000000 + np.arange(n_neurons) * 7  # FlyWire-like IDs, not the index
    return pd.DataFrame({
        "Presynaptic_ID": ids[pre], "Postsynaptic_ID": ids[post],
        "Presynaptic_Index": pre, "Postsynaptic_Index": post,
        "Connectivity": syn, "Excitatory": sign[pre], "Excitatory x Connectivity": syn * sign[pre],
    })


def test_shuffle_keeps_degrees_weights_and_signs():
    con = table()
    out, report = degree_preserving_shuffle(con, seed=0)
    assert check_shuffle(con, out) == []
    # Who connects to whom has changed for most connections.
    assert report.unchanged < 0.2 * len(con)
    assert report.shuffled == len(con) and report.kept == 0


def test_dense_table_needs_and_completes_swap_rounds():
    con = table(n_neurons=20, n_edges=250)  # ~66% dense, so the permutation makes many repeats
    out, report = degree_preserving_shuffle(con, seed=3)
    assert report.rounds > 0
    assert check_shuffle(con, out) == []


def test_same_seed_same_table_different_seed_different_table():
    con = table()
    a, _ = degree_preserving_shuffle(con, seed=5)
    b, _ = degree_preserving_shuffle(con, seed=5)
    c, _ = degree_preserving_shuffle(con, seed=6)
    assert a.equals(b)
    assert not a.equals(c)


def test_kept_connections_stay_in_place():
    con = table()
    keep = np.zeros(len(con), dtype=bool)
    keep[::10] = True
    out, report = degree_preserving_shuffle(con, seed=0, keep=keep)
    assert check_shuffle(con, out, keep=keep) == []
    assert report.kept == keep.sum()
    assert (out.loc[keep, "Postsynaptic_ID"].to_numpy() == con.loc[keep, "Postsynaptic_ID"].to_numpy()).all()


def test_original_table_is_not_modified():
    con = table()
    before = con.copy()
    degree_preserving_shuffle(con, seed=0)
    assert con.equals(before)


def test_check_catches_broken_shuffles():
    con = table()
    out, _ = degree_preserving_shuffle(con, seed=0)
    selfie = out.copy()
    selfie.loc[0, "Postsynaptic_Index"] = selfie.loc[0, "Presynaptic_Index"]
    assert "self-connections" in check_shuffle(con, selfie)
    dup = out.copy()
    dup.loc[1, ["Presynaptic_Index", "Postsynaptic_Index"]] = dup.loc[0, ["Presynaptic_Index", "Postsynaptic_Index"]]
    assert any("duplicate" in f for f in check_shuffle(con, dup))
    weight = out.copy()
    weight.loc[0, "Connectivity"] += 1
    assert "Connectivity changed" in check_shuffle(con, weight)


def test_keep_must_match_the_table():
    with pytest.raises(ValueError):
        degree_preserving_shuffle(table(), seed=0, keep=[True, False])


def test_control_path_and_checksum(tmp_path):
    from stereo_flyness.brain.controls import control_path, file_sha256

    con = table()
    out, _ = degree_preserving_shuffle(con, seed=0)
    path = control_path(tmp_path, "shuffle_s0")
    assert path.name == "Connectivity_783_shuffle_s0.parquet"
    con.to_parquet(tmp_path / "original.parquet", index=False)
    out.to_parquet(path, index=False)
    assert file_sha256(path) == file_sha256(path)
    assert file_sha256(path) != file_sha256(tmp_path / "original.parquet")


def test_brain_runs_on_a_shuffled_connectome(tmp_path):
    """The stepper reads a shuffled file like the original: same neurons, different wiring."""
    from brian2 import Hz, ms

    from stereo_flyness.brain.stepper import BrainStepper

    con = table(n_neurons=30, n_edges=200)
    ids = 720575940000000000 + np.arange(30) * 7
    pd.DataFrame({"Completed": True}, index=pd.Index(ids)).to_csv(tmp_path / "comp.csv")
    out, _ = degree_preserving_shuffle(con, seed=0)
    con.to_parquet(tmp_path / "con.parquet", index=False)
    out.to_parquet(tmp_path / "shuffled.parquet", index=False)
    counts = {}
    for name in ("con", "shuffled"):
        st = BrainStepper(tmp_path / "comp.csv", tmp_path / f"{name}.parquet",
                          inputs={"drive": [int(ids[0])]}, watch={"all": [int(i) for i in ids]}, seed=1)
        st.set_rate("drive", 200 * Hz)
        counts[name] = st.step(200 * ms)["all"]
    assert counts["con"].shape == counts["shuffled"].shape == (30,)
    assert counts["con"][0] > 0 and counts["shuffled"][0] > 0  # the driven neuron fires in both


# --- D51 additions -------------------------------------------------------------------------


def loom_gf_setup(con):
    """Neurons 0-4 stand in for LC4/LPLC2 and 50-51 for the Giant Fibers."""
    loom_idx, gf_idx = np.arange(5), np.array([50, 51])
    ids = 720575940000000000 + np.arange(60) * 7
    keep = (con["Presynaptic_Index"].isin(loom_idx) & con["Postsynaptic_Index"].isin(gf_idx)).to_numpy()
    return loom_idx, gf_idx, ids, keep


def test_looming_kept_shuffle_adds_no_new_looming_to_gf():
    from stereo_flyness.brain.controls import pathway_mask

    con = table()
    loom_idx, gf_idx, ids, keep = loom_gf_setup(con)
    assert keep.sum() > 0
    forbid = (loom_idx, gf_idx)
    for seed in range(5):
        out, report = degree_preserving_shuffle(con, seed=seed, keep=keep, forbid=forbid)
        assert check_shuffle(con, out, keep=keep, forbid=forbid) == []
        # Exactly the original looming -> Giant Fiber connections, no more, no less.
        now = pathway_mask(out, ids[loom_idx], ids[gf_idx])
        assert (now == keep).all()


def test_check_catches_a_forbidden_connection():
    con = table()
    loom_idx, gf_idx, ids, keep = loom_gf_setup(con)
    out, _ = degree_preserving_shuffle(con, seed=0)  # no forbid: some new looming -> GF may appear
    bad = out.copy()
    row = int(np.flatnonzero(~keep)[0])
    bad.loc[row, ["Presynaptic_Index", "Postsynaptic_Index"]] = [0, 50]
    assert any("forbidden" in f for f in check_shuffle(con, bad, keep=keep, forbid=(loom_idx, gf_idx)))


def test_relay_only_keeps_exactly_the_pathway():
    from stereo_flyness.brain.controls import relay_only

    con = table()
    loom_idx, gf_idx, ids, keep = loom_gf_setup(con)
    relay = relay_only(con, ids[loom_idx], ids[gf_idx])
    assert len(relay) == keep.sum()
    assert relay.equals(con[keep].reset_index(drop=True))
    assert list(relay.columns) == list(con.columns)


def test_random_network_size_signs_and_counts():
    from stereo_flyness.brain.controls import random_network

    con = table()
    ids = 720575940000000000 + np.arange(60) * 7
    net = random_network(con, ids, seed=0)
    assert len(net) == len(con) and list(net.columns) == list(con.columns)
    assert (net.dtypes == con.dtypes).all()
    assert not (net["Presynaptic_Index"] == net["Postsynaptic_Index"]).any()
    assert not net.duplicated(["Presynaptic_Index", "Postsynaptic_Index"]).any()
    # Synapse counts are the real ones, rearranged.
    assert sorted(net["Connectivity"]) == sorted(con["Connectivity"])
    # Each neuron keeps its sign wherever it had one.
    real = con.groupby("Presynaptic_Index")["Excitatory"].first()
    new = net.groupby("Presynaptic_Index")["Excitatory"].nunique()
    assert (new == 1).all()
    both = net.groupby("Presynaptic_Index")["Excitatory"].first().reindex(real.index).dropna()
    assert (both == real.reindex(both.index)).all()
    assert (net["Excitatory x Connectivity"] == net["Connectivity"] * net["Excitatory"]).all()
    # IDs and indices agree.
    assert (net["Presynaptic_ID"].to_numpy() == ids[net["Presynaptic_Index"].to_numpy()]).all()
    # Seeded.
    assert net.equals(random_network(con, ids, seed=0))
    assert not net.equals(random_network(con, ids, seed=1))


def test_matched_random_lesion_rules():
    from stereo_flyness.brain.controls import matched_random_lesion

    con = table(n_neurons=60, n_edges=1500)
    out_syn = con.groupby("Presynaptic_ID")["Connectivity"].sum()
    sign = con.groupby("Presynaptic_ID")["Excitatory"].first()
    ids = out_syn.index.to_numpy()
    lesion, exclude = list(ids[:3]), list(ids[3:6])
    for seed in range(3):
        picked = matched_random_lesion(con, lesion, exclude, seed=seed, tol=0.5)
        assert len(picked) == len(lesion) == len(set(picked))
        assert not set(picked) & (set(lesion) | set(exclude))
        for lid, pid in zip(sorted(lesion), picked):
            assert sign[pid] == sign[lid]
            assert 0.5 * out_syn[lid] <= out_syn[pid] <= 1.5 * out_syn[lid]
    assert matched_random_lesion(con, lesion, exclude, seed=0, tol=0.5) == \
        matched_random_lesion(con, lesion, exclude, seed=0, tol=0.5)


def test_matched_random_lesion_refuses_when_nothing_matches():
    from stereo_flyness.brain.controls import matched_random_lesion

    con = table()
    lid = int(con["Presynaptic_ID"].iloc[0])
    with pytest.raises(ValueError):
        matched_random_lesion(con, [lid], [], seed=0, tol=0.0)


def test_recruited_matched_lesion_keeps_involvement_status():
    from stereo_flyness.brain.controls import matched_random_lesion

    con = table(n_neurons=60, n_edges=1500)
    ids = con.groupby("Presynaptic_ID")["Connectivity"].sum().index.to_numpy()
    lesion, exclude = list(ids[:4]), list(ids[4:6])
    involved = set(ids[::2])  # every other neuron "fired in the recruitment runs"
    for seed in range(3):
        picked = matched_random_lesion(con, lesion, exclude, seed=seed, tol=0.6, involved=involved)
        for lid, pid in zip(sorted(int(i) for i in lesion), picked):
            assert (pid in involved) == (lid in involved)
    # Same count of involved neurons silenced as in the lesion.
    assert sum(p in involved for p in picked) == sum(int(i) in involved for i in lesion)
