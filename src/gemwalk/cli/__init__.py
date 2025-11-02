"""The command line, which is the only way anybody actually uses this.

Nothing is re-exported here. ``gemwalk.cli.main`` is a module and pulling the
function of the same name up into the package would shadow it, so anything that
wants either says which one it means.
"""

__all__: list[str] = []
