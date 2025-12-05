"""The coverage gate holds a total floor and a per file floor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gemwalk.tools import coverage_gate


def a_report(tmp_path: Path, files: dict[str, float], total: float) -> Path:
    body = {
        "totals": {"percent_covered": total},
        "files": {
            name: {"summary": {"percent_covered": percent, "missing_lines": 3}}
            for name, percent in files.items()
        },
    }
    path = tmp_path / coverage_gate.REPORT
    path.write_text(json.dumps(body))
    return path


def test_a_report_that_is_not_there_says_how_to_make_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(coverage_gate, "repo_root", lambda: tmp_path)
    assert coverage_gate.main([]) == 1
    assert "pytest --cov" in capsys.readouterr().out


def test_both_floors_held_is_a_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a_report(tmp_path, {"a.py": 99.0, "b.py": 92.0}, 97.0)
    monkeypatch.setattr(coverage_gate, "repo_root", lambda: tmp_path)
    assert coverage_gate.main([]) == 0
    assert "both floors held" in capsys.readouterr().out


def test_a_total_under_the_floor_is_a_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a_report(tmp_path, {"a.py": 99.0}, 80.0)
    monkeypatch.setattr(coverage_gate, "repo_root", lambda: tmp_path)
    assert coverage_gate.main([]) == 1
    assert "the total is 80.00%" in capsys.readouterr().out


def test_one_bad_file_fails_even_with_a_high_total(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a_report(tmp_path, {"a.py": 100.0, "thin.py": 41.0}, 97.9)
    monkeypatch.setattr(coverage_gate, "repo_root", lambda: tmp_path)
    assert coverage_gate.main([]) == 1
    printed = capsys.readouterr().out
    assert "thin.py is 41.00%" in printed
    assert "the total is" not in printed


def test_the_floors_can_be_moved(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    a_report(tmp_path, {"a.py": 100.0, "thin.py": 41.0}, 90.0)
    monkeypatch.setattr(coverage_gate, "repo_root", lambda: tmp_path)
    assert coverage_gate.main(["--floor", "85", "--file-floor", "40"]) == 0


def test_the_worst_files_are_printed_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a_report(tmp_path, {"a.py": 100.0, "b.py": 90.0, "c.py": 95.0}, 96.0)
    monkeypatch.setattr(coverage_gate, "repo_root", lambda: tmp_path)
    coverage_gate.main(["--worst", "2"])
    printed = capsys.readouterr().out
    assert printed.index("b.py") < printed.index("c.py")
    assert "a.py" not in printed


def test_a_report_reads_back_as_a_total_and_a_list(tmp_path: Path) -> None:
    path = a_report(tmp_path, {"a.py": 99.5}, 99.5)
    total, files = coverage_gate.read(path)
    assert total == pytest.approx(99.5)
    assert files[0].path == "a.py"
    assert files[0].missing == 3
    assert "99.50%" in str(files[0])


def test_an_argument_that_is_not_there_uses_the_default() -> None:
    assert coverage_gate.argument([], "--floor", 95.0) == pytest.approx(95.0)
    assert coverage_gate.argument(["--floor"], "--floor", 95.0) == pytest.approx(95.0)
    assert coverage_gate.argument(["--floor", "88"], "--floor", 95.0) == pytest.approx(88.0)
