"""Raising work orders, handing them out and closing them off.

An order raised off a compliance record takes that record's own deadline rather
than a fresh window, so a wellhead found hot on the eighth gets an order due on
the thirteenth whether the order was written on the eighth or the eleventh.
Losing that is the classic way a site works every ticket on time and still
misses the regulation.

Closing an order does not close the record it came from. The record is closed
by a reading that comes back under the limit, and a valve that was turned is
not a reading.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from gemwalk.errors import OrderError, RuleError
from gemwalk.ids import Labels
from gemwalk.model.work import Job, Standing, WorkOrder
from gemwalk.service.compliance import ComplianceDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.service.surface import SurfaceDesk
from gemwalk.store.book import Book
from gemwalk.store.work import WorkOrderRepository


@dataclass(frozen=True)
class Ticket:
    """One open order and where its date has got to."""

    order: WorkOrder
    days_left: int
    late: bool


class WorkDesk:
    """The jobs the field crew is handed, and where they came from."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.orders = WorkOrderRepository(book)
        self.compliance = ComplianceDesk(book)
        self.surface = SurfaceDesk(book)
        self.sites = SiteDesk(book)
        self.labels = Labels(book)

    def raise_order(
        self,
        site: str,
        job: Job,
        target: str,
        *,
        on: dt.date,
        due: dt.date,
        because: str | None = None,
        note: str = "",
        allow_past: bool = False,
    ) -> WorkOrder:
        """Write a job the desk decided on, with the date the desk chose.

        A date before the day the order is written is refused unless the caller
        says otherwise, because a person typing both dates has almost certainly
        got one of them wrong. An order raised off a record is the exception:
        there the date is the record's and may already have gone by.
        """
        self.sites.sites.get(site)
        if due < on and not allow_past:
            raise OrderError("work order", str(on), str(due))
        with self.book.writing():
            order = WorkOrder(
                label=self.labels.next("order", on),
                site=site,
                job=job,
                target=target,
                raised_on=on,
                due_on=due,
                because=because,
                note=note,
            )
            return self.orders.add(order)

    def raise_for_exceedance(self, label: str, job: Job, on: dt.date, note: str = "") -> WorkOrder:
        """Write a job off an open exceedance, on that record's own deadline."""
        record = self.compliance.exceedances.get(label)
        if not record.is_open:
            raise RuleError("work order", f"{label} is closed")
        subpart = self.sites.standard_of(record.site)
        due = record.due(subpart)
        if due is None:
            raise RuleError("work order", f"{label} has no window left")
        return self.raise_order(
            record.site,
            job,
            record.device,
            on=on,
            due=due,
            because=label,
            note=note,
            allow_past=True,
        )

    def raise_for_hit(self, label: str, job: Job, on: dt.date, note: str = "") -> WorkOrder:
        """Write a job off an open surface hit, on that spot's own deadline."""
        hit = self.surface.hits.get(label)
        if not hit.is_open:
            raise RuleError("work order", f"{label} is closed")
        subpart = self.sites.standard_of(hit.site)
        due = hit.due(subpart)
        if due is None:
            raise RuleError("work order", f"{label} has no window left")
        return self.raise_order(
            hit.site,
            job,
            hit.station,
            on=on,
            due=due,
            because=label,
            note=note,
            allow_past=True,
        )

    def assign(self, label: str, crew: str, on: dt.date) -> WorkOrder:
        """Hand an order to a crew."""
        order = self.orders.get(label)
        with self.book.writing():
            return self.orders.put(order.assign(crew, on))

    def finish(self, label: str, on: dt.date, note: str = "") -> WorkOrder:
        """Record an order as done."""
        order = self.orders.get(label)
        with self.book.writing():
            return self.orders.put(order.finish(on, note))

    def cancel(self, label: str, on: dt.date, why: str) -> WorkOrder:
        """Call an order off, with a reason."""
        order = self.orders.get(label)
        with self.book.writing():
            return self.orders.put(order.cancel(on, why))

    def board(self, site: str, on: dt.date) -> list[Ticket]:
        """Every open order at a site, the least time left first."""
        tickets: list[Ticket] = []
        for order in self.orders.open_at(site):
            left = order.days_left(on)
            if left is None:
                continue
            tickets.append(Ticket(order=order, days_left=left, late=order.is_late(on)))
        return sorted(tickets, key=lambda t: (t.days_left, t.order.label))

    def overdue(self, site: str, on: dt.date) -> list[Ticket]:
        """Every open order that has gone past its date."""
        return [ticket for ticket in self.board(site, on) if ticket.late]

    def unhandled(self, site: str, on: dt.date) -> list[str]:
        """Every open compliance record at a site with no order against it.

        A record with nobody sent to it is the thing this whole desk exists to
        stop, so it is worth being able to ask for directly.
        """
        raised = {
            order.because
            for order in self.orders.between_days(site, "0001-01-01", on.isoformat())
            if order.because is not None
        }
        waiting = [e.label for e in self.compliance.exceedances.open_at(site)]
        waiting += [h.label for h in self.surface.hits.open_at(site)]
        return sorted(label for label in waiting if label not in raised)

    def crew_load(self, site: str, on: dt.date) -> dict[str, int]:
        """How many open orders each crew is carrying, busiest first."""
        tally: dict[str, int] = {}
        for order in self.orders.in_state(site, Standing.ASSIGNED):
            if order.is_open and order.raised_on <= on:
                tally[order.crew] = tally.get(order.crew, 0) + 1
        return dict(sorted(tally.items(), key=lambda pair: (-pair[1], pair[0])))

    def history(self, target: str) -> list[WorkOrder]:
        """Every order ever raised against one place, oldest first."""
        return sorted(self.orders.of_target(target), key=lambda o: (o.raised_on, o.label))

    def finished_late(self, site: str, first: dt.date, last: dt.date) -> list[WorkOrder]:
        """Every order finished after its date inside a range."""
        window = self.orders.between_days(site, first.isoformat(), last.isoformat())
        return [order for order in window if order.was_late()]


__all__ = ["Ticket", "WorkDesk"]
