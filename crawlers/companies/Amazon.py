import httpx
import asyncio
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from schemas import Job
from crawlers.base import BaseCrawler


class Amazon(BaseCrawler):
    """Crawler for Amazon job postings."""

    def __init__(self):
        self.base_url = (
            "https://www.amazon.jobs/en/search.json?category%5B%5D=operations-it-support-engineering&"
            "schedule_type_id%5B%5D=Full-Time&radius=24km&facets%5B%5D=normalized_country_code&"
            "facets%5B%5D=normalized_state_name&facets%5B%5D=normalized_city_name&facets%5B%5D=location&"
            "facets%5B%5D=business_category&facets%5B%5D=category&facets%5B%5D=schedule_type_id&"
            "facets%5B%5D=employee_class&facets%5B%5D=normalized_location&facets%5B%5D=job_function_id&"
            "facets%5B%5D=is_manager&facets%5B%5D=is_intern&offset=0&result_limit=10&sort=relevant&"
            "latitude=&longitude=&loc_group_id=&loc_query=Germany&base_query=&city=&country=DEU&"
            "region=&county=&query_options=&"
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0",
        }

    def _build_url(self, offset: int, result_limit: int) -> str:
        parts = urlsplit(self.base_url)
        q = parse_qs(parts.query, keep_blank_values=True)
        q["offset"] = [str(offset)]
        q["result_limit"] = [str(result_limit)]
        new_query = urlencode(q, doseq=True)
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)
        )

    async def _make_request(self, offset=0, result_limit=50):
        page_url = self._build_url(offset=offset, result_limit=result_limit)
        async with httpx.AsyncClient() as client:
            r = await client.get(page_url, headers=self.headers, timeout=30.0)
            r.raise_for_status()
            return r.json()

    def _parse_job_url(self, job: dict) -> str:
        path = job.get("job_path") or job.get("url_next_step") or job.get("url")
        if not path:
            return ""
        if isinstance(path, str) and path.startswith("http"):
            return path
        if isinstance(path, str) and path.startswith("/"):
            return f"https://www.amazon.jobs{path}"
        return str(path)

    def _parse_date(self, date_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%B %d, %Y")
        except (ValueError, TypeError):
            return None

    async def get_jobs(self):
        offset = 0
        page_size = 50

        while True:
            data = await self._make_request(offset=offset, result_limit=page_size)
            jobs_data = data.get("jobs") or data.get("results") or []
            total = data.get("hits")

            if not jobs_data:
                break

            for job_dict in jobs_data:
                yield Job(
                    title=job_dict.get("title") or job_dict.get("job_title") or "",
                    url=self._parse_job_url(job_dict),
                    company="Amazon",
                    location=job_dict.get("location") or job_dict.get("normalized_location") or "",
                    create_time=self._parse_date(job_dict.get("posted_date")),
                    job_id=str(job_dict.get("id_icims") or job_dict.get("id") or ""),
                    remote_vs_office=job_dict.get("job_schedule_type") or None
                )

            offset += len(jobs_data)
            if total is not None and offset >= total:
                break
            if len(jobs_data) < page_size:
                break


if __name__ == "__main__":
    async def main():
        crawler = Amazon()
        async for job in crawler.get_jobs():
            print(f"{job.job_id}: {job.title} at {job.location} | Posted: {job.create_time}")

    asyncio.run(main())
