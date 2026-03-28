"""The package writes where it is told to and nowhere else.

Two things go wrong here and both of them are invisible until somebody runs the
package somewhere it does not own. A module that writes beside its own source
works perfectly out of a checkout and fails inside a wheel, a container image
or anything else installed read only. And a test suite that leaves files in the
repository looks clean on the machine that wrote them and dirty on every other.

So the suite watches both. It takes a listing of the package directory and the
checkout, does a full season of work, and takes the listing again.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from gemwalk.service.office import Office
from gemwalk.service.seed import seed
from gemwalk.tools.smoke import main as smoke
from gemwalk.tools.walker import package_root, repo_root

IGNORED = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".git",
    ".venv",
    "dist",
    "build",
}


def listing(root: Path) -> set[str]:
    """Every file under a directory, caches and build output left out."""
    found: set[str] = set()
    for path in root.rglob("*"):
        if any(part in IGNORED for part in path.parts):
            continue
        if path.is_file():
            found.add(str(path.relative_to(root)))
    return found


@pytest.fixture
def watched() -> Iterator[tuple[set[str], set[str]]]:
    """The package directory and the checkout, before and after."""
    before = (listing(package_root()), listing(repo_root()))
    yield before
    after = (listing(package_root()), listing(repo_root()))
    assert after[0] == before[0], "the package directory was written into"
    assert after[1] == before[1], "the checkout was written into"


def test_a_whole_season_writes_nothing_into_the_package(
    watched: tuple[set[str], set[str]],
) -> None:
    assert smoke(["--quiet"]) == 0


def test_seeding_a_book_writes_nothing_into_the_package(
    watched: tuple[set[str], set[str]], tmp_path: Path
) -> None:
    with Office.open(tmp_path / "seeded.sqlite3") as office:
        seed(office)
        assert office.counts()["reading"] > 0


def test_the_generated_documents_are_the_only_thing_written_to_the_checkout(
    tmp_path: Path,
) -> None:
    from gemwalk.tools import build_glossary, build_rules, check_migrations, schema_dump

    written = {
        schema_dump.TARGET,
        build_rules.TARGET,
        build_glossary.TARGET,
        check_migrations.LOCK,
    }
    have = listing(repo_root())
    assert written <= have


def test_the_package_directory_holds_only_source_and_the_marker() -> None:
    for name in listing(package_root()):
        assert name.endswith(".py") or name == "py.typed", name


def test_the_suite_runs_with_the_package_read_only(tmp_path: Path) -> None:
    """The one that catches a module writing beside its own source.

    It runs the smoke walk in a separate process with the whole package
    directory stripped of write permission, which is how it arrives inside a
    container image. The permissions go back afterwards whatever happens.
    """
    if os.geteuid() == 0:
        pytest.skip("root can write to a read only directory, so this proves nothing")
    root = package_root()
    modes = {path: path.stat().st_mode for path in root.rglob("*") if path.is_file()}
    modes[root] = root.stat().st_mode
    try:
        for path in modes:
            path.chmod(0o555 if path.is_dir() else 0o444)
        finished = subprocess.run(
            [sys.executable, "-m", "gemwalk.tools.smoke", "--quiet"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )
    finally:
        for path, mode in modes.items():
            path.chmod(mode)
    assert finished.returncode == 0, finished.stderr


def test_a_book_opens_by_a_relative_name_in_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with Office.open("here.sqlite3") as office:
        assert office.counts()["site"] == 0
    assert (tmp_path / "here.sqlite3").exists()
    assert not (package_root() / "here.sqlite3").exists()
