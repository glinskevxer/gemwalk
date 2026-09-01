"""The ci workflow, read as a file rather than trusted to be right.

Nothing compiles a shell script inside a yaml file, so the one place a renamed
command can sit being green for months is the walk job. ``check_cli`` parses it
and looks every command up in the click tree. This suite holds the rest of the
file: that the jobs exist, that they install what they say, and that every tool
``check.sh`` runs is also a step in ci.
"""

from __future__ import annotations

import tomllib

import pytest

from gemwalk.cli.main import main as tree
from gemwalk.tools import check_cli
from gemwalk.tools.walker import repo_root

WORKFLOW = ".github/workflows/ci.yml"
JOBS = ("lint", "checks", "tests", "everything", "coverage", "installed", "package", "walk")


def workflow() -> str:
    return (repo_root() / WORKFLOW).read_text()


@pytest.mark.repo
def test_the_workflow_is_in_the_checkout() -> None:
    assert (repo_root() / WORKFLOW).exists()


@pytest.mark.repo
def test_every_job_this_package_needs_is_there() -> None:
    text = workflow()
    for job in JOBS:
        assert f"\n  {job}:\n" in text


@pytest.mark.repo
def test_the_tests_run_on_both_supported_pythons() -> None:
    text = workflow()
    assert '"3.12"' in text
    assert '"3.13"' in text


@pytest.mark.repo
def test_the_installs_are_held_to_the_constraints_file() -> None:
    for line in workflow().splitlines():
        if 'pip install -e ".[dev]"' in line:
            assert "-c constraints.txt" in line


@pytest.mark.repo
def test_the_walk_says_only_commands_the_tree_answers_to() -> None:
    assert check_cli.walk_faults() == []


@pytest.mark.repo
def test_the_walk_actually_says_something() -> None:
    spoken = check_cli.spoken_in_the_walk()
    assert len(spoken) > 100
    assert "store init" in spoken


@pytest.mark.repo
def test_the_walk_reaches_most_of_the_tree() -> None:
    """The walk is the only place the whole command line is run end to end.

    It does not have to touch every command, because some of them only make
    sense against a book in a state the walk does not build. It does have to
    touch most of them, or a command can be broken for a release without
    anything noticing.
    """
    spoken = {" ".join(said.split()[:2]) for said in check_cli.spoken_in_the_walk()}
    leaves = {
        path for path, command in check_cli.commands(tree) if not hasattr(command, "commands")
    }
    reached = leaves & spoken
    assert len(reached) / len(leaves) > 0.75


@pytest.mark.repo
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


@pytest.mark.repo
def test_the_coverage_job_holds_both_floors() -> None:
    text = workflow()
    assert "coverage_gate --floor" in text
    assert "--file-floor" in text


@pytest.mark.repo
def test_the_package_job_builds_and_installs_the_wheel() -> None:
    text = workflow()
    assert "python -m build" in text
    assert "pip install dist/*.whl" in text


def heads() -> list[str]:
    """The walk as command paths, with the arguments taken off."""
    return [" ".join(said.split()[:2]) for said in check_cli.spoken_in_the_walk()]


@pytest.mark.repo
def test_the_walk_calibrates_before_it_reads_anything() -> None:
    said = heads()
    assert said.index("meter calibrate") < said.index("run open")


@pytest.mark.repo
def test_the_walk_lays_the_pattern_before_it_walks_the_cover() -> None:
    said = heads()
    assert said.index("cover pattern") < said.index("cover walk")


@pytest.mark.repo
def test_the_walk_posts_the_run_before_it_reads_the_board() -> None:
    said = heads()
    assert said.index("run post") < said.index("record board")


@pytest.mark.repo
def test_the_walk_ends_by_checking_the_book_it_built() -> None:
    said = heads()
    for wanted in ("store review", "store verify", "store check"):
        assert wanted in said


@pytest.mark.repo
def test_the_walk_prints_every_report() -> None:
    said = set(heads())
    for wanted in (
        "report month",
        "report quarter",
        "report board",
        "report plant",
        "report story",
        "report due",
        "report rate",
    ):
        assert wanted in said


@pytest.mark.repo
def test_the_walk_takes_a_backup_of_what_it_built() -> None:
    assert "store backup" in heads()


@pytest.mark.repo
def test_the_default_run_leaves_the_repository_gates_out() -> None:
    """A plain pytest run is behaviour only, or a branch cannot add a file."""
    with (repo_root() / "pyproject.toml").open("rb") as handle:
        settings = tomllib.load(handle)["tool"]["pytest"]["ini_options"]
    assert settings["addopts"] == "-m 'not repo'"
    assert any(said.startswith("repo:") for said in settings["markers"])


@pytest.mark.repo
def test_the_gates_are_still_run_by_the_script_and_by_ci() -> None:
    """Deselected is not deleted: both lists still run them by name."""
    assert "-m repo" in (repo_root() / "check.sh").read_text()
    assert "-m repo" in workflow()


@pytest.mark.repo
def test_the_coverage_job_measures_the_gates_too() -> None:
    """An empty -m overrides the deselection, so the file floor still holds."""
    assert '-m "" --cov' in workflow()
