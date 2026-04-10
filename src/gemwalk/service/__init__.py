"""The desks. Everything that has to look at more than one record lives here."""

from gemwalk.service.compliance import ComplianceDesk
from gemwalk.service.instruments import InstrumentDesk
from gemwalk.service.intake import IntakeDesk
from gemwalk.service.liquids import LiquidsDesk
from gemwalk.service.memos import MemoDesk
from gemwalk.service.monitoring import MonitoringDesk
from gemwalk.service.office import Office
from gemwalk.service.piping import PipingDesk
from gemwalk.service.plant import PlantDesk
from gemwalk.service.sites import SiteDesk
from gemwalk.service.surface import SurfaceDesk
from gemwalk.service.wellfield import WellfieldDesk
from gemwalk.service.work import WorkDesk

__all__ = [
    "ComplianceDesk",
    "InstrumentDesk",
    "IntakeDesk",
    "LiquidsDesk",
    "MemoDesk",
    "MonitoringDesk",
    "Office",
    "PipingDesk",
    "PlantDesk",
    "SiteDesk",
    "SurfaceDesk",
    "WellfieldDesk",
    "WorkDesk",
]
