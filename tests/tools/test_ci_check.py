"""The two lists of what has to pass, and the package, all agree."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemwalk.tools import check_ci
from gemwalk.tools.walker import repo_root


@pytest.mark.repo
def test_the_check_script_and_the_workflow_agree() -> None:
    assert check_ci.main() == 0
    assert check_ci.faults() == []


@pytest.mark.repo
def test_the_package_has_the_tools_both_lists_name() -> None:
    have = check_ci.tools()
    assert "check_layers" in have
    assert "check_handbook" in have
    assert "walker" not in have
    assert "smoke" not in have


@pytest.mark.repo
def test_both_files_name_every_tool() -> None:
    have = check_ci.tools()
    assert have <= check_ci.named_in(check_ci.SCRIPT)
    assert have <= check_ci.named_in(check_ci.WORKFLOW)


@pytest.mark.repo
def test_the_check_script_names_its_tools_in_a_loop() -> None:
    text = (repo_root() / check_ci.SCRIPT).read_text()
    found = check_ci._from_loop(text)
    assert "check_layers" in found
    assert "release_check" in found
    assert "check" not in found


def test_a_tool_the_script_does_not_run_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_ci, "tools", lambda: {"check_layers", "check_badgers"})
    faults = check_ci.faults()
    assert any("check_badgers is a tool and check.sh" in fault for fault in faults)


def test_a_script_naming_a_tool_that_is_gone_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_ci, "tools", lambda: set())
    monkeypatch.setattr(
        check_ci, "named_in", lambda path: {"check_ghost"} if path == check_ci.SCRIPT else set()
    )
    faults = check_ci.faults()
    assert any("there is no such tool" in fault for fault in faults)


def test_a_missing_file_names_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_ci, "repo_root", lambda: tmp_path)
    assert check_ci.named_in(check_ci.SCRIPT) == set()


def test_a_script_that_runs_no_tools_is_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check_ci, "repo_root", lambda: tmp_path)
    assert check_ci.main() == 1
    assert "runs no tools at all" in capsys.readouterr().out


def test_a_workflow_that_runs_no_tools_is_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        check_ci,
        "named_in",
        lambda path: {"check_layers"} if path == check_ci.SCRIPT else set(),
    )
    assert check_ci.main() == 1
    assert "runs no tools at all" in capsys.readouterr().out


@pytest.mark.repo
def test_the_check_is_in_both_lists_itself() -> None:
    assert "check_ci" in (repo_root() / check_ci.SCRIPT).read_text()
    assert "check_ci" in (repo_root() / check_ci.WORKFLOW).read_text()
