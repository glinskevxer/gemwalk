"""The migration lock, and what it catches."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemwalk.store.migrations import MIGRATIONS, Migration
from gemwalk.tools import check_migrations
from gemwalk.tools.walker import repo_root


def test_the_lock_file_matches_the_migrations() -> None:
    assert check_migrations.main([]) == 0


def test_the_lock_file_is_in_the_checkout() -> None:
    assert (repo_root() / check_migrations.LOCK).exists()


def test_every_migration_is_on_a_line_of_its_own() -> None:
    assert len(check_migrations.written()) == len(MIGRATIONS)
    assert len(check_migrations.stored()) == len(MIGRATIONS)


def test_the_hash_changes_when_the_script_does() -> None:
    first = Migration(1, "a", "CREATE TABLE a (x TEXT);")
    second = Migration(1, "a", "CREATE TABLE a (x INTEGER);")
    assert check_migrations.digest(first) != check_migrations.digest(second)


def test_the_hash_is_the_same_for_the_same_script() -> None:
    script = "CREATE TABLE a (x TEXT);"
    assert check_migrations.digest(Migration(1, "a", script)) == check_migrations.digest(
        Migration(1, "b", script)
    )


def test_the_numbers_run_with_no_gaps() -> None:
    assert check_migrations.order_faults() == []


def test_a_gap_in_the_numbers_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        check_migrations,
        "MIGRATIONS",
        (Migration(1, "a", "SELECT 1;"), Migration(3, "b", "SELECT 2;")),
    )
    assert any("one to 2" in fault for fault in check_migrations.order_faults())


def test_two_migrations_with_one_name_are_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        check_migrations,
        "MIGRATIONS",
        (Migration(1, "a", "SELECT 1;"), Migration(2, "a", "SELECT 2;")),
    )
    assert any("share a name" in fault for fault in check_migrations.order_faults())


def test_migrations_out_of_order_are_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        check_migrations,
        "MIGRATIONS",
        (Migration(2, "a", "SELECT 1;"), Migration(1, "b", "SELECT 2;")),
    )
    faults = check_migrations.order_faults()
    assert any("number order" in fault for fault in faults)


def test_an_edited_script_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    edited = (
        Migration(MIGRATIONS[0].number, MIGRATIONS[0].name, MIGRATIONS[0].script + "\n"),
        *MIGRATIONS[1:],
    )
    monkeypatch.setattr(check_migrations, "MIGRATIONS", edited)
    faults = check_migrations.lock_faults()
    assert any("the package says" in fault for fault in faults)


def test_a_new_migration_that_is_not_locked_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        check_migrations,
        "MIGRATIONS",
        (*MIGRATIONS, Migration(len(MIGRATIONS) + 1, "new", "SELECT 1;")),
    )
    faults = check_migrations.lock_faults()
    assert any("--update" in fault for fault in faults)


def test_a_lock_line_with_no_migration_behind_it_is_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_migrations, "MIGRATIONS", MIGRATIONS[:-1])
    faults = check_migrations.lock_faults()
    assert any("no such migration" in fault for fault in faults)


def test_a_missing_lock_file_says_how_to_make_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(check_migrations, "repo_root", lambda: tmp_path)
    faults = check_migrations.lock_faults()
    assert any("is missing" in fault for fault in faults)


def test_update_writes_a_lock_file_that_then_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check_migrations, "repo_root", lambda: tmp_path)
    assert check_migrations.main(["--update"]) == 0
    assert "wrote" in capsys.readouterr().out
    assert check_migrations.lock_faults() == []
    assert (tmp_path / check_migrations.LOCK).read_text().startswith("#")
