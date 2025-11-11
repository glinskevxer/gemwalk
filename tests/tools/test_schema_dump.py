"""The schema file is written out of a real book."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemwalk.store.migrations import MIGRATIONS
from gemwalk.tools import schema_dump
from gemwalk.tools.walker import repo_root


def test_the_schema_file_on_disk_is_current() -> None:
    assert schema_dump.main(["--check"]) == 0


def test_the_file_is_in_the_checkout() -> None:
    assert (repo_root() / schema_dump.TARGET).exists()


def test_the_dump_names_every_table() -> None:
    text = schema_dump.dump()
    for table in ("site", "area", "device", "reading", "exceedance", "hit", "work_order"):
        assert f"CREATE TABLE {table}" in text


def test_the_dump_carries_the_indexes_too() -> None:
    assert "CREATE INDEX device_by_area" in schema_dump.dump()


def test_the_dump_says_which_migration_it_is_at() -> None:
    assert f"migration {MIGRATIONS[-1].number}" in schema_dump.dump()


def test_the_dump_puts_the_tables_before_the_indexes() -> None:
    text = schema_dump.dump()
    assert text.index("CREATE TABLE site") < text.index("CREATE INDEX")


def test_an_alter_shows_up_in_the_table_it_altered() -> None:
    text = schema_dump.dump()
    assert "lateral" in text.split("CREATE TABLE device")[1].split(";")[0]


def test_writing_the_file_makes_the_check_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(schema_dump, "repo_root", lambda: tmp_path)
    assert schema_dump.main(["--check"]) == 1
    assert "is not the schema" in capsys.readouterr().out
    assert schema_dump.main([]) == 0
    assert schema_dump.main(["--check"]) == 0


def test_a_stale_file_is_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(schema_dump, "repo_root", lambda: tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / schema_dump.TARGET).write_text("CREATE TABLE old (x TEXT);\n")
    assert schema_dump.main(["--check"]) == 1
