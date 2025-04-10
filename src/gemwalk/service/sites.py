"""Opening a site, cutting it into areas, and closing both.

The desk is the only thing that reaches for two repositories at once, and it is
where the ordering rules between a site and its areas are held: an area belongs
to a site that exists, an area cannot have taken waste before its site opened,
and a site cannot be closed while one of its areas is still filling.
"""

from __future__ import annotations

import datetime as dt

from gemwalk.errors import RuleError
from gemwalk.model.landfill import Area, Cover, Site
from gemwalk.rules import Election, Standard, standard
from gemwalk.store.book import Book
from gemwalk.store.sites import AreaRepository, SiteRepository


class SiteDesk:
    """The records of the landfill itself and the ground inside its fence."""

    def __init__(self, book: Book) -> None:
        self.book = book
        self.sites = SiteRepository(book)
        self.areas = AreaRepository(book)

    def open_site(
        self,
        label: str,
        name: str,
        *,
        subpart: str,
        permit: str,
        zone: str,
        design_capacity: float,
        opened_on: dt.date,
    ) -> Site:
        """Put a landfill in the book, under the standard that reaches it."""
        standard(subpart)
        site = Site(
            label=label,
            name=name,
            standard=subpart,
            permit=permit,
            zone=zone,
            design_capacity=design_capacity,
            opened_on=opened_on,
        )
        with self.book.writing():
            return self.sites.add(site)

    def standard_of(self, label: str) -> Standard:
        """The federal standard the site is run against."""
        return standard(self.sites.get(label).standard)

    def zone_of(self, label: str) -> str:
        """The wall clock the site's operating records are kept on."""
        return self.sites.get(label).zone

    def elect(
        self,
        label: str,
        on: dt.date,
        *,
        nitrogen_alternative: bool = False,
        higher_pressure: bool = False,
    ) -> Site:
        """Record the choices a site has made under its standard."""
        site = self.sites.get(label)
        subpart = standard(site.standard)
        if nitrogen_alternative and not subpart.allows_nitrogen:
            raise RuleError(subpart.citation, "this standard has no nitrogen alternative")
        if higher_pressure and not subpart.allows_higher_pressure:
            raise RuleError(subpart.citation, "this standard has no pressure alternative")
        with self.book.writing():
            return self.sites.put(
                site.elect(
                    on,
                    nitrogen_alternative=nitrogen_alternative,
                    higher_pressure=higher_pressure,
                )
            )

    def election_of(self, label: str, on: dt.date | None = None) -> Election:
        """What the site had elected as of *on*, read through its standard."""
        site = self.sites.get(label)
        return site.election(standard(site.standard), on)

    def close_site(self, label: str, on: dt.date) -> Site:
        """Record a site as having taken its last load."""
        site = self.sites.get(label)
        still_filling = self.areas.filling(label)
        if still_filling:
            names = ", ".join(area.label for area in still_filling)
            raise RuleError("site", f"{names} still taking waste")
        with self.book.writing():
            return self.sites.put(site.close(on))

    def add_area(
        self,
        label: str,
        site: str,
        name: str,
        *,
        acres: float,
        first_waste: dt.date,
    ) -> Area:
        """Cut a new filling area into a site that exists."""
        parent = self.sites.get(site)
        if first_waste < parent.opened_on:
            raise RuleError("area", f"{parent.label} did not open until {parent.opened_on}")
        area = Area(label=label, site=site, name=name, acres=acres, first_waste=first_waste)
        with self.book.writing():
            return self.areas.add(area)

    def stop_filling(self, label: str, on: dt.date) -> Area:
        """Record an area as having taken its last load."""
        area = self.areas.get(label)
        with self.book.writing():
            return self.areas.put(area.stop_filling(on))

    def close_area(self, label: str, on: dt.date, cover: Cover = Cover.FINAL) -> Area:
        """Record final cover on an area and shut it."""
        area = self.areas.get(label)
        with self.book.writing():
            return self.areas.put(area.close(on, cover))

    def areas_of(self, site: str) -> list[Area]:
        """Every area of a site, in label order."""
        self.sites.get(site)
        return self.areas.of_site(site)

    def install_due(self, area: str) -> dt.date:
        """The last day collection has to be in the ground in this area."""
        found = self.areas.get(area)
        return found.install_due(self.standard_of(found.site))

    def overdue_areas(self, site: str, on: dt.date) -> list[Area]:
        """Every area whose collection deadline has already gone by."""
        subpart = self.standard_of(site)
        return [a for a in self.areas.of_site(site) if a.install_due(subpart) < on]


__all__ = ["SiteDesk"]
