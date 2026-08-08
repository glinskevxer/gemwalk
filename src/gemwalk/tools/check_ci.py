"""The check script and the workflow agree, and both of them run every tool.

There are two lists of what has to pass: ``check.sh``, which is what a person
runs before pushing, and ``.github/workflows/ci.yml``, which is what decides
whether the push was any good. Nothing keeps them in step. A tool added to one
and not the other is a tool that is either never run by anybody or run only
after it is too late to be useful, and neither failure announces itself.

So this reads both files, works out which tools each of them runs, and compares
that with the tools that are actually in the package. All three have to match.
"""

from __future__ import annotations

import re
import sys

from gemwalk.tools.walker import modules, repo_root, report

SCRIPT = "check.sh"
WORKFLOW = ".github/workflows/ci.yml"
NAMED = re.compile(r"gemwalk\.tools\.(\w+)")
# The walker is machinery the other tools are built out of, and the smoke walk
# and the coverage gate are run by name rather than in the list of checks.
NOT_A_CHECK = frozenset({"walker", "smoke", "coverage_gate", "tools", "seed"})


def tools() -> set[str]:
    """Every tool module in the package that is meant to be run."""
    found: set[str] = set()
    for module in modules("tools"):
        stem = module.name.rsplit(".", 1)[-1]
        if stem.startswith("_") or stem in NOT_A_CHECK:
            continue
        found.add(stem)
    return found


def named_in(path: str) -> set[str]:
    """Every tool a file names, whatever it names it for."""
    target = repo_root() / path
    if not target.exists():
        return set()
    return set(NAMED.findall(target.read_text())) | _from_loop(target.read_text())


def _from_loop(text: str) -> set[str]:
    """The tools named in the check script's loop rather than by module path."""
    found: set[str] = set()
    inside = False
    for line in text.splitlines():
        if line.strip().startswith("for check in"):
            inside = True
        if inside:
            found.update(re.findall(r"\b(check_\w+|release_check)\b", line))
            if line.rstrip().endswith("; do"):
                inside = False
    return found - {"check"}


def faults() -> list[str]:
    """Everything the two lists and the package do not agree about."""
    have = tools()
    script = named_in(SCRIPT)
    workflow = named_in(WORKFLOW)
    found: list[str] = []
    for name in sorted(have - script):
        found.append(f"{name} is a tool and {SCRIPT} does not run it")
    for name in sorted(have - workflow):
        found.append(f"{name} is a tool and {WORKFLOW} does not run it")
    for name in sorted(script - have - NOT_A_CHECK):
        found.append(f"{SCRIPT} runs {name} and there is no such tool")
    for name in sorted(workflow - have - NOT_A_CHECK):
        found.append(f"{WORKFLOW} runs {name} and there is no such tool")
    return found


def main() -> int:
    """Check both lists run every tool the package has and nothing else."""
    if not named_in(SCRIPT):
        return report("check_ci", [f"{SCRIPT} runs no tools at all"])
    if not named_in(WORKFLOW):
        return report("check_ci", [f"{WORKFLOW} runs no tools at all"])
    return report("check_ci", faults())


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
