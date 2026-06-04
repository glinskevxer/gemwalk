"""The heading every report starts with, written once.

Five reports were each opening with the same four lines: fetch the site, fetch
the standard it is run under, and build a title out of the site's name and a
subtitle out of the citation and the permit number. Four of them agreed about
the wording and the fifth did not, which is the usual way a document set stops
looking like one document set.
"""

from __future__ import annotations

from gemwalk.report.frame import Report
from gemwalk.rules import Standard
from gemwalk.service.office import Office


def headed(office: Office, site: str, kind: str, period: str) -> tuple[Report, Standard]:
    """A report with the standard heading on it, and the standard it is under.

    The standard comes back with it because every report that wants a heading
    also wants the standard a line later, and looking it up twice means two
    chances to look it up differently.
    """
    landfill = office.sites.sites.get(site)
    subpart = office.sites.standard_of(site)
    report = Report(
        title=f"{landfill.name} {kind}",
        subtitle=f"{period} under {subpart.citation}, permit {landfill.permit}",
    )
    return report, subpart


__all__ = ["headed"]
