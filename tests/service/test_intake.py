"""Taking a field sheet in, and saying what would not go."""

from __future__ import annotations

import datetime as dt

import pytest

from gemwalk.errors import RuleError
from gemwalk.service.intake import REQUIRED, IntakeDesk, read_sheet
from gemwalk.service.office import Office
from gemwalk.store.book import Book
from tests.support import SITE, furnish

APRIL = dt.date(2025, 4, 8)
HEADING = ",".join(("taken_on", *REQUIRED, "note"))
GOOD = "2025-04-08,{device},52.4,38.1,0.6,8.9,118.2,-1.4,-12.0,42.0,3.0,3.0,"


def sheet(*rows: str) -> str:
    return HEADING + "\n" + "\n".join(rows) + "\n"


@pytest.fixture
def office(book: Book) -> Office:
    return furnish(Office(book))


def a_run(office: Office) -> str:
    return office.monitoring.open_run(
        SITE, APRIL, monitor="D. Kasprzak", meter="GEM5000-40912"
    ).label


def test_a_clean_sheet_reads_every_row() -> None:
    read = read_sheet(sheet(GOOD.format(device="VW-001"), GOOD.format(device="VW-002")))
    assert read.is_clean
    assert [row.device for row in read.rows] == ["VW-001", "VW-002"]


def test_a_sheet_with_no_heading_says_so() -> None:
    read = read_sheet("")
    assert not read.is_clean
    assert "no heading row" in read.refused[0]


def test_a_sheet_missing_a_column_names_the_column() -> None:
    read = read_sheet("device,methane\nVW-001,52.4\n")
    assert "no carbon" in read.refused[0]


def test_a_row_with_no_device_is_refused_by_line() -> None:
    read = read_sheet(sheet(GOOD.format(device="")))
    assert read.refused == ["line 2: no device"]


def test_a_row_with_a_missing_number_names_the_column_and_the_line() -> None:
    row = GOOD.format(device="VW-001").replace(",118.2,", ",,")
    read = read_sheet(sheet(row))
    assert "line 2: VW-001 has no temperature" in read.refused[0]


def test_a_row_with_a_word_where_a_number_goes_says_what_it_read() -> None:
    row = GOOD.format(device="VW-001").replace(",118.2,", ",hot,")
    read = read_sheet(sheet(row))
    assert "'hot' is not a number" in read.refused[0]


def test_a_row_with_a_bad_date_is_refused() -> None:
    row = GOOD.format(device="VW-001").replace("2025-04-08,", "last thursday,")
    read = read_sheet(sheet(row))
    assert "is not a date" in read.refused[0]


def test_a_row_with_no_date_takes_the_day_of_the_run(office: Office) -> None:
    run = a_run(office)
    row = GOOD.format(device="VW-001").replace("2025-04-08,", ",")
    office.intake.take(run, sheet(row), on=APRIL)
    reading = office.monitoring.readings.on_run_for(run, "VW-001")
    assert reading is not None
    assert reading.taken_on == APRIL


def test_a_good_sheet_goes_in_whole(office: Office) -> None:
    run = a_run(office)
    taken = office.intake.take(
        run,
        sheet(*(GOOD.format(device=f"VW-00{n}") for n in range(1, 5))),
        on=APRIL,
    )
    assert taken.is_clean
    assert len(taken.recorded) == 4
    assert office.monitoring.missing(run) == []


def test_the_good_rows_go_in_and_the_bad_ones_are_named(office: Office) -> None:
    run = a_run(office)
    bad = GOOD.format(device="VW-002").replace(",118.2,", ",hot,")
    taken = office.intake.take(run, sheet(GOOD.format(device="VW-001"), bad), on=APRIL)
    assert taken.recorded == ["VW-001"]
    assert "line 3" in taken.refused[0]


def test_a_device_the_book_never_issued_is_refused_by_line(office: Office) -> None:
    run = a_run(office)
    taken = office.intake.take(run, sheet(GOOD.format(device="VW-999")), on=APRIL)
    assert taken.recorded == []
    assert "line 2" in taken.refused[0]
    assert "VW-999" in taken.refused[0]


def test_a_device_off_the_run_is_refused_by_line(office: Office) -> None:
    office.wellfield.take_offline("VW-002", dt.date(2025, 3, 1))
    run = a_run(office)
    taken = office.intake.take(run, sheet(GOOD.format(device="VW-002")), on=APRIL)
    assert "line 2" in taken.refused[0]


def test_all_or_nothing_writes_nothing_when_a_row_is_bad(office: Office) -> None:
    run = a_run(office)
    bad = GOOD.format(device="VW-002").replace(",118.2,", ",hot,")
    taken = office.intake.take(
        run, sheet(GOOD.format(device="VW-001"), bad), on=APRIL, all_or_nothing=True
    )
    assert taken.recorded == []
    assert office.monitoring.readings.of_run(run) == []


def test_all_or_nothing_rolls_back_a_row_the_book_refused(office: Office) -> None:
    run = a_run(office)
    with pytest.raises(RuleError, match="nothing was written"):
        office.intake.take(
            run,
            sheet(GOOD.format(device="VW-001"), GOOD.format(device="VW-999")),
            on=APRIL,
            all_or_nothing=True,
        )
    assert office.monitoring.readings.of_run(run) == []


def test_a_sheet_can_be_read_without_writing_any_of_it(office: Office) -> None:
    run = a_run(office)
    read = office.intake.preview(sheet(GOOD.format(device="VW-001")))
    assert read.is_clean
    assert office.monitoring.readings.of_run(run) == []


def test_the_desk_hands_out_a_heading_row_to_start_from(office: Office) -> None:
    assert office.intake.sample().startswith("taken_on,device,methane")


def test_a_run_reads_back_out_as_a_sheet_that_reads_in_again(office: Office) -> None:
    run = a_run(office)
    office.intake.take(run, sheet(GOOD.format(device="VW-001")), on=APRIL)
    written = office.intake.as_rows(office.monitoring.readings.of_run(run))
    assert read_sheet(written).is_clean
    assert "VW-001" in written


def test_an_intake_desk_is_made_once(office: Office) -> None:
    assert isinstance(office.intake, IntakeDesk)
    assert office.intake is office.intake
