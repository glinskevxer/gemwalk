"""The one exception tree the package raises.

Everything below :class:`GemwalkError` is a refusal the field desk can print at
a person. Nothing in the package raises a bare ``ValueError`` or ``KeyError``
at its own caller: a refusal carries the thing it refused so the message can
name it, and :mod:`gemwalk.tools.check_errors` holds that line.
"""

from __future__ import annotations


class GemwalkError(Exception):
    """Base of every refusal the package raises at its caller."""


class UnitError(GemwalkError):
    """A quantity was written in a way the unit reader cannot take."""

    def __init__(self, text: str, wanted: str) -> None:
        super().__init__(f"cannot read {text!r} as {wanted}")
        self.text = text
        self.wanted = wanted


class RangeError(GemwalkError):
    """A quantity is outside the range its instrument can produce."""

    def __init__(self, what: str, value: float, low: float, high: float) -> None:
        super().__init__(f"{what} of {value:g} is outside {low:g} to {high:g}")
        self.what = what
        self.value = value
        self.low = low
        self.high = high


class UnknownError(GemwalkError):
    """A label was handed in that the book has never issued."""

    def __init__(self, kind: str, label: str) -> None:
        super().__init__(f"no {kind} labelled {label}")
        self.kind = kind
        self.label = label


class DuplicateError(GemwalkError):
    """A label was handed in that the book already holds."""

    def __init__(self, kind: str, label: str) -> None:
        super().__init__(f"{kind} {label} is already in the book")
        self.kind = kind
        self.label = label


class StateError(GemwalkError):
    """The thing exists but is not in a state that allows what was asked."""

    def __init__(self, what: str, state: str, wanted: str) -> None:
        super().__init__(f"{what} is {state}, and this needs it {wanted}")
        self.what = what
        self.state = state
        self.wanted = wanted


class OrderError(GemwalkError):
    """Two moments were handed in the wrong way round."""

    def __init__(self, what: str, earlier: str, later: str) -> None:
        super().__init__(f"{what}: {earlier} is not before {later}")
        self.what = what
        self.earlier = earlier
        self.later = later


class DesignError(GemwalkError):
    """Something the package itself is built out of is put together wrongly.

    This is not a refusal aimed at a person filling in a field sheet. It is a
    programming mistake caught at the point it is made, and the message is for
    whoever wrote the line.
    """

    def __init__(self, what: str, why: str) -> None:
        super().__init__(f"{what}: {why}")
        self.what = what
        self.why = why


class RuleError(GemwalkError):
    """The regulation does not allow what was asked."""

    def __init__(self, rule: str, why: str) -> None:
        super().__init__(f"{rule}: {why}")
        self.rule = rule
        self.why = why
