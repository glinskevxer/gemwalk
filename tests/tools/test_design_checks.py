"""The command line and the design checks."""

from __future__ import annotations

import ast

import click
import pytest

from gemwalk.cli.main import main as tree
from gemwalk.tools import check_cli, check_design
from gemwalk.tools.walker import Module, package_root


def a_module(source: str, name: str = "gemwalk.model.probe") -> Module:
    return Module(package_root() / "model" / "probe.py", name, ast.parse(source))


def test_every_command_and_option_describes_itself() -> None:
    assert check_cli.described() == []


def test_the_whole_command_check_passes() -> None:
    assert check_cli.main() == 0


def test_the_tree_carries_every_group_and_its_commands() -> None:
    found = dict(check_cli.commands(tree))
    assert "site" in found
    assert "site open" in found
    assert "run post" in found
    assert "report quarter" in found


def test_a_command_with_no_help_is_found() -> None:
    group = click.Group("probe")

    @group.command("go")
    def go() -> None:
        pass

    faults = [
        f"{path} says nothing about what it does"
        for path, command in check_cli.commands(group)
        if not command.help
    ]
    assert faults == ["go says nothing about what it does"]


def test_the_paths_the_tree_answers_to_include_the_groups() -> None:
    paths = check_cli.paths()
    assert "well drill" in paths
    assert "store init" in paths


def test_a_walk_that_names_a_command_that_does_not_exist_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_cli, "spoken_in_the_walk", lambda: ["well badger"])
    faults = check_cli.walk_faults()
    assert any("nothing answers to it" in fault for fault in faults)


def test_a_walk_that_names_real_commands_is_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_cli, "spoken_in_the_walk", lambda: ["well drill", "store init"])
    assert check_cli.walk_faults() == []


def test_a_walk_that_reads_as_nothing_at_all_is_a_fault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_cli, "spoken_in_the_walk", list)
    faults = check_cli.walk_faults()
    assert any("nothing in it was read" in fault for fault in faults)


def test_the_book_option_comes_off_before_the_command_is_read() -> None:
    spoken = check_cli.spoken_in_the_walk()
    assert "store init" in spoken
    assert not any(command.startswith("--book") for command in spoken)


def test_the_model_is_frozen_all_the_way_through() -> None:
    assert check_design.main() == 0


def test_a_model_record_that_is_not_frozen_is_found() -> None:
    source = (
        '"""m."""\n\nfrom dataclasses import dataclass\n\n\n'
        '@dataclass\nclass Reading:\n    """r."""\n\n    value: int\n'
    )
    faults = check_design.faults_in(a_module(source))
    assert any("Reading is not frozen" in fault for fault in faults)


def test_a_frozen_record_is_left_alone() -> None:
    source = (
        '"""m."""\n\nfrom dataclasses import dataclass\n\n\n'
        '@dataclass(frozen=True)\nclass Reading:\n    """r."""\n\n    value: int\n'
    )
    assert check_design.faults_in(a_module(source)) == []


def test_a_record_outside_the_model_may_be_changed() -> None:
    source = (
        '"""m."""\n\nfrom dataclasses import dataclass\n\n\n'
        '@dataclass\nclass Posting:\n    """p."""\n\n    value: int\n'
    )
    assert check_design.faults_in(a_module(source, "gemwalk.service.probe")) == []


def test_a_mutable_default_is_found_anywhere_in_the_package() -> None:
    source = '"""m."""\n\n\ndef go(seen: list[int] = []) -> None:\n    """g."""\n'
    faults = check_design.faults_in(a_module(source, "gemwalk.service.probe"))
    assert any("mutable default" in fault for fault in faults)


def test_a_keyword_only_mutable_default_is_found_too() -> None:
    source = '"""m."""\n\n\ndef go(*, seen: dict[str, int] = {}) -> None:\n    """g."""\n'
    faults = check_design.faults_in(a_module(source, "gemwalk.service.probe"))
    assert any("mutable default" in fault for fault in faults)


def test_an_immutable_default_is_left_alone() -> None:
    source = '"""m."""\n\n\ndef go(seen: tuple[int, ...] = ()) -> None:\n    """g."""\n'
    assert check_design.faults_in(a_module(source, "gemwalk.service.probe")) == []


def test_a_plain_class_is_not_a_record() -> None:
    source = '"""m."""\n\n\nclass Desk:\n    """d."""\n'
    assert check_design.faults_in(a_module(source)) == []
