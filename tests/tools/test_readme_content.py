"""The readme says the things somebody has to know before using this.

A readme is not tested for prose. It is tested for the handful of facts that
somebody will otherwise get wrong, and every one of these is a fact the rest of
the suite holds somewhere else. If one of them changes in the code, this fails
too, which is the point: the document and the behaviour move together or the
build stops.
"""

from __future__ import annotations

import pytest

from gemwalk import __version__
from gemwalk.model.fault import ORDINARY_DAYS, URGENT_DAYS
from gemwalk.quality import AIR_RATIO
from gemwalk.rules import XXX
from gemwalk.tools.walker import modules, repo_root


def readme() -> str:
    return (repo_root() / "README.md").read_text()


@pytest.mark.repo
def test_the_readme_names_the_package() -> None:
    assert readme().startswith("# gemwalk")


@pytest.mark.repo
def test_it_says_the_wellhead_temperature_limit() -> None:
    assert f"{XXX.temperature_limit.fahrenheit:.0f} F" in readme()


@pytest.mark.repo
def test_it_says_the_three_wellhead_windows() -> None:
    text = readme()
    for days, word in (
        (XXX.windows.correct, "five days"),
        (XXX.windows.action, "fifteen"),
        (XXX.windows.expand, "hundred and twenty"),
    ):
        assert word in text
        assert days > 0


@pytest.mark.repo
def test_it_says_where_the_remonitor_window_is_counted_from() -> None:
    assert "remonitor window runs from the day the repair was made" in readme()


@pytest.mark.repo
def test_it_says_the_air_ratio_the_package_uses() -> None:
    assert f"{AIR_RATIO:.2f}" in readme()


@pytest.mark.repo
def test_it_says_the_two_cover_windows_exist() -> None:
    assert "one of two windows" in readme()
    assert URGENT_DAYS < ORDINARY_DAYS


@pytest.mark.repo
def test_it_says_how_long_a_well_may_be_off_the_run() -> None:
    assert "sixty days off the run" in readme()
    assert XXX.raising_days == 60


@pytest.mark.repo
def test_it_names_the_generated_documents() -> None:
    text = readme()
    for name in ("docs/schema.sql", "docs/rules.md", "docs/glossary.md", "docs/design.md"):
        assert name in text
    assert "docs/operating.md" in text


@pytest.mark.repo
def test_it_says_how_many_tools_there_are() -> None:
    tools = [
        module for module in modules("tools") if not module.name.endswith(("__init__", "walker"))
    ]
    assert "twenty four of these" in readme()
    assert len(tools) == 24


@pytest.mark.repo
def test_it_names_the_command_that_fills_a_book() -> None:
    assert "gemwalk store seed" in readme()


@pytest.mark.repo
def test_it_names_the_morning_page() -> None:
    assert "gemwalk report board" in readme()


@pytest.mark.repo
@pytest.mark.parametrize(
    "said",
    ["one sqlite file", "no server", "python -m pip install", "./check.sh"],
)
def test_it_says_what_somebody_has_to_do_to_use_it(said: str) -> None:
    assert said in readme()


@pytest.mark.repo
def test_the_changelog_and_the_readme_agree_about_the_version() -> None:
    assert f"## {__version__}" in (repo_root() / "CHANGELOG.md").read_text()
