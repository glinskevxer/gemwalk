"""The naming and error checks pass here, and they can see a fault."""

from __future__ import annotations

import ast

import pytest

from gemwalk.errors import DesignError
from gemwalk.tools import check_errors, check_naming
from gemwalk.tools.walker import Module, package_root


def a_module(source: str, name: str = "gemwalk.service.probe") -> Module:
    return Module(package_root() / "service" / "probe.py", name, ast.parse(source))


@pytest.mark.repo
def test_no_name_in_the_package_says_nothing() -> None:
    assert check_naming.main() == 0


@pytest.mark.parametrize("word", ["data", "manager", "helper", "utils", "temp", "process"])
def test_a_word_that_says_nothing_is_found(word: str) -> None:
    assert check_naming.is_vague(word)
    assert check_naming.is_vague(word.upper())


def test_a_name_built_out_of_a_vague_word_is_found() -> None:
    assert check_naming.is_vague("site_data")
    assert check_naming.is_vague("temp_reading")
    assert not check_naming.is_vague("temperature")


def test_a_name_that_says_something_is_left_alone() -> None:
    for name in ("wellhead", "exceedance", "install_due", "methane_share"):
        assert not check_naming.is_vague(name)


def test_a_vague_function_name_is_found() -> None:
    faults = check_naming.faults_in(
        a_module('"""m."""\n\n\ndef process() -> None:\n    """p."""\n')
    )
    assert any("process says nothing" in fault for fault in faults)


def test_a_vague_argument_name_is_found() -> None:
    source = '"""m."""\n\n\ndef read(data: int) -> None:\n    """r."""\n'
    faults = check_naming.faults_in(a_module(source))
    assert any("data says nothing" in fault for fault in faults)


def test_a_vague_assignment_is_found() -> None:
    faults = check_naming.faults_in(a_module('"""m."""\n\nstuff = 1\n'))
    assert any("stuff says nothing" in fault for fault in faults)


def test_a_vague_module_name_is_found() -> None:
    faults = check_naming.faults_in(a_module('"""m."""\n', "gemwalk.service.helpers"))
    assert any("the module itself" in fault for fault in faults)


def test_a_word_in_a_docstring_is_not_a_name() -> None:
    source = '"""The manager reads this, and the data is on the sheet."""\n'
    assert check_naming.faults_in(a_module(source)) == []


@pytest.mark.repo
def test_every_raise_in_the_package_is_one_of_ours() -> None:
    assert check_errors.main() == 0


def test_a_builtin_raise_is_found() -> None:
    source = '"""m."""\n\n\ndef go() -> None:\n    """g."""\n    raise ValueError("no")\n'
    faults = check_errors.faults_in(a_module(source))
    assert any("raises ValueError" in fault for fault in faults)


def test_a_raise_of_one_of_ours_is_allowed() -> None:
    source = (
        '"""m."""\n\nfrom gemwalk.errors import RuleError\n\n\n'
        'def go() -> None:\n    """g."""\n    raise RuleError("a", "b")\n'
    )
    assert check_errors.faults_in(a_module(source)) == []


def test_a_bare_re_raise_is_allowed() -> None:
    source = (
        '"""m."""\n\n\ndef go() -> None:\n    """g."""\n'
        "    try:\n        pass\n    except Exception:\n        raise\n"
    )
    assert check_errors.faults_in(a_module(source)) == []


def test_not_implemented_is_allowed_because_it_is_a_stub() -> None:
    source = '"""m."""\n\n\ndef go() -> None:\n    """g."""\n    raise NotImplementedError\n'
    assert check_errors.faults_in(a_module(source)) == []


def test_the_errors_module_is_allowed_to_name_builtins() -> None:
    source = '"""m."""\n\n\ndef go() -> None:\n    """g."""\n    raise ValueError("x")\n'
    assert check_errors.faults_in(a_module(source, "gemwalk.errors")) == []


def test_a_tool_may_raise_what_it_likes() -> None:
    source = '"""m."""\n\n\ndef go() -> None:\n    """g."""\n    raise RuntimeError("x")\n'
    module = Module(package_root() / "tools" / "probe.py", "gemwalk.tools.probe", ast.parse(source))
    assert check_errors.faults_in(module) == []


def test_a_design_error_says_what_was_put_together_wrongly() -> None:
    failure = DesignError("windows", "the three windows have to widen")
    assert failure.what == "windows"
    assert "widen" in str(failure)
