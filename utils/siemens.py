import httpx

from schemas import Job


class Siemens:
    def __init__(self):
        self.headers = {
            'accept': '*/*',
            'content-type': 'application/json',
        }
        self.url = "https://jobs.siemens.com/api/apply/v2/jobs?domain=siemen" \
            "s.com&start={}&num=10&location=Bayern%2C%20Germany&pid=56315612" \
            "4036636&level=student%20%28not%20yet%20graduated%29&domain=siem" \
            "ens.com&sort_by=relevance&utm_source=j_c_global&triggerGoButton" \
            "=true"

    async def _make_request(self, start=0):
        async with httpx.AsyncClient() as client:
            response = await client.get(url=self.url.format(start), headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_jobs(self):
        start = 0
        positions = (await self._make_request(start))["positions"]
        while positions:
            for job in positions:
                yield Job(
                    title=job["name"],
                    location=job["location"],
                    update_time=job["t_update"],
                    create_time=job["t_create"],
                    job_id=job["display_job_id"],
                    remote_vs_office=job["work_location_option"],
                    url=job["canonicalPositionUrl"],
                    company="Siemens Others"
                )
            start += 10
            positions = (await self._make_request(start))["positions"]

