import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas import Job
from crawlers.base import BaseCrawler


class Bosch(BaseCrawler):
    """Crawler for Bosch job postings in Germany.

    Filters applied (matching the user's portal selection):
      - Country: Germany
      - Apply as: Graduate
      - Working Hours: Full-time, Full-time and/or part-time,
        Full-time or job sharing

    Data source: FirstSpirit CaaS API at e-spirit.cloud,
    backing the https://jobs.bosch.com portal.
    """

    BASE_URL = (
        "https://bosch-i3-caas-api.e-spirit.cloud"
        "/bosch-i3-prod/bosch-de.jobs.content/_aggrs/get_jobs"
    )
    API_KEY = "19c815d0-6b97-4c7d-a966-e8cadb1f50ed"
    JOB_LINK_PREFIX = "https://jobs.bosch.com/en/job/"
    PAGE_SIZE = 20
    COMPANY = "Bosch"

    # Filter UUIDs from the portal URL
    POSITION_TYPES = [
        "19bfc7ac-fce5-4fdd-b466-bc0a04eb0d74",
        "eb495920-2471-4aea-a4b7-83cab76cab0c",
        "5349d7af-228f-4a66-ad1d-a2cc72904502",
        "20062440-08bf-4c49-aba3-c9bb674011ad",
        "9ac27bce-3ecf-440b-a04a-5ba763c0287d",
        "43f66aba-9e7a-44d1-936b-17a6912ecabf",
    ]
    WORKING_HOURS = [
        "60756b3e-dbab-4353-ac3a-0064d2bb27d8",
        "d3c8765d-627b-4922-a2af-2f6054539e56",
        "ff7c69f3-f89c-498c-9a0e-25f4dad301d4",
        "1e1c7860-6146-4f33-a931-74e4a2425c6c",
        "83e52946-7f19-474f-be7c-00b62efed2a3",
        "08e19577-5874-4d47-b055-a869c52eb5fc",
    ]

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Accept": "application/json",
        }
        self.avars = {
            "country": ["de"],
            "position_types": self.POSITION_TYPES,
            "working_hours": self.WORKING_HOURS,
            "sort": {"releasedDate": -1},
        }

    async def _fetch_page(self, client: httpx.AsyncClient, page: int) -> dict:
        params = {
            "page": page,
            "pagesize": self.PAGE_SIZE,
            "avars": json.dumps(self.avars),
        }
        r = await client.get(
            self.BASE_URL, headers=self.headers, params=params, timeout=30.0
        )
        r.raise_for_status()
        return r.json()["_embedded"]["rh:result"][0]

    @staticmethod
    def _parse_job(raw: dict, link_prefix: str) -> dict:
        """Extract job fields from a single API result item."""
        name = raw.get("name", "")
        ref = raw.get("refNumber", "")
        job_url_slug = raw.get("jobUrl", "")
        url = f"{link_prefix}{job_url_slug}" if job_url_slug else ""

        loc = raw.get("location", {})
        location = loc.get("fullLocation", "") or loc.get("city", "")

        released = raw.get("releasedDate", "")
        update_time: Optional[datetime] = None
        if released:
            try:
                update_time = datetime.fromisoformat(released.replace("Z", "+00:00"))
            except ValueError:
                pass

        working_loc = loc.get("workLocation", "")
        remote = "Remote" if loc.get("remote") else ("Hybrid" if loc.get("hybrid") else "Office")

        return {
            "title": name,
            "url": url,
            "job_id": ref,
            "location": location,
            "update_time": update_time,
            "remote_vs_office": f"{remote} - {working_loc}" if working_loc else remote,
        }

    async def get_jobs(self):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            page = 1
            while True:
                result = await self._fetch_page(client, page)
                jobs = result.get("data", [])
                meta = result.get("meta", [])
                total = meta[0]["count"] if meta else 0

                for raw in jobs:
                    parsed = self._parse_job(raw, self.JOB_LINK_PREFIX)
                    if parsed["url"]:
                        yield Job(
                            title=parsed["title"],
                            url=parsed["url"],
                            company=self.COMPANY,
                            location=parsed["location"],
                            update_time=parsed["update_time"],
                            job_id=parsed["job_id"],
                            remote_vs_office=parsed["remote_vs_office"],
                        )

                if not jobs or page * self.PAGE_SIZE >= total:
                    break
                page += 1


if __name__ == "__main__":
    import asyncio

    async def main():
        crawler = Bosch()
        count = 0
        async for job in crawler.get_jobs():
            count += 1
            print(
                f"{count:>3}. [{job.job_id}] {job.title}\n"
                f"     Location: {job.location}  |  Posted: {job.update_time}\n"
                f"     {job.remote_vs_office}\n"
                f"     URL: {job.url}\n"
            )
        print(f"\n=== Total Bosch jobs: {count} ===")

    asyncio.run(main())
