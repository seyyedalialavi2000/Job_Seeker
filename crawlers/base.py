from abc import ABC, abstractmethod
from typing import AsyncIterator

from schemas import Job


class BaseCrawler(ABC):
    """
    Abstract base class for all job crawlers.
    
    All crawlers must inherit from this class and implement the get_jobs() method.
    This provides a unified interface for crawling different job sources.
    """
    
    @abstractmethod
    async def get_jobs(self) -> AsyncIterator[Job]:
        """
        Asynchronously yields Job objects from the crawler source.
        
        Yields:
            Job: Individual job postings from the source.
        """
        pass
