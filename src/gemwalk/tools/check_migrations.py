"""A migration that has shipped is never edited again.

Every book that already exists has run the migrations it has run. Editing one
of them changes what a fresh book gets and leaves every existing book on the
old shape, and the two look identical from the outside: the version number is
the same, the log says the same name, and the tables are different.

So each migration's script is hashed and the hashes are written to
``migrations.lock``. Changing a script changes its hash and this check fails,
which is the point. Adding a migration adds a line, and running the tool with
``--update`` writes the new file.

The check also insists the numbers run one, two, three with no gaps, that no
number is used twice, and that every name is written once, because two
migrations called the same thing is how a merge quietly loses one.
"""

from __future__ import annotations

import hashlib
import sys

from gemwalk.store.migrations import MIGRATIONS, Migration
from gemwalk.tools.walker import repo_root, report

LOCK = "migrations.lock"
HEADER = "# Each line is a migration and the hash of the script it shipped with."


def digest(migration: Migration) -> str:
    """The hash of one migration's script."""
    return hashlib.sha256(migration.script.encode()).hexdigest()[:16]


def written() -> list[str]:
    """The lock file as it stands, one line a migration."""
    return [
        f"{migration.number:03d}  {digest(migration)}  {migration.name}" for migration in MIGRATIONS
    ]


def stored() -> list[str]:
    """The lines the lock file on disk holds, comments dropped."""
    path = repo_root() / LOCK
    if not path.exists():
        return []
    return [
        line.rstrip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def order_faults() -> list[str]:
    """Everything wrong with the numbering or the names."""
    found: list[str] = []
    numbers = [m.number for m in MIGRATIONS]
    if numbers != sorted(numbers):
        found.append("the migrations are not in number order")
    if len(set(numbers)) != len(numbers):
        found.append("two migrations share a number")
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        found.append(f"the numbers do not run one to {len(numbers)}")
    names = [m.name for m in MIGRATIONS]
    if len(set(names)) != len(names):
        found.append("two migrations share a name")
    return found


def lock_faults() -> list[str]:
    """Every migration whose script no longer matches what it shipped with."""
    have = stored()
    want = written()
    if not have:
        return [f"{LOCK} is missing, run this tool with --update"]
    found: list[str] = []
    for index, line in enumerate(want):
        if index >= len(have):
            found.append(f"{line} is not in {LOCK}, run this tool with --update")
        elif have[index] != line:
            found.append(f"{LOCK} says {have[index]!r} and the package says {line!r}")
    for line in have[len(want) :]:
        found.append(f"{LOCK} holds {line!r} and the package has no such migration")
    return found


def update() -> int:
    """Write the lock file from the migrations as they are now."""
    path = repo_root() / LOCK
    path.write_text("\n".join([HEADER, *written()]) + "\n")
    print(f"check_migrations: wrote {len(MIGRATIONS)} lines to {LOCK}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Check the numbering and the lock file, or write the lock file."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--update" in args:
        return update()
    return report("check_migrations", order_faults() + lock_faults())


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
