"""Writing notes, and finding the one somebody half remembers.

The desk does two things the store cannot. It works out what kind of thing a
label is about by asking the book, so a person can write a note against VW-041
without saying that VW-041 is a device. And it searches, which is the only
reason anybody writes notes down: a note nobody can find again is a note nobody
wrote.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.errors import UnknownError
from gemwalk.model.memo import About, Memo
from gemwalk.service.compliance import ComplianceDesk
from gemwalk.service.plant import PlantDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.service.surface import SurfaceDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.service.work import WorkDesk
from gemwalk.store.book import Book
from gemwalk.store.memos import MemoRepository


class MemoDesk:
    """The notes, and how to find one again."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.memos = MemoRepository(book)
        self.sites = SiteDesk(book)
        self.wellfield = WellfieldDesk(book)
        self.compliance = ComplianceDesk(book)
        self.surface = SurfaceDesk(book)
        self.plant = PlantDesk(book)
        self.work = WorkDesk(book)

    def kind_of(self, subject: str) -> tuple[About, str]:
        """What kind of thing a label is, and which site it belongs to.

        Asked of the book rather than worked out from the shape of the label,
        because a site that typed its old wells in off paper has labels this
        package would never have handed out.
        """
        found = self.wellfield.devices.find(subject)
        if found is not None:
            return About.DEVICE, found.site
        area = self.sites.areas.find(subject)
        if area is not None:
            return About.AREA, area.site
        record = self.compliance.exceedances.find(subject)
        if record is not None:
            return About.RECORD, record.site
        hit = self.surface.hits.find(subject)
        if hit is not None:
            return About.SPOT, hit.site
        run = self.compliance.monitoring.runs.find(subject)
        if run is not None:
            return About.RUN, run.site
        walk = self.surface.walks.find(subject)
        if walk is not None:
            return About.WALK, walk.site
        control = self.plant.controls.find(subject)
        if control is not None:
            return About.CONTROL, control.site
        order = self.work.orders.find(subject)
        if order is not None:
            return About.ORDER, order.site
        site = self.sites.sites.find(subject)
        if site is not None:
            return About.SITE, site.label
        raise UnknownError("anything", subject)

    def write(self, subject: str, at: dt.datetime, *, by_whom: str, body: str) -> Memo:
        """Put a note against whatever the label turns out to be."""
        about, site = self.kind_of(subject)
        with self.book.writing():
            return self.memos.add(
                Memo(
                    site=site,
                    about=about,
                    subject=subject,
                    at=at,
                    by_whom=by_whom,
                    body=body,
                )
            )

    def about(self, subject: str) -> list[Memo]:
        """Every note about one thing, oldest first."""
        return self.memos.about_subject(subject)

    def of_kind(self, site: str, about: About) -> list[Memo]:
        """Every note at one site about one kind of thing."""
        return self.memos.of_kind(site, about)

    def find(self, site: str, word: str) -> list[Memo]:
        """Every note at one site that says a word, oldest first."""
        return self.memos.saying(site, word)

    def recent(self, site: str, count: int = 10) -> list[Memo]:
        """The last few notes at a site, newest first."""
        return list(reversed(self.memos.of_site(site)))[:count]

    def counts(self, site: str) -> dict[str, int]:
        """How many notes there are about each kind of thing."""
        tally = {str(about): 0 for about in About}
        for memo in self.memos.of_site(site):
            tally[str(memo.about)] += 1
        return {kind: number for kind, number in tally.items() if number}


__all__ = ["MemoDesk"]
