"""The checks pass against this repository, and they can see a fault."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from gemwalk.tools import check_docstrings, check_layers
from gemwalk.tools.walker import (
    Module,
    modules,
    package_root,
    repo_root,
    report,
    suite_modules,
    suite_root,
)


def a_module(source: str, name: str = "gemwalk.model.probe") -> Module:
    return Module(package_root() / "model" / "probe.py", name, ast.parse(source))


def test_the_walker_finds_this_package(capsys: pytest.CaptureFixture[str]) -> None:
    names = {module.name for module in modules()}
    assert "gemwalk.units" in names
    assert "gemwalk.store.book" in names
    assert "gemwalk.cli.main" in names


def test_the_walker_finds_the_test_suite() -> None:
    names = {module.name for module in suite_modules()}
    assert "tests.support" in names
    assert suite_root().name == "tests"
    assert (repo_root() / "pyproject.toml").exists()


def test_a_module_knows_which_part_of_the_package_it_is_in() -> None:
    assert a_module("").package == "model"
    assert a_module("", "gemwalk").package == ""


def test_a_module_lists_what_it_imports() -> None:
    module = a_module("import os\nfrom gemwalk.units import Percent\nfrom . import x\n")
    assert module.imports() == ["os", "gemwalk.units", "gemwalk.units.Percent"]


def test_importing_a_module_by_name_names_the_module() -> None:
    module = a_module("from gemwalk.tools import check_sql\n")
    assert "gemwalk.tools.check_sql" in module.imports()


def test_reporting_nothing_is_a_pass(capsys: pytest.CaptureFixture[str]) -> None:
    assert report("check_x", []) == 0
    assert "nothing to report" in capsys.readouterr().out


def test_reporting_something_is_a_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert report("check_x", ["one", "two"]) == 1
    printed = capsys.readouterr().out
    assert "2 to fix" in printed
    assert "one" in printed


def test_the_package_has_a_docstring_everywhere_it_should(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert check_docstrings.main() == 0


def test_a_module_with_no_docstring_is_found() -> None:
    faults = check_docstrings.faults_in(a_module("x = 1\n"))
    assert any("module has no docstring" in fault for fault in faults)


def test_a_public_function_with_no_docstring_is_found() -> None:
    faults = check_docstrings.faults_in(a_module('"""m."""\n\n\ndef go() -> None:\n    pass\n'))
    assert any("go has no docstring" in fault for fault in faults)


def test_a_private_helper_needs_no_docstring() -> None:
    faults = check_docstrings.faults_in(a_module('"""m."""\n\n\ndef _go() -> None:\n    pass\n'))
    assert faults == []


def test_a_dunder_says_what_it_does_by_its_name() -> None:
    source = "\n".join(
        [
            '"""m."""',
            "",
            "",
            "class A:",
            '    """a."""',
            "",
            "    def __str__(self) -> str:",
            '        return ""',
        ]
    )
    assert check_docstrings.faults_in(a_module(source)) == []
    assert not check_docstrings.is_public("__str__")


def test_a_public_class_with_no_docstring_is_found() -> None:
    faults = check_docstrings.faults_in(a_module('"""m."""\n\n\nclass A:\n    pass\n'))
    assert any("A has no docstring" in fault for fault in faults)


def test_every_import_in_the_package_runs_downhill() -> None:
    assert check_layers.main() == 0


def test_every_part_of_the_package_has_a_layer() -> None:
    parts = {
        path.name
        for path in package_root().iterdir()
        if path.is_dir() and not path.name.startswith((".", "_"))
    }
    parts |= {path.stem for path in package_root().glob("*.py") if not path.stem.startswith("_")}
    assert parts <= set(check_layers.LAYERS)


def test_a_name_outside_the_package_has_no_layer() -> None:
    assert check_layers.layer_of("click") is None
    assert check_layers.layer_of("gemwalk") == 0
    assert check_layers.layer_of("gemwalk.store.book") == 2


def test_the_layer_file_lists_the_directories_that_exist() -> None:
    for part in check_layers.LAYERS:
        assert (package_root() / part).exists() or (package_root() / f"{part}.py").exists()


def test_a_test_module_is_not_in_the_package(tmp_path: Path) -> None:
    assert all(not module.name.startswith("tests") for module in modules())
