from dataclasses import dataclass
from typing import Type

from crawlers.base import BaseCrawler
from crawlers.companies import (
    Accenture, SiemensEnergy, Siemens, Fraunhofer, Amazon, Deloitte
)


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
    CrawlerMetadata("Accenture", Accenture, interval=1),
    CrawlerMetadata("Amazon", Amazon, interval=1),
    CrawlerMetadata("Deloitte", Deloitte, interval=1),
]
