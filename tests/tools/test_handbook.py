"""The handbook names commands that exist and gets to every part of the job."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemwalk.tools import check_handbook, release_check
from gemwalk.tools.walker import repo_root


@pytest.mark.repo
def test_the_handbook_is_in_the_checkout() -> None:
    assert (repo_root() / check_handbook.TARGET).exists()


@pytest.mark.repo
def test_the_handbook_names_only_real_commands() -> None:
    assert check_handbook.unknown() == []


@pytest.mark.repo
def test_the_handbook_gets_to_every_part_of_the_job() -> None:
    assert check_handbook.unwritten() == []


@pytest.mark.repo
def test_the_whole_check_passes() -> None:
    assert check_handbook.main() == 0


@pytest.mark.repo
def test_the_handbook_names_the_sequence_it_says_it_does() -> None:
    said = check_handbook.named()
    assert said[0] == "store init"
    assert "run post" in said
    assert "cover cross" in said
    assert said.index("run open") < said.index("run close")
    assert said.index("meter calibrate") < said.index("run open")


def test_a_handbook_naming_something_that_is_not_a_command_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_handbook, "named", lambda: ["well badger"])
    faults = check_handbook.unknown()
    assert any("nothing answers to it" in fault for fault in faults)


def test_a_handbook_that_never_gets_to_a_group_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_handbook, "named", lambda: ["store init"])
    faults = check_handbook.unwritten()
    assert any("whole group" in fault for fault in faults)
    assert any("cover" in fault for fault in faults)


def test_a_handbook_that_is_not_there_is_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check_handbook, "repo_root", lambda: tmp_path)
    assert check_handbook.main() == 1
    assert "is missing" in capsys.readouterr().out


def test_a_handbook_with_no_commands_in_it_is_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check_handbook, "repo_root", lambda: tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / check_handbook.TARGET).write_text("# nothing here\n")
    assert check_handbook.main() == 1
    assert "names no commands" in capsys.readouterr().out


@pytest.mark.repo
def test_a_release_wants_the_handbook() -> None:
    assert check_handbook.TARGET in release_check.DOCUMENTS
    assert release_check.missing_files() == []


@pytest.mark.repo
def test_the_check_is_a_step_in_the_check_script_and_in_ci() -> None:
    assert "check_handbook" in (repo_root() / "check.sh").read_text()
    assert "check_handbook" in (repo_root() / ".github/workflows/ci.yml").read_text()
