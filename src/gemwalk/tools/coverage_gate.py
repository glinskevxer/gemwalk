"""Two floors on coverage, and the second one is the one that catches things.

A total floor is easy to clear and says almost nothing: a package that is
ninety eight percent covered can hold one module at forty. The per file floor
is the one that finds the module added by the last commit, whose refusal
branches nothing has exercised yet, and that is exactly the module nobody has
looked at.

It reads ``coverage.json``, which is written by ``pytest --cov
--cov-report=json``. It does not run the suite itself, because ci wants the
suite and the gate as separate steps so a red gate is not confused with a red
suite.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from gemwalk.tools.walker import repo_root

REPORT = "coverage.json"
FLOOR = 95.0
FILE_FLOOR = 80.0
WORST = 6


@dataclass(frozen=True)
class Measured:
    """One file and how much of it the suite reached."""

    path: str
    percent: float
    missing: int

    def __str__(self) -> str:
        return f"{self.path}  {self.percent:.2f}%  {self.missing} lines not reached"


def read(path: Path) -> tuple[float, list[Measured]]:
    """The total and every file, out of a coverage report."""
    loaded = json.loads(path.read_text())
    total = float(loaded["totals"]["percent_covered"])
    files = [
        Measured(
            path=name,
            percent=float(body["summary"]["percent_covered"]),
            missing=int(body["summary"]["missing_lines"]),
        )
        for name, body in sorted(loaded["files"].items())
    ]
    return total, files


def argument(args: list[str], name: str, fallback: float) -> float:
    """Read one numeric argument off the command line."""
    if name not in args:
        return fallback
    index = args.index(name)
    if index + 1 >= len(args):
        return fallback
    return float(args[index + 1])


def main(argv: list[str] | None = None) -> int:
    """Read the coverage report and hold both floors."""
    args = list(sys.argv[1:] if argv is None else argv)
    floor = argument(args, "--floor", FLOOR)
    file_floor = argument(args, "--file-floor", FILE_FLOOR)
    worst = int(argument(args, "--worst", float(WORST)))
    path = repo_root() / REPORT
    if not path.exists():
        print(f"coverage_gate: {REPORT} is not there, run pytest --cov --cov-report=json")
        return 1
    total, files = read(path)
    ranked = sorted(files, key=lambda f: (f.percent, f.path))
    print(f"coverage_gate: {total:.2f}% over {len(files)} files")
    for measured in ranked[:worst]:
        print(f"  {measured}")
    faults: list[str] = []
    if total < floor:
        faults.append(f"the total is {total:.2f}% against a floor of {floor:.2f}%")
    for measured in ranked:
        if measured.percent < file_floor:
            faults.append(
                f"{measured.path} is {measured.percent:.2f}% against a file floor of "
                f"{file_floor:.2f}%"
            )
    if not faults:
        print("coverage_gate: both floors held")
        return 0
    print(f"coverage_gate: {len(faults)} to fix")
    for fault in faults:
        print(f"  {fault}")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
