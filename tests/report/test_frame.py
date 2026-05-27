"""How a report is built and how it prints."""

from __future__ import annotations

import pytest

from gemwalk.errors import DesignError
from gemwalk.report.frame import (
    Align,
    Column,
    Report,
    Section,
    Table,
    money,
    number,
    share,
)


def a_table() -> Table:
    return Table(
        columns=(
            Column("well"),
            Column("methane", Align.RIGHT),
            Column("note", blank="none"),
        ),
        title="wellheads",
    )


def test_a_table_with_nothing_on_it_says_so() -> None:
    table = a_table()
    assert table.is_empty
    assert table.lines() == ["wellheads", "  nothing to report"]


def test_a_table_prints_its_headings_and_a_rule() -> None:
    table = a_table().add("VW-041", "52.4%", None)
    lines = table.lines()
    assert lines[0] == "wellheads"
    assert lines[1].startswith("well")
    assert set(lines[2]) <= {"-", " "}


def test_a_column_pushes_its_cells_the_way_it_says() -> None:
    table = a_table().add("VW-041", "52.4%", "seal")
    row = table.lines()[-1]
    assert row.startswith("VW-041")
    assert "52.4%" in row


def test_a_blank_cell_uses_the_column_s_own_word() -> None:
    table = a_table().add("VW-041", "52.4%", None)
    assert "none" in table.lines()[-1]


def test_a_column_widens_to_what_is_actually_in_it() -> None:
    narrow = a_table().add("VW-1", "1%", "x")
    wide = a_table().add("VW-000000000041", "1%", "x")
    assert wide.widths()[0] > narrow.widths()[0]


def test_a_row_of_the_wrong_length_is_refused() -> None:
    with pytest.raises(DesignError, match="cells for"):
        a_table().add("VW-041")


def test_several_rows_go_on_at_once() -> None:
    table = a_table().extend([("VW-041", "52%", "a"), ("VW-042", "48%", "b")])
    assert len(table.rows) == 2


def test_a_section_holds_text_and_tables() -> None:
    section = Section("wellfield")
    section.say("40 wellheads read").table(a_table().add("VW-041", "52%", "a"))
    lines = section.lines()
    assert lines[0] == "wellfield"
    assert "40 wellheads read" in lines
    assert not section.is_empty


def test_an_empty_section_knows_it_is_empty() -> None:
    section = Section("wellfield").table(a_table())
    assert section.is_empty


def test_a_report_carries_its_sections_in_order() -> None:
    report = Report("northridge", "april 2025")
    report.section("wellfield").say("40 read")
    report.section("surface").say("2 spots")
    assert [s.heading for s in report.sections] == ["wellfield", "surface"]
    found = report.find("surface")
    assert found is not None
    assert found.body == ["2 spots"]
    assert report.find("plant") is None


def test_a_report_renders_with_its_title_underlined() -> None:
    report = Report("northridge", "april 2025")
    report.section("wellfield").say("40 read")
    text = report.render()
    assert text.startswith("northridge\n==========\napril 2025")
    assert text.endswith("\n")
    assert str(report) == text


def test_a_report_lists_every_table_it_holds() -> None:
    report = Report("northridge")
    report.section("wellfield").table(a_table()).table(a_table())
    report.section("surface").table(a_table())
    assert len(report.tables()) == 3


def test_the_number_helpers_print_the_way_the_paperwork_does() -> None:
    assert money(1234.5) == "1,234.50"
    assert number(1234.56) == "1,234.6"
    assert number(1234.56, 3) == "1,234.560"
    assert share(0.5) == "50%"


def a_counting_table() -> Table:
    return Table(
        columns=(
            Column("well"),
            Column("readings", Align.RIGHT, adds_up=True),
            Column("findings", Align.RIGHT, adds_up=True),
        ),
        title="the year",
    )


def test_a_column_that_does_not_add_up_refuses_to_be_totalled() -> None:
    with pytest.raises(DesignError, match="does not add up"):
        a_counting_table().add("VW-001", 12, 1).total("well")


def test_a_column_nobody_has_is_refused() -> None:
    with pytest.raises(DesignError, match="no column called"):
        a_counting_table().total("badgers")


def test_a_column_adds_up() -> None:
    table = a_counting_table().extend([("VW-001", 12, 1), ("VW-002", 12, 0)])
    assert table.total("readings") == pytest.approx(24.0)
    assert table.totals() == {"readings": 24.0, "findings": 1.0}


def test_a_cell_that_is_not_a_number_is_skipped() -> None:
    table = a_counting_table().extend([("VW-001", 12, 1), ("VW-002", None, "-")])
    assert table.total("readings") == pytest.approx(12.0)


def test_a_flag_is_not_counted_as_a_number() -> None:
    table = a_counting_table().add("VW-001", True, 1)
    assert table.total("readings") == pytest.approx(0.0)


def test_a_table_with_totals_prints_a_footer() -> None:
    table = a_counting_table().extend([("VW-001", 12, 1), ("VW-002", 12, 0)])
    lines = table.lines()
    assert lines[-1].strip().startswith("24")
    assert set(lines[-2]) <= {"-", " "}


def test_a_table_with_no_totalling_columns_has_no_footer() -> None:
    table = a_table().add("VW-041", "52.4%", "seal")
    assert table.totals() == {}
    assert table.lines()[-1].startswith("VW-041")


def test_the_footer_widens_the_column_when_the_total_is_long() -> None:
    table = a_counting_table().add("VW-001", 1_000_000, 1)
    assert max(table.widths()) >= len("1e+06")


def test_the_annual_report_totals_its_tables() -> None:
    from gemwalk.report.annual import annual_report

    assert callable(annual_report)
