"""The smoke walk runs, and it notices when a step goes wrong."""

from __future__ import annotations

import pytest

from gemwalk.tools.smoke import SmokeError, expect, insist, main


def test_the_whole_walk_runs_quietly() -> None:
    assert main(["--quiet"]) == 0


def test_the_whole_walk_prints_when_it_is_not_told_to_be_quiet(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == 0
    printed = capsys.readouterr().out
    assert "wellfield report" in printed
    assert "compliance report" in printed
    assert "every step did what it was supposed to" in printed


def test_a_step_that_gets_the_wrong_answer_names_itself() -> None:
    with pytest.raises(SmokeError, match="the roster"):
        expect("the roster", 5, 6)


def test_a_step_that_is_not_true_names_itself() -> None:
    with pytest.raises(SmokeError, match="the spot closed"):
        insist("the spot closed", False)


def test_a_step_that_is_true_says_nothing() -> None:
    insist("the spot closed", True)
    expect("the roster", 6, 6)
