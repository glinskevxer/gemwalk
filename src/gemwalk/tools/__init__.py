"""Tools that check this repository against itself, and one that exercises it.

Nothing in here is imported by the package. They are run from ``check.sh`` and
again as separate ci steps, they take no arguments they cannot work out for
themselves, and each one exits non zero with a list of what it found.
"""

__all__: list[str] = []
