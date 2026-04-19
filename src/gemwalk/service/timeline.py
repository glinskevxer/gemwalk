"""Everything that ever happened to one thing, in the order it happened.

The book keeps twelve kinds of record and each one is filed with its own kind.
That is right for every question except the one people actually ask, which is
"what happened to this well". Answering it means reading eight tables and
sorting the answers by date, and doing that by hand is how somebody ends up
believing a pump went in before the well flooded.

An event is deliberately thin: a day, what kind of thing it was, and one line
of words. Anything richer belongs on the record it came from, and the point of
the timeline is to say which record to go and look at.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.errors import UnknownError
from gemwalk.model.memo import About
from gemwalk.service.memos import MemoDesk
from gemwalk.store.book import Book


@dataclass(frozen=True)
class Event:
    """One thing that happened on one day."""

    on: dt.date
    kind: str
    subject: str
    said: str

    def __str__(self) -> str:
        return f"{self.on}  {self.kind:<12}  {self.said}"


def count_kinds(events: list[Event]) -> dict[str, int]:
    """How many events of each kind are in a list, the most first.

    It takes the events rather than a label so that a caller printing part of
    a story can tally what it printed. Tallying the whole story under a range
    that showed three lines of it is a footer that contradicts the page above
    it.
    """
    tally: dict[str, int] = {}
    for event in events:
        tally[event.kind] = tally.get(event.kind, 0) + 1
    return dict(sorted(tally.items(), key=lambda pair: (-pair[1], pair[0])))


class TimelineDesk:
    """Everything that ever happened to one thing, gathered up."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.memos = MemoDesk(book)

    def of_device(self, label: str) -> list[Event]:
        """Everything that ever happened to one device, oldest first."""
        found = self.memos.wellfield.devices.get(label)
        events: list[Event] = [
            Event(found.drilled_on, "drilled", label, f"{found.kind} into {found.area}")
        ]
        if found.connected_on is not None:
            events.append(
                Event(
                    found.connected_on,
                    "connected",
                    label,
                    f"onto {found.lateral or 'no lateral'}",
                )
            )
        if found.hov_approved is not None and found.hov_degrees is not None:
            events.append(
                Event(
                    found.hov_approved,
                    "approval",
                    label,
                    f"held to {found.hov_degrees:g} F from this day",
                )
            )
        if found.abandoned_on is not None:
            events.append(Event(found.abandoned_on, "abandoned", label, "out of service"))
        events.extend(self._readings(label))
        events.extend(self._records(label))
        events.extend(self._water(label))
        events.extend(self._rework(label))
        events.extend(self._orders(label))
        events.extend(self._notes(label))
        return sorted(events, key=lambda event: (event.on, event.kind, event.said))

    def _readings(self, label: str) -> list[Event]:
        events: list[Event] = []
        for reading in self.memos.compliance.monitoring.readings.of_device(label):
            events.append(
                Event(
                    reading.taken_on,
                    "read",
                    label,
                    f"{reading.methane_reading} methane, {reading.wellhead_temperature}, "
                    f"{reading.gauge}, {reading.gas_flow} on {reading.run}",
                )
            )
        return events

    def _records(self, label: str) -> list[Event]:
        events: list[Event] = []
        for record in self.memos.compliance.exceedances.of_device(label):
            events.append(
                Event(
                    record.opened_on,
                    "finding",
                    record.label,
                    f"{record.kind} at {record.value:g} against {record.limit_value:g}",
                )
            )
            if record.closed_on is not None:
                events.append(
                    Event(record.closed_on, "closed", record.label, f"{record.kind} back under")
                )
            for check in self.memos.compliance.rechecks.of_exceedance(record.label):
                verdict = "back under" if check.clear else "still over"
                events.append(
                    Event(
                        check.taken_on,
                        "recheck",
                        record.label,
                        f"{check.value:g}, {verdict}, at the {check.stage} stage",
                    )
                )
        return events

    def _water(self, label: str) -> list[Event]:
        device = self.memos.wellfield.devices.get(label)
        events: list[Event] = []
        for level in self.memos.compliance.monitoring.liquids.levels.of_device(label):
            share = level.submerged_share(device)
            events.append(
                Event(
                    level.taken_on,
                    "tape",
                    label,
                    f"{level.depth:g} ft to liquid, {share * 100:.0f}% of the screen under",
                )
            )
        return events

    def _rework(self, label: str) -> list[Event]:
        events: list[Event] = []
        for job in self.memos.wellfield.rework.of_device(label):
            events.append(Event(job.started_on, "work", job.label, f"{job.kind} started"))
            if job.finished_on is not None:
                said = f"{job.kind} finished"
                if job.raised_by:
                    said += f", {job.raised_by:g} ft taller"
                events.append(Event(job.finished_on, "work", job.label, said))
        return events

    def _orders(self, label: str) -> list[Event]:
        events: list[Event] = []
        for order in self.memos.work.history(label):
            events.append(
                Event(
                    order.raised_on,
                    "order",
                    order.label,
                    f"{order.job}, due {order.due_on}",
                )
            )
            if order.done_on is not None:
                events.append(Event(order.done_on, "order", order.label, f"{order.state}"))
        return events

    def _notes(self, label: str) -> list[Event]:
        return [
            Event(memo.at.date(), "note", label, f"{memo.by_whom}: {memo.first_line}")
            for memo in self.memos.about(label)
        ]

    def of_subject(self, subject: str) -> list[Event]:
        """Everything that happened to whatever the label turns out to be."""
        about, _ = self.memos.kind_of(subject)
        if about is About.DEVICE:
            return self.of_device(subject)
        raise UnknownError("timeline", f"{subject}, which is a {about}")

    def between(self, label: str, first: dt.date, last: dt.date) -> list[Event]:
        """Everything that happened to one device inside a range of days."""
        return [event for event in self.of_device(label) if first <= event.on <= last]

    def kinds(self, label: str) -> dict[str, int]:
        """How many events of each kind there are, most first."""
        return count_kinds(self.of_device(label))


__all__ = ["Event", "TimelineDesk", "count_kinds"]
