import json

import pytest

from stereo_flyness.experiments.batches import BrokenProcessPool, play_with_retries, resumable


def flaky(breaks_after: list[int]):
    """A play_batch that breaks the pool after the given numbers of finished runs, once per call."""
    calls = []

    def play_batch(todo):
        calls.append(list(todo))
        limit = breaks_after[len(calls) - 1] if len(calls) <= len(breaks_after) else None
        for i, n in enumerate(todo):
            if limit is not None and i == limit:
                raise BrokenProcessPool("handle is invalid")
            yield {"level": n}
    return play_batch, calls


def test_retries_only_the_unfinished_runs():
    play, calls = flaky([2])
    out = play_with_retries(["a", "b", "c", "d"], play, log=lambda *_: None)
    assert [s["level"] for s in out] == ["a", "b", "c", "d"]
    assert calls == [["a", "b", "c", "d"], ["c", "d"]]


def test_gives_up_after_the_last_try():
    play, calls = flaky([0, 0, 0])
    with pytest.raises(BrokenProcessPool):
        play_with_retries(["a", "b"], play, tries=3, log=lambda *_: None)
    assert len(calls) == 3


def test_other_errors_are_not_retried():
    def play(todo):
        raise ValueError("a real bug")
        yield  # noqa
    with pytest.raises(ValueError):
        play_with_retries(["a"], play, log=lambda *_: None)


def run(tmp_path, name, commit):
    (tmp_path / name).mkdir()
    (tmp_path / name / "run.json").write_text(json.dumps({"commit": commit}))


def test_resume_skips_finished_runs_from_this_commit(tmp_path):
    run(tmp_path, "a", "abc")
    (tmp_path / "b").mkdir()  # cut off: no run.json
    assert resumable(["a", "b", "c"], tmp_path, "abc") == (["b", "c"], ["a"])


def test_resume_refuses_runs_from_another_commit_or_a_dirty_tree(tmp_path):
    run(tmp_path, "a", "old")
    with pytest.raises(ValueError):
        resumable(["a"], tmp_path, "abc")
    with pytest.raises(ValueError):
        resumable(["b"], tmp_path, "abc-dirty")
