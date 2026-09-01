"""The sql and index checks pass here, and they can see a fault."""

from __future__ import annotations

import ast

import pytest

from gemwalk.store.book import Book
from gemwalk.store.migrations import migrate
from gemwalk.tools import check_indexes, check_sql
from gemwalk.tools.walker import Module, package_root


def a_module(source: str, name: str = "gemwalk.report.probe") -> Module:
    return Module(package_root() / "report" / "probe.py", name, ast.parse(source))


@pytest.mark.repo
def test_no_module_outside_the_store_writes_sql() -> None:
    assert check_sql.main() == 0


def test_a_query_in_a_report_is_found() -> None:
    faults = check_sql.faults_in(a_module('"""m."""\n\nQ = "SELECT * FROM device"\n'))
    assert len(faults) == 1
    assert "sql outside the store" in faults[0]


def test_a_query_in_the_store_is_allowed() -> None:
    module = a_module('"""m."""\n\nQ = "SELECT 1"\n', "gemwalk.store.probe")
    assert check_sql.faults_in(module) == []


def test_an_ordinary_sentence_is_not_a_statement() -> None:
    source = '"""m."""\n\nWORDS = "update the valve and read it again"\n'
    assert check_sql.faults_in(a_module(source)) == []


def test_a_script_needs_its_statements_on_separate_lines() -> None:
    assert check_sql.STATEMENTS.match("SELECT 1") is not None
    assert check_sql.STATEMENTS.match("select 1") is None


def test_a_pragma_outside_the_store_is_found() -> None:
    faults = check_sql.faults_in(a_module('"""m."""\n\nQ = "PRAGMA foreign_keys"\n'))
    assert len(faults) == 1


def test_the_walker_finds_every_string_in_a_module() -> None:
    found = check_sql.strings_in(a_module('"""m."""\n\nA = "one"\nB = "two"\n'))
    assert {text for _, text in found} >= {"one", "two"}


@pytest.mark.repo
def test_every_foreign_key_in_the_schema_has_an_index() -> None:
    assert check_indexes.main() == 0


def test_a_key_with_no_index_behind_it_is_found() -> None:
    with Book.memory() as book:
        migrate(book)
        book.script(
            "CREATE TABLE probe (label TEXT PRIMARY KEY, "
            "device TEXT NOT NULL REFERENCES device(label));"
        )
        faults = check_indexes.faults_in(book)
    assert any("probe.device" in fault for fault in faults)


def test_a_key_with_an_index_is_not_found() -> None:
    with Book.memory() as book:
        migrate(book)
        book.script(
            "CREATE TABLE probe (label TEXT PRIMARY KEY, "
            "device TEXT NOT NULL REFERENCES device(label));\n"
            "CREATE INDEX probe_by_device ON probe(device);"
        )
        assert check_indexes.faults_in(book) == []


def test_a_key_that_is_the_primary_key_needs_no_second_index() -> None:
    with Book.memory() as book:
        migrate(book)
        book.script("CREATE TABLE probe (device TEXT PRIMARY KEY REFERENCES device(label));")
        assert check_indexes.faults_in(book) == []


@pytest.mark.repo
@pytest.mark.parametrize("table", ["device", "reading", "exceedance", "hit", "work_order"])
def test_the_tables_that_carry_keys_have_their_indexes(table: str) -> None:
    with Book.memory() as book:
        migrate(book)
        covered = check_indexes.indexed_columns(book, table)
        keys = {str(row["from"]) for row in book.all(f"PRAGMA foreign_key_list('{table}')")}
        assert keys <= covered
