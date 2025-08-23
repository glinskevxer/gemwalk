"""One runner for every command suite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner, Result

from gemwalk.cli.main import main


@dataclass
class Shell:
    """A book on disk and a runner pointed at it."""

    runner: CliRunner
    book: Path

    def run(self, *args: str) -> Result:
        """Run one command against this book."""
        return self.runner.invoke(main, ["--book", str(self.book), *args])

    def ok(self, *args: str) -> str:
        """Run one command, insist it worked, and hand back what it printed."""
        result = self.run(*args)
        if result.exit_code != 0:
            raise AssertionError(f"{' '.join(args)} failed: {result.output}{result.exception}")
        return result.output

    def fails(self, *args: str) -> str:
        """Run one command, insist it was refused, and hand back the message."""
        result = self.run(*args)
        if result.exit_code == 0:
            raise AssertionError(f"{' '.join(args)} was expected to fail: {result.output}")
        return result.output


def shell(tmp_path: Path) -> Shell:
    """A fresh book with the schema on it."""
    made = Shell(CliRunner(), tmp_path / "northridge.sqlite3")
    made.ok("store", "init")
    return made


def furnish(made: Shell) -> None:
    """A site with pipe in the ground and four wells on the run."""
    open_site(made)
    made.ok(
        "pipe",
        "header",
        "NORTHRIDGE",
        "north trunk",
        "--diameter",
        "18",
        "--material",
        "HDPE SDR17",
        "--length",
        "2140",
        "--on",
        "2019-09-03",
    )
    made.ok(
        "pipe",
        "lateral",
        "NORTHRIDGE",
        "HD-01",
        "--diameter",
        "8",
        "--material",
        "HDPE SDR17",
        "--length",
        "460",
        "--on",
        "2019-09-03",
    )
    for index in range(4):
        made.ok(
            "well",
            "drill",
            "NORTHRIDGE",
            "A-03" if index % 2 == 0 else "A-04",
            "--station",
            f"N {12 + index}+40",
            "--depth",
            "92",
            "--screen-top",
            "22",
            "--screen-bottom",
            "86",
            "--on",
            "2021-05-12",
        )
        made.ok("pipe", "tie", f"VW-00{index + 1}", "LT-001")
        made.ok("well", "connect", f"VW-00{index + 1}", "--on", "2021-06-02")


def open_site(made: Shell, label: str = "NORTHRIDGE", subpart: str = "XXX") -> None:
    """Put a site and two areas in through the command line."""
    made.ok(
        "site",
        "open",
        label,
        "Northridge Sanitary Landfill",
        "--subpart",
        subpart,
        "--permit",
        "MSW-1188-04",
        "--zone",
        "America/Chicago",
        "--capacity",
        "8400000",
        "--opened",
        "1998-06-01",
    )
    made.ok(
        "site",
        "area",
        "A-03",
        label,
        "phase 3 north slope",
        "--acres",
        "12.4",
        "--first-waste",
        "2019-04-15",
    )
    made.ok(
        "site",
        "area",
        "A-04",
        label,
        "phase 4 east",
        "--acres",
        "8.0",
        "--first-waste",
        "2020-06-01",
    )
