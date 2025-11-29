"""The package agrees with itself, and everything a release needs is here."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from gemwalk import __version__
from gemwalk.tools import check_package, release_check
from gemwalk.tools.walker import Module, package_root, repo_root


def a_module(source: str, name: str = "gemwalk.service.probe") -> Module:
    return Module(package_root() / "service" / "probe.py", name, ast.parse(source))


def test_the_package_agrees_with_itself() -> None:
    assert check_package.main() == 0


def test_the_version_is_written_in_two_places_and_they_agree() -> None:
    assert check_package.pyproject()["version"] == __version__
    assert check_package.version_faults() == []


def test_a_name_exported_and_not_defined_is_found() -> None:
    module = a_module('"""m."""\n\n__all__ = ["missing"]\n')
    names = check_package.exported(module)
    assert names == ["missing"]
    assert "missing" not in check_package.defined(module)


def test_a_module_with_no_exports_says_nothing() -> None:
    assert check_package.exported(a_module('"""m."""\n')) is None


def test_a_module_lists_what_it_defines_and_imports() -> None:
    source = (
        '"""m."""\n\nimport os\nfrom pathlib import Path\n\nX = 1\n'
        'Y: int = 2\n\n\ndef go() -> None:\n    """g."""\n\n\nclass A:\n    """a."""\n'
    )
    names = check_package.defined(a_module(source))
    assert {"os", "Path", "X", "Y", "go", "A"} <= names


def test_every_export_in_the_package_is_real() -> None:
    assert check_package.export_faults() == []


def test_every_direct_dependency_is_pinned() -> None:
    assert check_package.dependency_faults() == []
    assert "click" in check_package.pinned()
    assert "pytest" in check_package.pinned()


def test_a_dependency_that_is_not_pinned_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_package, "pinned", lambda: {"click"})
    faults = check_package.dependency_faults()
    assert any("constraints.txt does not pin it" in fault for fault in faults)


def test_a_dependency_with_no_pin_at_all_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_package, "pyproject", lambda: {"dependencies": ["click>=8"]})
    faults = check_package.dependency_faults()
    assert any("not pinned to one version" in fault for fault in faults)


def test_everything_a_release_needs_is_in_the_checkout() -> None:
    assert release_check.main() == 0
    assert release_check.missing_files() == []


def test_a_missing_file_is_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(release_check, "repo_root", lambda: tmp_path)
    faults = release_check.missing_files()
    assert len(faults) == len(release_check.REQUIRED) + len(release_check.DOCUMENTS)


def test_the_changelog_has_an_entry_for_this_version() -> None:
    assert release_check.changelog_faults() == []
    assert f"## {__version__}" in (repo_root() / "CHANGELOG.md").read_text()


def test_a_changelog_with_no_entry_is_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release_check, "repo_root", lambda: tmp_path)
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")
    faults = release_check.changelog_faults()
    assert any("no entry" in fault for fault in faults)


def test_the_console_script_points_at_something_that_exists() -> None:
    assert release_check.script_faults() == []


def test_a_console_script_pointing_at_nothing_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        release_check, "pyproject", lambda: {"scripts": {"gemwalk": "gemwalk.cli.main:absent"}}
    )
    faults = release_check.script_faults()
    assert any("there is no absent" in fault for fault in faults)


def test_a_console_script_pointing_at_no_module_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        release_check, "pyproject", lambda: {"scripts": {"gemwalk": "gemwalk.absent:run"}}
    )
    faults = release_check.script_faults()
    assert any("will not import" in fault for fault in faults)


def test_the_package_says_what_it_is_in_both_places() -> None:
    assert release_check.description_faults() == []


def test_a_readme_that_does_not_name_the_package_is_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release_check, "repo_root", lambda: tmp_path)
    (tmp_path / "README.md").write_text("# something else\n")
    faults = release_check.description_faults()
    assert any("does not name the package" in fault for fault in faults)
