"""The things the field desk keeps records about.

Every model object is a frozen dataclass with no behaviour that needs the book.
Anything that has to look at more than one of them lives in a service.
"""

from gemwalk.model.landfill import Area, Cover, Site

__all__ = ["Area", "Cover", "Site"]
