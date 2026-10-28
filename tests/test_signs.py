"""The T4/T5 sign correction (D27) on a tiny hand-made connectivity table."""

import pandas as pd

from stereo_flyness.brain.signs import T4T5_TYPES, correct_signs

T4, T5, OTHER, POST = 1, 2, 3, 9


def table():
    edges = [  # pre, post, synapses, sign
        (T4, POST, 10, -1),
        (T4, OTHER, 4, 1),
        (T5, POST, 7, -1),
        (OTHER, T4, 5, -1),  # inhibitory *onto* T4: must stay inhibitory
        (OTHER, POST, 3, -1),
    ]
    return pd.DataFrame({
        "Presynaptic_ID": [e[0] for e in edges],
        "Postsynaptic_ID": [e[1] for e in edges],
        "Connectivity": [e[2] for e in edges],
        "Excitatory": [e[3] for e in edges],
        "Excitatory x Connectivity": [e[2] * e[3] for e in edges],
    })


def test_only_outgoing_t4t5_connections_flip():
    con = table()
    out, report = correct_signs(con, [T4, T5])

    assert out["Excitatory"].tolist() == [1, 1, 1, -1, -1]
    assert out["Excitatory x Connectivity"].tolist() == [10, 4, 7, -5, -3]
    assert (out["Connectivity"] == con["Connectivity"]).all()
    assert report.neurons == 2 and report.neurons_flipped == 2
    assert report.connections_flipped == 2 and report.synapses_flipped == 17
    assert report.rows_total == 5


def test_original_table_is_not_modified():
    con = table()
    before = con.copy()
    correct_signs(con, [T4, T5])
    pd.testing.assert_frame_equal(con, before)


def test_type_list_is_t4_t5_a_to_d():
    assert T4T5_TYPES == ("T4a", "T4b", "T4c", "T4d", "T5a", "T5b", "T5c", "T5d")
