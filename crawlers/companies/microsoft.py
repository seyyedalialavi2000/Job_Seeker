import asyncio
import httpx
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from schemas import Job
from crawlers.base import BaseCrawler


class Microsoft(BaseCrawler):
    """Crawler for Microsoft job postings."""

    def __init__(self):
        self.base_api_url = (
            "https://apply.careers.microsoft.com/api/pcsx/search?"
            "domain=microsoft.com&"
            "query=&"
            "location=germany&"
            "start=0&"
            "sort_by=distance&"
            "filter_profession=data+center&"
            "filter_profession=software+engineering&"
            "filter_profession=research%252C%2520applied%252C%2520%2526%2520data%2520sciences&"
            "filter_profession=program+management"
        )
        self.job_base_url = "https://jobs.careers.microsoft.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    def _build_url(self, start: int) -> str:
        parts = urlsplit(self.base_api_url)
        q = parse_qs(parts.query, keep_blank_values=True)
        q["start"] = [str(start)]
        new_query = urlencode(q, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    async def _fetch_positions(self, start: int):
        page_url = self._build_url(start=start)
        r = await self.client.get(page_url)
        r.raise_for_status()

        payload = r.json()
        data = payload.get("data") or {}
        positions = data.get("positions") or []
        total = data.get("count")
        return positions, total

    def _position_key(self, pos: dict) -> str:
        return str(pos.get("id") or pos.get("atsJobId") or pos.get("displayJobId") or "")

    def _position_link(self, pos: dict) -> str:
        path = pos.get("positionUrl")
        if not path:
            return ""
        if isinstance(path, str) and path.startswith("http"):
            return path
        if isinstance(path, str) and path.startswith("/"):
            return f"{self.job_base_url}{path}"
        return str(path)

    async def get_jobs(self):
        max_pages = 200
        seen = set()
        start = 0
        pages = 0
        total_available = None

        while pages < max_pages:
            try:
                positions, total = await self._fetch_positions(start=start)
            except Exception:
                break
            
            pages += 1

            if total_available is None and isinstance(total, int):
                total_available = total

            if not positions:
                break

            new_in_page = 0
            for pos in positions:
                key = self._position_key(pos)
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                
                title = pos.get("name") or "(no title)"
                locations = pos.get("locations") or []
                location_str = ", ".join(locations[:3]) if isinstance(locations, list) else str(locations)
                link = self._position_link(pos)
                
                yield Job(
                    title=title,
                    url=link,
                    company="Microsoft",
                    location=location_str,
                    job_id=key
                )
                new_in_page += 1

            if new_in_page == 0:
                break

            start += len(positions)

            if total_available is not None and len(seen) >= total_available:
                break


if __name__ == "__main__":
    async def main():
        crawler = Microsoft()
        async for job in crawler.get_jobs():
            print(f"[{job.job_id}]: {job.title} at {job.location}")

    asyncio.run(main())
