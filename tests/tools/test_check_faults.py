"""Every check can see the fault it exists to see.

A check that has never failed in anger is a check nobody knows the shape of.
These plant one of each on purpose and read the message that comes back, which
is the only way to be sure that a green run means what it looks like it means.
"""

from __future__ import annotations

import ast
from pathlib import Path

import click
import pytest

from gemwalk.tools import (
    check_cli,
    check_layers,
    check_package,
    release_check,
)
from gemwalk.tools.walker import Module, package_root


def a_module(source: str, name: str) -> Module:
    return Module(package_root() / "probe.py", name, ast.parse(source), source)


def test_a_module_with_no_layer_written_down_is_found() -> None:
    faults = check_layers.faults_in(a_module('"""m."""\n', "gemwalk.badgers.probe"))
    assert any("no layer is written down" in fault for fault in faults)


def test_an_import_that_runs_uphill_is_found() -> None:
    source = '"""m."""\n\nfrom gemwalk.cli.main import main\n'
    faults = check_layers.faults_in(a_module(source, "gemwalk.model.probe"))
    assert any("imports gemwalk.cli.main at layer 5" in fault for fault in faults)


def test_an_import_that_runs_downhill_is_not_a_fault() -> None:
    source = '"""m."""\n\nfrom gemwalk.units import Percent\n'
    assert check_layers.faults_in(a_module(source, "gemwalk.cli.probe")) == []


def test_an_import_of_something_outside_the_package_is_ignored() -> None:
    source = '"""m."""\n\nimport click\n'
    assert check_layers.faults_in(a_module(source, "gemwalk.model.probe")) == []


def test_a_command_with_no_help_is_found() -> None:
    group = click.Group("probe")

    @group.command("go")
    def go() -> None:
        pass

    faults = [
        f"{path} says nothing" for path, command in check_cli.commands(group) if not command.help
    ]
    assert faults == ["go says nothing"]


def test_an_option_with_no_help_is_found() -> None:
    group = click.Group("probe")

    @group.command("go")
    @click.option("--quietly", is_flag=True)
    def go(quietly: bool) -> None:
        """Go."""

    naked = [
        parameter
        for _, command in check_cli.commands(group)
        for parameter in command.params
        if isinstance(parameter, click.Option) and not parameter.help
    ]
    assert [p.name for p in naked] == ["quietly"]


def test_a_walk_file_that_is_not_there_reads_as_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(check_cli, "repo_root", lambda: tmp_path)
    assert check_cli.spoken_in_the_walk() == []
    assert check_cli.walk_faults() == []


def test_a_name_exported_and_not_defined_is_a_fault(monkeypatch: pytest.MonkeyPatch) -> None:
    module = a_module('"""m."""\n\n__all__ = ["missing"]\n', "gemwalk.probe")
    monkeypatch.setattr(check_package, "modules", lambda: [module])
    faults = check_package.export_faults()
    assert any("which is not here" in fault for fault in faults)


def test_a_name_exported_twice_is_a_fault(monkeypatch: pytest.MonkeyPatch) -> None:
    source = '"""m."""\n\nX = 1\n__all__ = ["X", "X"]\n'
    module = a_module(source, "gemwalk.probe")
    monkeypatch.setattr(check_package, "modules", lambda: [module])
    faults = check_package.export_faults()
    assert any("twice" in fault for fault in faults)


def test_a_module_with_a_tuple_of_exports_reads_the_same_way() -> None:
    module = a_module('"""m."""\n\nX = 1\n__all__ = ("X",)\n', "gemwalk.probe")
    assert check_package.exported(module) == ["X"]


def test_a_version_that_disagrees_with_pyproject_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_package, "pyproject", lambda: {"version": "9.9.9"})
    faults = check_package.version_faults()
    assert any("pyproject says version" in fault for fault in faults)


def test_a_pyproject_with_no_project_table_reads_as_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(check_package, "repo_root", lambda: tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n")
    assert check_package.pyproject() == {}


def test_a_constraints_file_that_is_not_there_pins_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(check_package, "repo_root", lambda: tmp_path)
    assert check_package.pinned() == set()


def test_a_changelog_that_is_not_there_says_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release_check, "repo_root", lambda: tmp_path)
    assert release_check.changelog_faults() == []


def test_a_pyproject_with_no_scripts_says_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release_check, "pyproject", dict)
    assert release_check.script_faults() == []


def test_a_project_with_no_description_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(release_check, "pyproject", dict)
    faults = release_check.description_faults()
    assert any("no description" in fault for fault in faults)
