"""The two generated documents come out of the code they describe."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemwalk.model.device import State
from gemwalk.rules import STANDARDS, Finding
from gemwalk.tools import build_glossary, build_rules
from gemwalk.tools.walker import repo_root


@pytest.mark.repo
def test_the_rules_document_on_disk_is_current() -> None:
    assert build_rules.main(["--check"]) == 0


@pytest.mark.repo
def test_the_glossary_on_disk_is_current() -> None:
    assert build_glossary.main(["--check"]) == 0


@pytest.mark.repo
def test_both_documents_are_in_the_checkout() -> None:
    assert (repo_root() / build_rules.TARGET).exists()
    assert (repo_root() / build_glossary.TARGET).exists()


def test_every_standard_has_a_section() -> None:
    text = build_rules.build()
    for code in STANDARDS:
        assert f"## Subpart {code}" in text


def test_the_temperature_limit_is_written_in_both_units() -> None:
    text = build_rules.build()
    assert "131.0 F" in text
    assert "(55 C)" in text


def test_the_standard_with_no_nitrogen_alternative_says_so() -> None:
    section = build_rules.build().split("## Subpart WWW")[1].split("## Subpart")[0]
    assert "not available" in section
    assert "Nitrogen may stand in for oxygen: no." in section


def test_the_newer_standards_say_they_have_one() -> None:
    section = build_rules.build().split("## Subpart XXX")[1].split("## Subpart")[0]
    assert "Nitrogen may stand in for oxygen: yes." in section


def test_the_remonitor_window_says_where_it_is_counted_from() -> None:
    assert "10 calendar days from the repair" in build_rules.build()


def test_every_finding_is_listed_with_its_limit_family() -> None:
    text = build_rules.build()
    for finding in Finding:
        assert f"**{finding}**" in text


def test_every_enumeration_member_is_in_the_glossary() -> None:
    text = build_glossary.build()
    for _, _, group in build_glossary.GROUPS:
        for member in group:
            assert f"**{member.value}**" in text


def test_the_glossary_names_the_enumeration_a_word_comes_from() -> None:
    assert "`State.ABANDONED`" in build_glossary.build()
    assert str(State.ABANDONED) == "abandoned"


def test_writing_the_rules_makes_the_check_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(build_rules, "repo_root", lambda: tmp_path)
    assert build_rules.main(["--check"]) == 1
    assert "out of date" in capsys.readouterr().out
    assert build_rules.main([]) == 0
    assert build_rules.main(["--check"]) == 0


def test_writing_the_glossary_makes_the_check_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(build_glossary, "repo_root", lambda: tmp_path)
    assert build_glossary.main(["--check"]) == 1
    assert build_glossary.main([]) == 0
    assert build_glossary.main(["--check"]) == 0


def test_a_stale_document_is_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(build_glossary, "repo_root", lambda: tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / build_glossary.TARGET).write_text("# old\n")
    assert build_glossary.main(["--check"]) == 1
