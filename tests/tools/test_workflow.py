"""The ci workflow, read as a file rather than trusted to be right.

Nothing compiles a shell script inside a yaml file, so the one place a renamed
command can sit being green for months is the walk job. ``check_cli`` parses it
and looks every command up in the click tree. This suite holds the rest of the
file: that the jobs exist, that they install what they say, and that every tool
``check.sh`` runs is also a step in ci.
"""

from __future__ import annotations

import re

from gemwalk.tools import check_cli
from gemwalk.tools.walker import repo_root

WORKFLOW = ".github/workflows/ci.yml"
JOBS = ("lint", "checks", "tests", "everything", "coverage", "installed", "package", "walk")


def workflow() -> str:
    return (repo_root() / WORKFLOW).read_text()


def check_script() -> str:
    return (repo_root() / "check.sh").read_text()


def test_the_workflow_is_in_the_checkout() -> None:
    assert (repo_root() / WORKFLOW).exists()


def test_every_job_this_package_needs_is_there() -> None:
    text = workflow()
    for job in JOBS:
        assert f"\n  {job}:\n" in text


def test_the_tests_run_on_both_supported_pythons() -> None:
    text = workflow()
    assert '"3.12"' in text
    assert '"3.13"' in text


def test_the_installs_are_held_to_the_constraints_file() -> None:
    for line in workflow().splitlines():
        if 'pip install -e ".[dev]"' in line:
            assert "-c constraints.txt" in line


def test_every_tool_the_check_script_runs_is_a_step_in_ci() -> None:
    text = workflow()
    for tool in re.findall(r"gemwalk\.tools\.(\w+)", check_script()):
        assert f"gemwalk.tools.{tool}" in text, f"{tool} is in check.sh and not in ci"


def test_every_tool_ci_runs_is_a_real_module() -> None:
    for tool in sorted(set(re.findall(r"gemwalk\.tools\.(\w+)", workflow()))):
        assert (repo_root() / "src" / "gemwalk" / "tools" / f"{tool}.py").exists()


def test_the_walk_says_only_commands_the_tree_answers_to() -> None:
    assert check_cli.walk_faults() == []


def test_the_walk_actually_says_something() -> None:
    spoken = check_cli.spoken_in_the_walk()
    assert len(spoken) > 40
    assert "store init" in spoken


def test_the_walk_touches_every_command_group() -> None:
    heads = {" ".join(command.split()[:1]) for command in check_cli.spoken_in_the_walk()}
    assert {
        "site",
        "well",
        "pipe",
        "run",
        "record",
        "work",
        "cover",
        "plant",
        "water",
        "report",
        "store",
        "about",
    } <= heads


def test_the_coverage_job_holds_both_floors() -> None:
    text = workflow()
    assert "coverage_gate --floor" in text
    assert "--file-floor" in text


def test_the_package_job_builds_and_installs_the_wheel() -> None:
    text = workflow()
    assert "python -m build" in text
    assert "pip install dist/*.whl" in text
