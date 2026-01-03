from dataclasses import dataclass
from typing import Type

from crawlers.base import BaseCrawler
from crawlers.companies import SiemensEnergy, Siemens, Fraunhofer


@dataclass
class CrawlerMetadata:
    """Metadata for registering a crawler with scheduling info."""
    name: str
    cls: Type[BaseCrawler]
    interval: int  # minutes


# Crawler Registry - Add new crawlers with their schedule here
CRAWLER_REGISTRY = [
    CrawlerMetadata("SiemensEnergy", SiemensEnergy, interval=1),
    CrawlerMetadata("Siemens", Siemens, interval=1),
    CrawlerMetadata("Fraunhofer", Fraunhofer, interval=1),
]
