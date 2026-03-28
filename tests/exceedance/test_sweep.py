"""A sweep over the two clocks, because the difference between them is the point.

These are the same two rules the rest of the suite checks one case at a time.
The reason for walking them over a few hundred combinations instead is that
both clocks are made of dates, and a rule about dates that is right for one
pair of them is right for most pairs of them. What matters is whether it is
right for all of them: month boundaries, leap days, the day the window closes,
the day after, and a recheck taken on the day the record was opened.
"""

from __future__ import annotations

import datetime as dt
import itertools

import pytest

from gemwalk.model.exceedance import ORDER, Exceedance, Stage
from gemwalk.model.landfill import Cover
from gemwalk.model.surface import Hit, Step
from gemwalk.rules import CF, STANDARDS, WWW, XXX, Finding

DAYS = [
    dt.date(2025, 1, 1),
    dt.date(2025, 1, 31),
    dt.date(2025, 2, 26),
    dt.date(2024, 2, 28),
    dt.date(2024, 12, 20),
    dt.date(2025, 6, 30),
    dt.date(2025, 11, 2),
    dt.date(2025, 12, 28),
]
GAPS = [0, 1, 4, 5, 6, 14, 15, 16, 119, 120, 121, 400]


def an_exceedance(opened: dt.date, stage: Stage = Stage.CORRECT) -> Exceedance:
    return Exceedance(
        label="EX-2025-001",
        site="NORTHRIDGE",
        device="VW-041",
        kind=Finding.TEMPERATURE,
        opened_on=opened,
        reading=1,
        value=138.0,
        limit_value=131.0,
        stage=stage,
    )


def a_hit(found: dt.date) -> Hit:
    return Hit(
        label="SH-2025Q2-001",
        walk="SW-2025Q2-01",
        site="NORTHRIDGE",
        area="A-03",
        station="grid 14-J",
        reading=720.0,
        cover=Cover.INTERMEDIATE,
        found_on=found,
    )


@pytest.mark.parametrize(("opened", "stage"), list(itertools.product(DAYS, ORDER)))
def test_every_wellhead_window_is_counted_from_the_reading(opened: dt.date, stage: Stage) -> None:
    found = an_exceedance(opened, stage)
    for subpart in STANDARDS.values():
        due = found.due(subpart)
        assert due is not None
        assert (due - opened).days == found.window(subpart)


@pytest.mark.parametrize(("opened", "gap"), list(itertools.product(DAYS, GAPS)))
def test_a_wellhead_clock_never_moves_backwards(opened: dt.date, gap: int) -> None:
    day = opened + dt.timedelta(days=gap)
    found = an_exceedance(opened)
    expected = found.stage_for(XXX, day)
    later = found.stage_for(XXX, day + dt.timedelta(days=1))
    assert ORDER.index(later) >= ORDER.index(expected)


@pytest.mark.parametrize(("opened", "gap"), list(itertools.product(DAYS, GAPS)))
def test_the_stage_the_calendar_says_matches_the_windows(opened: dt.date, gap: int) -> None:
    day = opened + dt.timedelta(days=gap)
    found = an_exceedance(opened)
    stage = found.stage_for(XXX, day)
    if gap <= XXX.windows.correct:
        assert stage is Stage.CORRECT
    elif gap <= XXX.windows.action:
        assert stage is Stage.ACTION
    else:
        assert stage is Stage.EXPANSION


@pytest.mark.parametrize(("opened", "gap"), list(itertools.product(DAYS, GAPS)))
def test_a_record_is_late_exactly_the_day_after_its_window(opened: dt.date, gap: int) -> None:
    found = an_exceedance(opened)
    due = found.due(XXX)
    assert due is not None
    assert not found.is_late(XXX, due)
    assert found.is_late(XXX, due + dt.timedelta(days=1))
    del gap


@pytest.mark.parametrize("opened", DAYS)
def test_escalating_never_moves_the_day_it_was_opened(opened: dt.date) -> None:
    found = an_exceedance(opened)
    for _ in range(2):
        found = found.escalate()
        assert found.opened_on == opened


