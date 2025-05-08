"""Turning readings into clocks, and walking the clocks that are already open.

Posting a run is the one place a reading becomes a compliance record, and it
does three things at once.

A reading over a limit with nothing open on that limit opens an exceedance. A
reading over a limit with something already open is a recheck that came back
still over: it is written down, the clock is not restarted, and the record is
moved to whatever stage the calendar has reached. A reading under a limit with
something open on it is a recheck that came back clear, and it closes the
record where it stands.

Matching is done on the family and not the kind, because oxygen and nitrogen
are the same limit read two ways. A site that elects the nitrogen alternative
in the middle of an open oxygen clock closes that clock with its next clean
nitrogen reading, which is what a person would expect and what matching on the
kind would not do.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from gemwalk.assess import Assessment, Judgement
from gemwalk.errors import RuleError, StateError
from gemwalk.ids import Labels
from gemwalk.model.exceedance import Exceedance, Recheck, Stage
from gemwalk.rules import Finding
from gemwalk.service.monitoring import MonitoringDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.store.book import Book
from gemwalk.store.exceedances import ExceedanceRepository, RecheckRepository
from gemwalk.store.readings import ReadingRepository


@dataclass
class Posting:
    """What posting a run did to the compliance records."""

    run: str
    opened: list[str] = field(default_factory=list)
    closed: list[str] = field(default_factory=list)
    continued: list[str] = field(default_factory=list)
    escalated: list[str] = field(default_factory=list)

    @property
    def touched(self) -> int:
        """How many records the run moved in any way."""
        return len(self.opened) + len(self.closed) + len(self.continued)


@dataclass(frozen=True)
class Standing:
    """One open exceedance and where its clock has got to."""

    exceedance: Exceedance
    due: dt.date
    days_left: int
    late: bool
    expected: Stage


class ComplianceDesk:
    """The exceedance clocks, opened and walked off the monitoring runs."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.exceedances = ExceedanceRepository(book)
        self.rechecks = RecheckRepository(book)
        self.readings = ReadingRepository(book)
        self.monitoring = MonitoringDesk(book)
        self.sites = SiteDesk(book)
        self.labels = Labels(book)

    def post_run(self, run: str) -> Posting:
        """Read every wellhead on a run into the compliance records."""
        pass_ = self.monitoring.runs.get(run)
        posting = Posting(run=run)
        with self.book.writing():
            for assessment in self.monitoring.assessments(run):
                self._post_one(pass_.site, run, assessment, posting)
        return posting

    def _post_one(self, site: str, run: str, assessment: Assessment, posting: Posting) -> None:
        reading = self.readings.id_on_run(run, assessment.device)
        for judgement in assessment.judgements:
            standing = self.exceedances.open_of_family(assessment.device, judgement.finding)
            if judgement.over:
                if standing is None:
                    posting.opened.append(self._open(site, assessment, judgement, reading).label)
                else:
                    self._still_over(standing, assessment, judgement, reading, posting)
            elif standing is not None:
                self._clear(standing, assessment, judgement, reading, posting)

    def _open(
        self,
        site: str,
        assessment: Assessment,
        judgement: Judgement,
        reading: int,
    ) -> Exceedance:
        found = Exceedance(
            label=self.labels.next("finding", assessment.taken_on),
            site=site,
            device=assessment.device,
            kind=judgement.finding,
            opened_on=assessment.taken_on,
            reading=reading,
            value=judgement.value,
            limit_value=judgement.limit,
        )
        return self.exceedances.add(found)

    def _still_over(
        self,
        standing: Exceedance,
        assessment: Assessment,
        judgement: Judgement,
        reading: int,
        posting: Posting,
    ) -> None:
        self.rechecks.add(
            Recheck(
                exceedance=standing.label,
                taken_on=assessment.taken_on,
                reading=reading,
                value=judgement.value,
                clear=False,
                stage=standing.stage,
            )
        )
        posting.continued.append(standing.label)
        moved = self._catch_up(standing, assessment.taken_on)
        if moved.stage is not standing.stage:
            posting.escalated.append(standing.label)

    def _clear(
        self,
        standing: Exceedance,
        assessment: Assessment,
        judgement: Judgement,
        reading: int,
        posting: Posting,
    ) -> None:
        self.rechecks.add(
            Recheck(
                exceedance=standing.label,
                taken_on=assessment.taken_on,
                reading=reading,
                value=judgement.value,
                clear=True,
                stage=standing.stage,
            )
        )
        self.exceedances.put(standing.close(assessment.taken_on))
        posting.closed.append(standing.label)

    def _catch_up(self, standing: Exceedance, on: dt.date) -> Exceedance:
        subpart = self.sites.standard_of(standing.site)
        moved = standing
        while moved.behind(subpart, on):
            moved = moved.escalate()
        if moved.stage is not standing.stage:
            self.exceedances.put(moved)
        return moved

    def recheck(
        self,
        label: str,
        on: dt.date,
        value: float,
        *,
        clear: bool,
        note: str = "",
    ) -> Exceedance:
        """Record a field visit against an open exceedance, off a run."""
        standing = self.exceedances.get(label)
        if not standing.is_open:
            raise StateError(label, "closed", "open")
        if on < standing.opened_on:
            raise RuleError("recheck", f"{label} was opened on {standing.opened_on}")
        with self.book.writing():
            self.rechecks.add(
                Recheck(
                    exceedance=label,
                    taken_on=on,
                    value=value,
                    clear=clear,
                    stage=standing.stage,
                    note=note,
                )
            )
            if clear:
                return self.exceedances.put(standing.close(on, note))
            return self._catch_up(standing, on)

    def catch_up(self, site: str, on: dt.date) -> list[str]:
        """Move every open record at a site to the stage the calendar reached."""
        moved: list[str] = []
        with self.book.writing():
            for standing in self.exceedances.open_at(site):
                after = self._catch_up(standing, on)
                if after.stage is not standing.stage:
                    moved.append(standing.label)
        return moved

    def board(self, site: str, on: dt.date) -> list[Standing]:
        """Every open exceedance at a site, the least time left first."""
        subpart = self.sites.standard_of(site)
        standings: list[Standing] = []
        for found in self.exceedances.open_at(site):
            due = found.due(subpart)
            if due is None:
                continue
            standings.append(
                Standing(
                    exceedance=found,
                    due=due,
                    days_left=(due - on).days,
                    late=found.is_late(subpart, on),
                    expected=found.stage_for(subpart, on),
                )
            )
        return sorted(standings, key=lambda s: (s.days_left, s.exceedance.label))

    def overdue(self, site: str, on: dt.date) -> list[Standing]:
        """Every open exceedance whose current window has already run out."""
        return [standing for standing in self.board(site, on) if standing.late]

    def open_kinds(self, site: str) -> dict[str, int]:
        """How many open records there are of each kind, in report order."""
        tally = {str(kind): 0 for kind in Finding}
        for found in self.exceedances.open_at(site):
            tally[str(found.kind)] += 1
        return tally


__all__ = ["ComplianceDesk", "Posting", "Standing"]
