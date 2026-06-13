import re
from datetime import datetime
from typing import Optional, List
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# Ensure project root is on sys.path when running this file directly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas import Job
from crawlers.base import BaseCrawler
from utils import get_logger

logger = get_logger(__name__)


class BMW(BaseCrawler):
    """Crawler for BMW Group job postings in Germany.

    Mirrors the filters visible on https://www.bmwgroup.jobs/de/de.html:
      - Country: Germany
      - Einstiegsart (entry level): Graduates, Experienced professionals,
        Young Investigator Programs
      - Tätigkeitsbereich (work area): Information Technology,
        Research / Development, Quality Management

    Data source: https://jobs.bmwgroup.com/search/ (SuccessFactors portal)
    which serves server-rendered HTML that is reliably scrapeable.
    The portal is paginated (25 results per page) and filtered to Germany
    via the ``locationsearch`` parameter.  Work-area and entry-level
    filtering is applied client-side on the job title & description
    because the portal does not expose those facets in the HTML.
    """

    BASE = "https://jobs.bmwgroup.com"
    SEARCH_URL = f"{BASE}/search/"
    PAGE_SIZE = 25
    COMPANY = "BMW Group"

    # --- title / description keywords that approximate the UI filters --------
    # Work-area keywords  (IT, Research & Development, Quality Management)
    AREA_KEYWORDS: list[re.Pattern] = [
        re.compile(r"\bIT\b"),
        re.compile(r"software", re.I),
        re.compile(r"data\s*(engineer|scien|analy)", re.I),
        re.compile(r"developer|entwickl", re.I),
        re.compile(r"cloud|devops|infrastructure|plattform", re.I),
        re.compile(r"cyber\s*security|informationssicherheit", re.I),
        re.compile(r"artificial intelligence|\bAI\b|\bKI\b|machine[\s-]?learn", re.I),
        re.compile(r"quant(um|en)", re.I),
        re.compile(r"digital", re.I),
        re.compile(r"frontend|backend|fullstack|full[\s-]?stack", re.I),
        re.compile(r"forschung|research", re.I),
        re.compile(r"entwicklung|development", re.I),
        re.compile(r"phd|doktorand|promotion", re.I),
        re.compile(r"qualit(y|ät)", re.I),
        re.compile(r"test[\s-]?(manager|engineer|automat)", re.I),
    ]

    # Entry-level keywords (Graduates, Experienced professionals, Young Investigator)
    LEVEL_KEYWORDS: list[re.Pattern] = [
        re.compile(r"graduate|absolvent", re.I),
        re.compile(r"experienced|berufserfahren|professional|senior|lead|expert|specialist|spezialist", re.I),
        re.compile(r"young investigator|nachwuchswissenschaftler", re.I),
        re.compile(r"phd|doktorand|promotion", re.I),
        re.compile(r"master.*thesis|masterarbeit", re.I),
        # Also keep generic engineer/scientist roles (imply graduates/experienced)
        re.compile(r"engineer|ingenieur|scientist|wissenschaftler", re.I),
    ]

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

    # --------------------------------------------------------------------- #
    #  network helpers                                                       #
    # --------------------------------------------------------------------- #
    async def _fetch_search_page(self, client: httpx.AsyncClient, start: int) -> str:
        """Fetch one page of search results from jobs.bmwgroup.com."""
        try:
            r = await client.get(
                self.SEARCH_URL,
                params={
                    "q": "",
                    "locationsearch": "Germany",
                    "searchby": "location",
                    "startrow": str(start),
                },
                headers=self.headers,
                timeout=30.0,
            )
            r.raise_for_status()
            return r.text
        except (httpx.HTTPError, httpx.TransportError) as exc:
            logger.error(f"Error fetching search page (start={start}): {exc}")
            return ""

    # --------------------------------------------------------------------- #
    #  parsing helpers                                                       #
    # --------------------------------------------------------------------- #
    @staticmethod
    def _parse_total(soup: BeautifulSoup) -> Optional[int]:
        """Extract total result count from pagination label."""
        bolds = soup.select("span.paginationLabel b")
        if len(bolds) >= 2:
            try:
                return int(bolds[1].text.strip().replace(",", ""))
            except ValueError:
                pass
        return None

    def _parse_rows(self, soup: BeautifulSoup) -> List[dict]:
        """Parse job rows from a search-results page into dicts."""
        jobs: list[dict] = []
        for row in soup.select("tr.data-row"):
            a = row.select_one("a.jobTitle-link")
            if not a:
                continue
            title = a.text.strip()
            href = a.get("href", "")
            url = href if href.startswith("http") else f"{self.BASE}{href}"

            loc_span = row.select_one("td.colLocation span.jobLocation")
            location = loc_span.text.strip() if loc_span else ""

            date_span = row.select_one("td.colDate span.jobDate")
            date_str = date_span.text.strip() if date_span else ""

            # Extract numeric job id from the URL (last path segment)
            job_id_match = re.search(r"/(\d{5,})/?$", href)
            job_id = job_id_match.group(1) if job_id_match else ""

            posted_date: Optional[datetime] = None
            if date_str:
                for fmt in ("%b %d, %Y", "%d.%m.%Y", "%B %d, %Y"):
                    try:
                        posted_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue

            jobs.append({
                "title": title,
                "url": url,
                "location": location,
                "job_id": job_id,
                "posted_date": posted_date,
            })
        return jobs

    # --------------------------------------------------------------------- #
    #  client-side filtering                                                 #
    # --------------------------------------------------------------------- #
    @classmethod
    def _matches_filters(cls, title: str) -> bool:
        """Return True if the title matches BOTH an area keyword AND a level keyword."""
        area_ok = any(p.search(title) for p in cls.AREA_KEYWORDS)
        level_ok = any(p.search(title) for p in cls.LEVEL_KEYWORDS)
        return area_ok and level_ok

    # --------------------------------------------------------------------- #
    #  public interface                                                      #
    # --------------------------------------------------------------------- #
    async def get_jobs(self):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            start = 0
            total: Optional[int] = None

            while True:
                html = await self._fetch_search_page(client, start)
                if not html:
                    break

                soup = BeautifulSoup(html, "html.parser")

                if total is None:
                    total = self._parse_total(soup)

                page_jobs = self._parse_rows(soup)
                if not page_jobs:
                    break

                for j in page_jobs:
                    if self._matches_filters(j["title"]):
                        yield Job(
                            title=j["title"],
                            url=j["url"],
                            company=self.COMPANY,
                            location=j["location"],
                            update_time=j["posted_date"],
                            job_id=j["job_id"],
                        )

                start += len(page_jobs)
                if total is not None and start >= total:
                    break
                if len(page_jobs) < self.PAGE_SIZE:
                    break


if __name__ == "__main__":
    import asyncio

    async def main():
        crawler = BMW()
        count = 0
        async for job in crawler.get_jobs():
            count += 1
            print(
                f"{count:>3}. [{job.job_id}] {job.title}\n"
                f"     Location: {job.location}  |  Posted: {job.update_time}\n"
                f"     URL: {job.url}\n"
            )
        print(f"\n=== Total filtered BMW jobs: {count} ===")

    asyncio.run(main())

