import json
import re
import sys
import threading
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas import Job
from crawlers.base import BaseCrawler
from utils import get_logger


logger = get_logger(__name__)


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
    JOBS_PORTAL_URL = "https://jobs.bosch.com/en/"
    JOB_LINK_PREFIX = "https://jobs.bosch.com/en/job/"
    PAGE_SIZE = 20
    COMPANY = "Bosch"
    TOKEN_REFRESH_INTERVAL_SEC = 45 * 60
    TOKEN_WAIT_TIMEOUT_SEC = 20.0
    SCRIPT_SRC_PATTERN = re.compile(r"<script[^>]+src=[\"']([^\"']+)[\"']", re.I)
    API_KEY_PATTERNS = [
        re.compile(r"jobsApi\s*:\s*\{[^}]*apiKey\s*:\s*\"([^\"]+)\"", re.S),
        re.compile(r"caasApiKey\s*:\s*\"([^\"]+)\"", re.S),
        re.compile(r"apiKey\s*:\s*\"([^\"]+)\"", re.S),
        re.compile(r"Bearer\s+([0-9a-fA-F-]{36})", re.I),
    ]
    UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

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
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        self.avars = {
            "country": ["de"],
            "position_types": self.POSITION_TYPES,
            "working_hours": self.WORKING_HOURS,
            "sort": {"releasedDate": -1},
        }

        self._token: Optional[str] = None
        self._token_version = 0
        self._token_lock = threading.Lock()
        self._refresh_requested = threading.Event()
        self._stop_refresh = threading.Event()
        self._token_thread = threading.Thread(
            target=self._token_refresh_worker,
            name="bosch-token-refresh",
            daemon=True,
        )
        self._token_thread.start()
        self._refresh_requested.set()

    def _get_token(self) -> Optional[str]:
        with self._token_lock:
            return self._token

    def _set_token(self, token: str) -> None:
        with self._token_lock:
            if token != self._token:
                self._token = token
                self._token_version += 1

    def _request_token_refresh(self, reason: str, wait: bool = False) -> bool:
        with self._token_lock:
            current_version = self._token_version

        logger.info(f"Bosch token refresh requested: {reason}")
        self._refresh_requested.set()

        if not wait:
            return True

        deadline = time.time() + self.TOKEN_WAIT_TIMEOUT_SEC
        while time.time() < deadline:
            with self._token_lock:
                if self._token_version > current_version and self._token:
                    return True
            time.sleep(0.2)

        return bool(self._get_token())

    def _extract_candidate_tokens(self, text: str) -> list[str]:
        candidates: list[str] = []
        seen: set[str] = set()

        for pattern in self.API_KEY_PATTERNS:
            for m in pattern.findall(text):
                token = m if isinstance(m, str) else m[0]
                token = token.strip()
                if not token or token in seen:
                    continue
                seen.add(token)
                candidates.append(token)

        # Fallback: some pages expose plain UUIDs instead of explicit "apiKey" labels.
        for token in self.UUID_PATTERN.findall(text):
            if token in seen:
                continue
            seen.add(token)
            candidates.append(token)

        return candidates

    def _extract_script_urls(self, html: str) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        for m in self.SCRIPT_SRC_PATTERN.finditer(html):
            src = m.group(1).strip()
            if not src:
                continue
            full_url = urljoin(self.JOBS_PORTAL_URL, src)
            if full_url in seen:
                continue
            seen.add(full_url)
            urls.append(full_url)
        return urls

    def _validate_candidate_token(self, client: httpx.Client, token: str) -> bool:
        probe_params = {
            "page": 1,
            "pagesize": 1,
            "avars": json.dumps({"country": ["de"], "sort": {"releasedDate": -1}}),
        }
        probe_headers = {**self.headers, "Authorization": f"Bearer {token}"}

        try:
            response = client.get(
                self.BASE_URL,
                headers=probe_headers,
                params=probe_params,
                timeout=20.0,
            )
        except httpx.HTTPError:
            return False

        return response.status_code == 200

    def _discover_token(self) -> Optional[str]:
        with httpx.Client(follow_redirects=True, timeout=30.0, headers=self.headers) as client:
            r = client.get(self.JOBS_PORTAL_URL)
            r.raise_for_status()
            html = r.text

            candidates: list[str] = []
            seen: set[str] = set()

            for token in self._extract_candidate_tokens(html):
                if token not in seen:
                    seen.add(token)
                    candidates.append(token)

            for script_url in self._extract_script_urls(html):
                try:
                    js = client.get(script_url)
                    js.raise_for_status()
                except httpx.HTTPError:
                    continue

                for token in self._extract_candidate_tokens(js.text):
                    if token not in seen:
                        seen.add(token)
                        candidates.append(token)

            for token in candidates[:50]:
                if self._validate_candidate_token(client, token):
                    return token

        return None

    def _token_refresh_worker(self) -> None:
        while not self._stop_refresh.is_set():
            self._refresh_requested.wait(timeout=self.TOKEN_REFRESH_INTERVAL_SEC)
            if self._stop_refresh.is_set():
                break
            self._refresh_requested.clear()

            try:
                token = self._discover_token()
            except Exception as exc:
                logger.warning(f"Failed to refresh Bosch token: {exc}")
                continue

            if token:
                self._set_token(token)
                logger.info("Bosch token refreshed successfully")
            else:
                logger.warning("Bosch token refresh returned no token")

    def _stop_token_worker(self) -> None:
        self._stop_refresh.set()
        self._refresh_requested.set()
        if self._token_thread.is_alive():
            self._token_thread.join(timeout=1.5)

    async def _fetch_page(self, client: httpx.AsyncClient, page: int) -> dict:
        params = {
            "page": page,
            "pagesize": self.PAGE_SIZE,
            "avars": json.dumps(self.avars),
        }

        if not self._get_token():
            ok = await asyncio.to_thread(
                self._request_token_refresh,
                "startup",
                True,
            )
            if not ok:
                raise RuntimeError("Could not fetch Bosch API token")

        token = self._get_token()
        request_headers = {**self.headers, "Authorization": f"Bearer {token}"}

        r = await client.get(self.BASE_URL, headers=request_headers, params=params, timeout=30.0)

        if r.status_code in (401, 403):
            logger.warning(f"Bosch auth failed with status {r.status_code}; refreshing token")
            ok = await asyncio.to_thread(
                self._request_token_refresh,
                f"auth_{r.status_code}",
                True,
            )
            if not ok:
                r.raise_for_status()

            token = self._get_token()
            request_headers = {**self.headers, "Authorization": f"Bearer {token}"}
            r = await client.get(self.BASE_URL, headers=request_headers, params=params, timeout=30.0)

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
        try:
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
        finally:
            self._stop_token_worker()


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
