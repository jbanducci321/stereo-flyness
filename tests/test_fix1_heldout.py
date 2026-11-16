"""Fix 1, step 4's verdicts (docs/notes/fix1_heldout_plan.md): the test, the no-harm check."""

import numpy as np

from stereo_flyness.experiments import fix1_heldout as H


def test_groups_passed_counts_cleared_groups():
    assert H.groups_passed(["cleared", "cleared", "died", "not reached"]) == 2
    assert H.groups_passed(["cleared"] * 4) == 4
    assert H.groups_passed([]) == 0


def test_a_level_scores_its_median_run():
    assert H.level_score([3, 7, 5]) == 5
    assert H.level_score([2, 2, 9]) == 2


def test_compare_counts_better_worse_tied():
    fixed, unfixed = {"a": 5, "b": 3, "c": 4, "d": 1}, {"a": 4, "b": 3, "c": 6, "d": 1}
    assert H.compare(fixed, unfixed) == (1, 1, 2)


def test_the_bar_needs_more_better_and_p_below_005():
    assert H.bar_verdict(12, 0)[0]  # p = 0.0005
    assert not H.bar_verdict(5, 0)[0]  # p = 0.0625
    assert not H.bar_verdict(0, 12)[0]  # significant, the wrong way
    assert not H.bar_verdict(0, 0)[0]


def test_no_harm_fails_on_more_worse_or_a_significant_drop():
    assert H.no_harm_verdict(3, 3)[:2] == (True, True)
    assert H.no_harm_verdict(2, 3)[:2] == (True, False)  # worse on more levels, not significant
    assert H.no_harm_verdict(0, 8)[:2] == (False, False)  # p = 0.0078
    assert H.no_harm_verdict(0, 0)[:2] == (True, True)


def test_the_arms_must_match_until_fix_1_changes_a_frame():
    u = np.array([0, 1, 0, 0, 1, 0], bool)
    none = np.zeros(6, bool)
    assert H.arms_diverge(u, u.copy(), none) is None  # nothing changed, identical
    assert "changed no frame" in H.arms_diverge(u, ~u, none)  # nothing changed, yet different
    pred = np.array([0, 0, 0, 1, 0, 0], bool)
    after = u.copy(); after[4] = False
    assert H.arms_diverge(u, after, pred) is None  # differs only after the first changed frame
    before = u.copy(); before[1] = False
    assert "before" in H.arms_diverge(u, before, pred)
    assert "length" in H.arms_diverge(u, u, np.zeros(5, bool))
