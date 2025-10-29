"""The three standards and where they part company."""

from __future__ import annotations

import pytest

from gemwalk.errors import DesignError, UnknownError
from gemwalk.rules import CF, STANDARDS, WWW, XXX, Finding, Windows, codes, standard
from gemwalk.units import Percent


def test_every_standard_answers_to_its_letter() -> None:
    assert codes() == ["WWW", "XXX", "Cf"]
    for code in codes():
        assert standard(code).code == code


def test_a_letter_nobody_writes_is_refused() -> None:
    with pytest.raises(UnknownError):
        standard("QQQ")


def test_all_three_agree_about_the_wellhead_temperature() -> None:
    limits = {s.temperature_limit.fahrenheit for s in STANDARDS.values()}
    assert limits == {131.0}
    assert WWW.temperature_limit.celsius == pytest.approx(55.0)


def test_only_the_older_standard_refuses_the_nitrogen_reading() -> None:
    assert not WWW.allows_nitrogen
    assert XXX.allows_nitrogen
    assert CF.allows_nitrogen
    assert XXX.nitrogen_limit == Percent(20.0)


def test_the_older_standard_wants_more_gas_before_it_applies() -> None:
    assert WWW.nmoc_threshold_mg == 50.0
    assert XXX.nmoc_threshold_mg == 34.0
    assert CF.nmoc_threshold_mg == 34.0


def test_only_the_older_standard_holds_the_pressure_line() -> None:
    assert not WWW.allows_higher_pressure
    assert XXX.allows_higher_pressure


def test_the_three_windows_widen_in_the_order_they_are_walked() -> None:
    for subpart in STANDARDS.values():
        assert subpart.windows.correct == 5
        assert subpart.windows.action == 15
        assert subpart.windows.expand == 120


def test_windows_that_do_not_widen_are_refused() -> None:
    with pytest.raises(DesignError, match="widen"):
        Windows(correct=15, action=5, expand=120)


def test_the_surface_limit_is_the_same_five_hundred_everywhere() -> None:
    for subpart in STANDARDS.values():
        assert subpart.surface_limit.value == 500.0
        assert subpart.surface_windows.repair == 10
        assert subpart.surface_windows.remonitor == 10


def test_a_finding_prints_as_the_word_the_report_uses() -> None:
    assert str(Finding.TEMPERATURE) == "temperature"
    assert {str(f) for f in Finding} == {
        "temperature",
        "oxygen",
        "nitrogen",
        "pressure",
        "surface",
    }


def test_the_install_deadline_is_shorter_once_an_area_is_closed() -> None:
    for subpart in STANDARDS.values():
        assert subpart.closed_install_years < subpart.active_install_years


def test_a_citation_is_carried_with_every_standard() -> None:
    for subpart in STANDARDS.values():
        assert subpart.citation.startswith("40 CFR 60 subpart ")
        assert subpart.citation.endswith(subpart.code)
