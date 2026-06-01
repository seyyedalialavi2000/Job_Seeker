from crawlers.base import BaseCrawler
from crawlers.companies import (
    Siemens, SiemensEnergy, Fraunhofer, Accenture, Amazon, Deloitte
)
from crawlers.registry import CrawlerMetadata, CRAWLER_REGISTRY
from crawlers.runner import run_crawler, register_crawler_tasks
