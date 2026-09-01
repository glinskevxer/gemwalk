"""The writing conventions, and what breaks them."""

from __future__ import annotations

import ast

import pytest

from gemwalk.tools import check_style
from gemwalk.tools.walker import Module, package_root


def a_module(source: str, name: str = "gemwalk.service.probe") -> Module:
    return Module(package_root() / "service" / "probe.py", name, ast.parse(source), source)


@pytest.mark.repo
def test_the_package_is_written_the_way_it_says_it_is() -> None:
    assert check_style.main() == 0


def test_a_first_line_that_is_not_a_sentence_is_found() -> None:
    faults = check_style.sentence_faults(a_module('"""a module"""\n'))
    assert any("does not end a sentence" in fault for fault in faults)


def test_a_first_line_that_is_a_sentence_is_left_alone() -> None:
    assert check_style.sentence_faults(a_module('"""A module."""\n')) == []


def test_a_first_line_that_introduces_a_list_is_allowed() -> None:
    assert check_style.sentence_faults(a_module('"""The three of them are:"""\n')) == []


def test_every_docstring_in_a_module_is_read() -> None:
    source = (
        '"""A module."""\n\n\nclass A:\n    """A class."""\n\n'
        '    def go(self) -> None:\n        """A method."""\n'
    )
    found = check_style.docstrings_in(a_module(source))
    assert [said for _, said in found] == ["A module.", "A class.", "A method."]


def test_a_library_that_prints_is_found() -> None:
    source = '"""A module."""\n\n\ndef go() -> None:\n    """Go."""\n    print("hello")\n'
    faults = check_style.print_faults(a_module(source))
    assert any("a library that prints" in fault for fault in faults)


def test_a_tool_may_print() -> None:
    source = '"""A module."""\n\n\ndef go() -> None:\n    """Go."""\n    print("hello")\n'
    module = Module(package_root() / "tools" / "probe.py", "gemwalk.tools.probe", ast.parse(source))
    assert check_style.print_faults(module) == []


def test_the_command_line_may_print() -> None:
    source = '"""A module."""\n\n\ndef go() -> None:\n    """Go."""\n    print("hello")\n'
    module = Module(
        package_root() / "cli" / "probe.py", "gemwalk.cli.probe", ast.parse(source), source
    )
    assert check_style.print_faults(module) == []


def test_an_assert_outside_the_tools_is_found() -> None:
    source = '"""A module."""\n\n\ndef go(x: int) -> None:\n    """Go."""\n    assert x\n'
    faults = check_style.assert_faults(a_module(source))
    assert any("compiled out under -O" in fault for fault in faults)


def test_a_tool_may_assert() -> None:
    source = '"""A module."""\n\n\ndef go(x: int) -> None:\n    """Go."""\n    assert x\n'
    module = Module(package_root() / "tools" / "probe.py", "gemwalk.tools.probe", ast.parse(source))
    assert check_style.assert_faults(module) == []


def test_a_note_to_nobody_is_found() -> None:
    source = '"""A module."""\n\n# TODO: come back to this\nX = 1\n'
    faults = check_style.note_faults(a_module(source))
    assert any("a note to nobody" in fault for fault in faults)


def test_the_word_in_a_string_is_not_a_note() -> None:
    source = '"""A module."""\n\nSUBPART = "XXX: the newer standard"\n'
    assert check_style.note_faults(a_module(source)) == []


def test_a_module_carries_its_own_source_when_it_has_no_file() -> None:
    source = '"""A module."""\n'
    assert a_module(source).source() == source


def test_the_whole_check_takes_all_four_together() -> None:
    source = '"""a module"""\n\n\ndef go(x: int) -> None:\n    """Go."""\n    assert x\n'
    faults = check_style.faults_in(a_module(source))
    assert len(faults) == 2


@pytest.mark.repo
def test_the_check_is_a_step_in_the_check_script_and_in_ci() -> None:
    from gemwalk.tools.walker import repo_root

    assert "check_style" in (repo_root() / "check.sh").read_text()
    assert "check_style" in (repo_root() / ".github/workflows/ci.yml").read_text()
