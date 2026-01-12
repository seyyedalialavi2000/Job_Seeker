import httpx
from datetime import datetime
from schemas import Job
from crawlers.base import BaseCrawler


class Accenture(BaseCrawler):
    """Crawler for Accenture job postings."""

    def __init__(self):
        self.url = "https://www.accenture.com/api/accenture/jobsearch/result"
        self.payload = {
            "jobKeyword": "",
            "jobLanguage": "de",
            "countrySite": "de-de",
            "jobFilters": (
                "[{\"fieldName\":\"skill\",\"items\":[\"ai & data\",\"business & technology integration\",\"software engineering\",\"technology & information architectures\"]},"
                "{\"fieldName\":\"employeeType\",\"items\":[\"full-time\"]}]"
            ),
            "aggregations": (
                "[{\"fieldName\":\"location\"},{\"fieldName\":\"postedDate\"},{\"fieldName\":\"jobTypeDescription\"},"
                "{\"fieldName\":\"workforceEntity\"},{\"fieldName\":\"businessArea\"},{\"fieldName\":\"skill\"},"
                "{\"fieldName\":\"travelPercentage\"},{\"fieldName\":\"yearsOfExperience\"},{\"fieldName\":\"specialization\"},"
                "{\"fieldName\":\"employeeType\"},{\"fieldName\":\"remoteType\"}]"
            ),
            "jobCountry": "Deutschland",
            "sortBy": "1",
            "componentId": "careerjobsearchresults-6a5fbb2938",
        }

    async def _make_request(self, start_index=0, max_result_size=25):
        payload = dict(self.payload)
        payload["startIndex"] = str(start_index)
        payload["maxResultSize"] = str(max_result_size)
        
        async with httpx.AsyncClient() as client:
            r = await client.post(self.url, data=payload, timeout=30.0)
            r.raise_for_status()
            return r.json()

    async def get_jobs(self):
        start = 0
        page_size = 25

        while True:
            data = await self._make_request(start_index=start, max_result_size=page_size)
            jobs_data = data.get("data") or []
            total = data.get("total")

            if not jobs_data:
                break

            for job in jobs_data:
                locs = job.get("jobCityState")
                location = ", ".join(locs) if isinstance(locs, list) else str(locs or "")
                
                posted_date = job.get("postedDate")
                update_time = datetime.fromtimestamp(posted_date / 1000.0) if posted_date else None

                yield Job(
                    title=job.get("title", ""),
                    url=job.get("jobDetailUrl", ""),
                    company="Accenture",
                    location=location,
                    update_time=update_time,
                    job_id=str(job.get("requisitionId") or ""),
                    remote_vs_office=job.get("jobRemoteType") or None
                )

            start += len(jobs_data)
            if total is not None and start >= total:
                break
            if len(jobs_data) < page_size:
                break


if __name__ == "__main__":
    import asyncio

    async def main():
        crawler = Accenture()
        async for job in crawler.get_jobs():
            print(f"{job.job_id}: {job.title} at {job.location} | Updated: {job.update_time}")

    asyncio.run(main())
