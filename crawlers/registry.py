from dataclasses import dataclass
from typing import Type


@dataclass
class CrawlerMetadata:
    """Metadata for registering a crawler with scheduling info."""
    name: str
    cls: Type
    interval: int  # minutes


# Import crawlers for registry
from crawlers.siemens_energy import SiemensEnergy
from crawlers.siemens import Siemens
from crawlers.fraunhofer import Fraunhofer


# Crawler Registry - Add new crawlers with their schedule here
CRAWLER_REGISTRY = [
    CrawlerMetadata("SiemensEnergy", SiemensEnergy, interval=1),
    CrawlerMetadata("Siemens", Siemens, interval=1),
    CrawlerMetadata("Fraunhofer", Fraunhofer, interval=1),
]
