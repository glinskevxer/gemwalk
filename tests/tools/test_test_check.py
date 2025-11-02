"""The check that asks whether anybody wrote a test about a module."""

from __future__ import annotations

from gemwalk.tools import check_tests
from gemwalk.tools.walker import modules


def test_every_module_in_the_package_is_named_by_the_suite() -> None:
    assert check_tests.main() == 0


def test_the_suite_names_the_modules_it_imports() -> None:
    named = check_tests.named_by_the_suite()
    assert "gemwalk.units" in named
    assert "gemwalk.store.repo" in named
    assert "gemwalk.cli.support" in named


def test_a_module_nobody_names_is_found() -> None:
    faults = check_tests.faults(set())
    assert len(faults) == len(list(modules())) - len(check_tests.SKIP)
    assert any("nothing in the suite imports" in fault for fault in faults)


def test_a_package_init_is_not_asked_about() -> None:
    assert "gemwalk.model" in check_tests.SKIP
    assert check_tests.faults(check_tests.named_by_the_suite()) == []
