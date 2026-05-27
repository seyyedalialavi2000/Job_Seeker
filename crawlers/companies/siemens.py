import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup as bs

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas import Job
from crawlers.base import BaseCrawler


class Siemens(BaseCrawler):
    """Crawler for Siemens job postings in Germany.

    Filters applied (via URL parameters):
      - Country: Germany
      - Field of work: Communications, Customer Services, Cybersecurity,
        Engineering, Experience Design, Finance, Human Resources,
        Information Technology, Internal Services, Marketing,
        People & Organization, Project Management, Quality Management,
        Research & Development
      - Experience Level: Recent College Graduate, Early Professional,
        Mid-level Professional, Experienced Professional
    """

    PAGE_SIZE = 6

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
        }
        self.url = (
            "https://jobs.siemens.com/en_US/externaljobs/SearchJobs/"
            "?42386=%5B812132%5D&42386_format=17546"
            "&42389=%5B102116%2C102130%2C39106405%2C102117%2C144468627"
            "%2C102119%2C102121%2C102122%2C102114%2C102132%2C62803293"
            "%2C102133%2C102126%2C102127%5D&42389_format=17549"
            "&42390=%5B102155%2C102156%2C102157%2C102158%5D&42390_format=17550"
            "&43471=%5B811689%5D&43471_format=17871"
            "&listFilterMode=1"
            "&folderRecordsPerPage={page_size}"
            "&folderOffset={offset}"
        )

    async def _make_request(self, offset=0):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=self.url.format(page_size=self.PAGE_SIZE, offset=offset),
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.text

    @staticmethod
    def _parse_job_card(article):
        """Extract job data from a single article--result element."""
        link = article.select_one(".article__header__text__title a.link")
        if not link:
            return None

        title = link.text.strip()
        url = link.get("href", "")

        job_id = ""
        location = ""

        job_id_span = article.select_one("span.list-item-jobId")
        if job_id_span:
            id_match = re.search(r"(\d+)", job_id_span.text)
            if id_match:
                job_id = id_match.group(1)

        loc_span = article.select_one("span.list-item-jobCity")
        if loc_span:
            location = loc_span.text.strip()

        return {
            "title": title,
            "url": url,
            "job_id": job_id,
            "location": location,
        }

    async def get_jobs(self):
        offset = 0
        while True:
            html = await self._make_request(offset)
            soup = bs(html, "html.parser")
            articles = soup.select(".article--result")
            if not articles:
                break

            for article in articles:
                data = self._parse_job_card(article)
                if data:
                    yield Job(
                        title=data["title"],
                        url=data["url"],
                        company="Siemens",
                        location=data["location"],
                        job_id=data["job_id"],
                    )

            if len(articles) < self.PAGE_SIZE:
                break
            offset += self.PAGE_SIZE


if __name__ == "__main__":
    import asyncio

    async def main():
        crawler = Siemens()
        count = 0
        async for job in crawler.get_jobs():
            count += 1
            print(
                f"{count:>3}. [{job.job_id}] {job.title}\n"
                f"     Location: {job.location}\n"
                f"     URL: {job.url}\n"
            )
        print(f"\n=== Total Siemens jobs: {count} ===")

    asyncio.run(main())