@pytest.mark.parametrize(("opened", "gap"), list(itertools.product(DAYS, GAPS)))
def test_a_closed_record_has_no_window_left_whenever_it_closed(opened: dt.date, gap: int) -> None:
    found = an_exceedance(opened).close(opened + dt.timedelta(days=gap))
    assert found.due(XXX) is None
    assert not found.is_late(XXX, opened + dt.timedelta(days=400))
    assert not found.behind(XXX, opened + dt.timedelta(days=400))


@pytest.mark.parametrize("subpart", list(STANDARDS.values()), ids=lambda s: s.code)
def test_the_three_standards_agree_about_the_wellhead_windows(subpart: object) -> None:
    found = an_exceedance(DAYS[0])
    assert found.due(subpart) == found.due(XXX)  # type: ignore[arg-type]
    assert WWW.windows == CF.windows


@pytest.mark.parametrize(("found_on", "gap"), list(itertools.product(DAYS, GAPS)))
def test_the_repair_window_is_always_counted_from_the_day_it_was_found(
    found_on: dt.date, gap: int
) -> None:
    hit = a_hit(found_on)
    due = hit.due(XXX)
    assert due is not None
    assert (due - found_on).days == XXX.surface_windows.repair
    del gap


@pytest.mark.parametrize(("found_on", "gap"), list(itertools.product(DAYS, GAPS)))
def test_the_remonitor_window_is_always_counted_from_the_repair(
    found_on: dt.date, gap: int
) -> None:
    repaired = found_on + dt.timedelta(days=gap)
    hit = a_hit(found_on).repair(repaired)
    due = hit.due(XXX)
    assert due is not None
    assert (due - repaired).days == XXX.surface_windows.remonitor


@pytest.mark.parametrize("gap", GAPS)
def test_a_later_repair_always_means_a_later_remonitor(gap: int) -> None:
    found_on = DAYS[0]
    early = a_hit(found_on).repair(found_on)
    late = a_hit(found_on).repair(found_on + dt.timedelta(days=gap))
    early_due = early.due(XXX)
    late_due = late.due(XXX)
    assert early_due is not None
    assert late_due is not None
    assert late_due >= early_due


@pytest.mark.parametrize("found_on", DAYS)
def test_the_expansion_window_always_goes_back_to_the_day_it_was_found(
    found_on: dt.date,
) -> None:
    hit = a_hit(found_on)
    for repaired, remonitored in ((3, 8), (9, 15)):
        hit = hit.repair(found_on + dt.timedelta(days=repaired))
        hit = hit.still_over(XXX, found_on + dt.timedelta(days=remonitored))
    assert hit.step is Step.EXPANSION
    due = hit.due(XXX)
    assert due is not None
    assert (due - found_on).days == XXX.surface_windows.expand


@pytest.mark.parametrize("found_on", DAYS)
def test_a_second_attempt_always_starts_the_repair_window_again(found_on: dt.date) -> None:
    hit = a_hit(found_on).repair(found_on + dt.timedelta(days=2))
    again = hit.still_over(XXX, found_on + dt.timedelta(days=6))
    assert again.step is Step.REPAIR
    assert again.repaired_on is None
    due = again.due(XXX)
    assert due is not None
    assert (due - found_on).days == XXX.surface_windows.repair


@pytest.mark.parametrize(("found_on", "gap"), list(itertools.product(DAYS, GAPS[:6])))
def test_a_cleared_spot_has_no_window_left(found_on: dt.date, gap: int) -> None:
    hit = a_hit(found_on).repair(found_on).clear(found_on + dt.timedelta(days=gap))
    assert hit.due(XXX) is None
    assert not hit.is_late(XXX, found_on + dt.timedelta(days=400))


def test_the_two_clocks_do_not_agree_and_that_is_the_point() -> None:
    day = dt.date(2025, 5, 13)
    wellhead = an_exceedance(day)
    spot = a_hit(day).repair(day + dt.timedelta(days=9))
    wellhead_due = wellhead.due(XXX)
    spot_due = spot.due(XXX)
    assert wellhead_due is not None
    assert spot_due is not None
    assert (wellhead_due - day).days == 5
    assert (spot_due - day).days == 19
