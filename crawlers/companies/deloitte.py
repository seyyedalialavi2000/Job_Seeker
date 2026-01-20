import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from schemas import Job
from crawlers.base import BaseCrawler


class Deloitte(BaseCrawler):
    """Crawler for Deloitte job postings."""

    def __init__(self):
        self.base_url = "https://job.deloitte.com/ai-data-analytics-jobs-_pr1"
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Encoding": "gzip, deflate",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    def _build_url(self, page: int) -> str:
        parts = urlsplit(self.base_url)
        q = parse_qs(parts.query, keep_blank_values=True)
        if page <= 1:
            q.pop("page", None)
        else:
            q["page"] = [str(page)]
        new_query = urlencode(q, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    async def _fetch_html(self, url: str) -> str:
        r = await self.client.get(url)
        r.raise_for_status()
        return r.text

    def _parse_listing_page(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for a in soup.select('a[href^="/job-"]'):
            href = a.get("href")
            title = a.get_text(" ", strip=True)
            if not href or not title:
                continue
            link = urljoin("https://job.deloitte.com", href)
            m = re.search(r"_([0-9]{3,})$", href)
            job_id = m.group(1) if m else ""
            jobs.append({"title": title, "job_id": job_id, "url": link})
        return jobs

    def _parse_job_location(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        pill = soup.select_one('[class*=location], [class*=standort], [data-testid*=location]')
        if pill:
            text = pill.get_text(" ", strip=True)
            text = re.sub(r"^STANDORT\s*", "", text, flags=re.IGNORECASE).strip()
            return text

        label = soup.find(string=lambda s: isinstance(s, str) and s.strip().upper() == "STANDORT")
        if label:
            nxt = label.parent.find_next(string=True)
            if nxt:
                return str(nxt).strip()
        return ""

    async def _fetch_job_location(self, url: str) -> str:
        try:
            html = await self._fetch_html(url)
            return self._parse_job_location(html)
        except Exception:
            return ""

    async def get_jobs(self):
        page = 1
        while True:
            page_url = self._build_url(page=page)
            try:
                html = await self._fetch_html(page_url)
            except Exception:
                break

            jobs_data = self._parse_listing_page(html)
            if not jobs_data:
                break

            # Fetch all job locations concurrently
            location_tasks = [
                self._fetch_job_location(job_dict["url"])
                for job_dict in jobs_data
            ]
            locations = await asyncio.gather(*location_tasks)

            for job_dict, location in zip(jobs_data, locations):
                yield Job(
                    title=job_dict["title"],
                    url=job_dict["url"],
                    company="Deloitte",
                    location=location,
                    job_id=job_dict["job_id"]
                )

            if len(jobs_data) < 10:
                break
            page += 1


if __name__ == "__main__":
    async def main():
        crawler = Deloitte()
        async for job in crawler.get_jobs():
            print(f"[{job.job_id}]: {job.title} at {job.location}")

    asyncio.run(main())

