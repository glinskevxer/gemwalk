"""The check that asks whether a desk method has a caller."""

from __future__ import annotations

import ast

from gemwalk.tools import check_wiring
from gemwalk.tools.walker import Module, package_root


def a_module(source: str, name: str = "gemwalk.service.probe") -> Module:
    return Module(package_root() / "service" / "probe.py", name, ast.parse(source))


def test_every_desk_method_has_a_caller() -> None:
    assert check_wiring.main() == 0


def test_the_survey_finds_the_desks() -> None:
    found = check_wiring.survey()
    assert "SiteDesk.open_site" in found.methods
    assert "ComplianceDesk.post_run" in found.methods
    assert "open_site" in found.called_in_package


def test_a_public_method_is_listed_and_a_private_one_is_not() -> None:
    source = (
        '"""m."""\n\n\nclass Desk:\n    """d."""\n\n'
        '    def read(self) -> None:\n        """r."""\n\n'
        '    def _hidden(self) -> None:\n        """h."""\n'
    )
    methods = check_wiring.methods_of(a_module(source))
    assert "Desk.read" in methods
    assert "Desk._hidden" not in methods


def test_a_module_lists_every_attribute_it_reaches_for() -> None:
    calls = check_wiring.calls_in(a_module('"""m."""\n\nx = a.read()\ny = b.write\n'))
    assert calls == {"read", "write"}


def test_a_method_with_no_caller_at_all_is_found() -> None:
    found = check_wiring.Surface(methods={"Desk.forgotten": "probe.py:1"})
    faults = check_wiring.faults(found)
    assert faults == ["probe.py:1: Desk.forgotten has no caller at all"]


def test_a_method_only_the_suite_calls_is_told_apart() -> None:
    found = check_wiring.Surface(
        methods={"Desk.forgotten": "probe.py:1"}, called_in_suite={"forgotten"}
    )
    faults = check_wiring.faults(found)
    assert faults == ["probe.py:1: Desk.forgotten is only ever called by the suite"]


def test_a_method_the_package_calls_is_not_a_fault() -> None:
    found = check_wiring.Surface(methods={"Desk.used": "probe.py:1"}, called_in_package={"used"})
    assert check_wiring.faults(found) == []
