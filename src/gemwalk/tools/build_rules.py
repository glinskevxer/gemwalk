"""Write the regulation out of the table it is held in.

``docs/rules.md`` is generated from :mod:`gemwalk.rules`. It exists so that a
person asking "what does this package think the temperature limit is" reads the
answer rather than the code, and so that changing a number in one place changes
the document in the same commit. Run with ``--check`` it compares instead of
writing, which is what ci does.
"""

from __future__ import annotations

import sys

from gemwalk.rules import STANDARDS, Finding, Standard
from gemwalk.tools.walker import repo_root

TARGET = "docs/rules.md"
HEADER = """# The standards

Written by `gemwalk.tools.build_rules` out of `gemwalk/rules.py`. Do not edit:
change the table and run the tool.
"""


def _yes(value: bool) -> str:
    return "yes" if value else "no"


def _section(subpart: Standard) -> list[str]:
    limits = [
        (
            "wellhead temperature",
            f"{subpart.temperature_limit} ({subpart.temperature_limit.celsius:.0f} C)",
        ),
        ("wellhead oxygen", str(subpart.oxygen_limit)),
        (
            "wellhead nitrogen",
            "not available" if subpart.nitrogen_limit is None else str(subpart.nitrogen_limit),
        ),
        ("wellhead gauge pressure", f"under {subpart.pressure_limit}"),
        ("surface methane", f"{subpart.surface_limit} above background"),
        ("emission rate threshold", f"{subpart.nmoc_threshold_mg:g} Mg a year"),
        ("design capacity threshold", f"{subpart.design_capacity_mg:,.0f} Mg"),
        ("walkover pattern", f"{subpart.sem_spacing_metres:g} m serpentine"),
        (
            "walkover wind",
            f"average under {subpart.wind_average_mph:g} mph, "
            f"gusts under {subpart.wind_gust_mph:g} mph",
        ),
    ]
    windows = [
        ("correct a wellhead finding", f"{subpart.windows.correct} calendar days"),
        ("act on a wellhead finding", f"{subpart.windows.action} calendar days"),
        ("expand collection", f"{subpart.windows.expand} calendar days"),
        ("repair a surface spot", f"{subpart.surface_windows.repair} calendar days"),
        (
            "remonitor a repaired spot",
            f"{subpart.surface_windows.remonitor} calendar days from the repair",
        ),
        ("goes at the cover", f"{subpart.surface_windows.attempts}"),
        ("collection in a filling area", f"{subpart.active_install_years} years"),
        ("collection in a closed area", f"{subpart.closed_install_years} years"),
        ("system off for repair", f"{subpart.shutdown_days} days"),
        ("device off the run for a raise", f"{subpart.raising_days} days"),
    ]
    lines = [
        "",
        f"## Subpart {subpart.code}",
        "",
        subpart.name.capitalize() + ".",
        "",
        f"Cited as {subpart.citation}.",
        "",
        "| limit | value |",
        "| --- | --- |",
    ]
    lines.extend(f"| {name} | {value} |" for name, value in limits)
    lines.extend(["", "| window | length |", "| --- | --- |"])
    lines.extend(f"| {name} | {value} |" for name, value in windows)
    lines.extend(
        [
            "",
            f"Nitrogen may stand in for oxygen: {_yes(subpart.allows_nitrogen)}.",
            "",
            f"A higher operating temperature may be approved: "
            f"{_yes(subpart.allows_higher_temperature)}.",
            "",
            f"An alternative to the pressure standard may be approved: "
            f"{_yes(subpart.allows_higher_pressure)}.",
        ]
    )
    return lines


def build() -> str:
    """The whole document, as text."""
    lines = [HEADER.rstrip(), ""]
    lines.append("The kinds of finding a reading can produce: ")
    lines.append("")
    for finding in Finding:
        lines.append(f"- **{finding}** — one of the {finding.family} limits")
    for subpart in STANDARDS.values():
        lines.extend(_section(subpart))
    return "\n".join(lines) + "\n"


def written() -> str:
    """What the file on disk says, or an empty string if there is none."""
    path = repo_root() / TARGET
    return path.read_text() if path.exists() else ""


def update() -> int:
    """Write the document out."""
    path = repo_root() / TARGET
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build())
    print(f"build_rules: wrote {TARGET}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Write the document, or check the one on disk is current."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check" not in args:
        return update()
    if written() == build():
        print("build_rules: nothing to report")
        return 0
    print(f"build_rules: {TARGET} is out of date, run this tool with no arguments")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
