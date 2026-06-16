import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from schemas import Job
from crawlers.base import BaseCrawler


class SAP(BaseCrawler):
    """Crawler for SAP job postings."""

    def __init__(self):
        self.base_url = (
            "https://jobs.sap.com/search/?"
            "createNewAlert=false&"
            "q=AI+Data&"
            "locationsearch=&"
            "optionsFacetsDD_department=&"
            "optionsFacetsDD_customfield3=Professional&"
            "optionsFacetsDD_country=DE"
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Encoding": "gzip, deflate",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    def _build_url(self, startrow: int) -> str:
        parts = urlsplit(self.base_url)
        q = parse_qs(parts.query, keep_blank_values=True)
        q["startrow"] = [str(startrow)]
        new_query = urlencode(q, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    async def _fetch_page(self, startrow: int) -> str:
        page_url = self._build_url(startrow=startrow)
        r = await self.client.get(page_url)
        r.raise_for_status()
        return r.text

    def _parse_jobs(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for a in soup.select('a[href*="/job/"]'):
            href = a.get("href")
            if not href or "/job/" not in href:
                continue
            full = urljoin("https://jobs.sap.com", href)
            text = a.get_text(" ", strip=True)
            m = re.search(r"/job/.+/(\d+)/?", full)
            job_id = m.group(1) if m else ""
            # Simple location extraction if available in the text or surrounding, 
            # but current script doesn't have it.
            jobs.append({"title": text, "link": full, "id": job_id})

        # de-dupe by link while preserving order
        seen = set()
        out = []
        for j in jobs:
            if j["link"] in seen:
                continue
            seen.add(j["link"])
            out.append(j)
        return out

    async def get_jobs(self):
        page_size = 25
        max_pages = 200
        startrow = 0
        pages = 0
        seen_links = set()

        while pages < max_pages:
            try:
                html = await self._fetch_page(startrow=startrow)
            except Exception:
                break
                
            jobs = self._parse_jobs(html)
            pages += 1

            if not jobs:
                break

            new_in_page = 0
            for j in jobs:
                if j["link"] in seen_links:
                    continue
                seen_links.add(j["link"])
                
                yield Job(
                    title=j["title"],
                    url=j["link"],
                    company="SAP",
                    location="",  # Location not extracted in original script
                    job_id=j["id"]
                )
                new_in_page += 1

            if new_in_page == 0:
                break

            startrow += page_size
            if len(jobs) < page_size:
                break


if __name__ == "__main__":
    async def main():
        crawler = SAP()
        async for job in crawler.get_jobs():
            print(f"[{job.job_id}]: {job.title} at {job.location}")

    asyncio.run(main())
