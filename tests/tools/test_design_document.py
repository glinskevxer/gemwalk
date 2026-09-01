"""The map of the package, written out of the package."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemwalk.tools import build_design
from gemwalk.tools.check_layers import LAYERS
from gemwalk.tools.walker import modules, repo_root


@pytest.mark.repo
def test_the_document_on_disk_is_current() -> None:
    assert build_design.main(["--check"]) == 0


@pytest.mark.repo
def test_the_document_is_in_the_checkout() -> None:
    assert (repo_root() / build_design.TARGET).exists()


@pytest.mark.repo
def test_every_module_with_a_layer_is_in_it() -> None:
    text = build_design.build()
    named = {
        module.name
        for module in modules()
        if not module.name.endswith("__init__") and module.name != "gemwalk"
    }
    for name in named:
        assert f"`{name}`" in text, name


@pytest.mark.repo
def test_every_part_is_in_the_table() -> None:
    text = build_design.build()
    for part in LAYERS:
        assert f"`gemwalk.{part}`" in text


@pytest.mark.repo
def test_the_layers_come_out_in_order() -> None:
    text = build_design.build()
    assert text.index("## Layer 0") < text.index("## Layer 1")
    assert text.index("## Layer 3") < text.index("## Layer 5")


@pytest.mark.repo
def test_each_module_carries_its_own_first_sentence() -> None:
    found = {module.name: module for module in modules()}
    sentence = build_design.first_sentence(found["gemwalk.units"])
    assert sentence.startswith("The quantities a wellhead reading is written in")
    assert sentence.endswith(".")


def test_a_sentence_with_no_full_stop_gets_one() -> None:
    import ast

    from gemwalk.tools.walker import Module, package_root

    module = Module(package_root() / "probe.py", "gemwalk.probe", ast.parse('"""A module"""\n'))
    assert build_design.first_sentence(module) == "A module."


@pytest.mark.repo
def test_the_modules_are_gathered_by_layer() -> None:
    by_layer = build_design.grouped()
    names = {module.name for module in by_layer[0]}
    assert "gemwalk.units" in names
    assert "gemwalk.rules" in names
    assert "gemwalk.store.book" not in names


def test_writing_the_document_makes_the_check_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(build_design, "repo_root", lambda: tmp_path)
    assert build_design.main(["--check"]) == 1
    assert "out of date" in capsys.readouterr().out
    assert build_design.main([]) == 0
    assert build_design.main(["--check"]) == 0


@pytest.mark.repo
def test_the_document_is_a_step_in_the_check_script_and_in_ci() -> None:
    assert "build_design" in (repo_root() / "check.sh").read_text()
    assert "build_design" in (repo_root() / ".github/workflows/ci.yml").read_text()


def test_a_release_wants_the_document() -> None:
    from gemwalk.tools import release_check

    assert build_design.TARGET in release_check.DOCUMENTS
