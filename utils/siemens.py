from requests import get


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

    def _make_request(self, start=0):
        response = get(url=self.url.format(start), headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_jobs(self):
        start = 0
        positions = self._make_request(start)["positions"]
        while positions:
            for job in positions:
                yield {
                    "name": job["name"],
                    "location": job["location"],
                    "t_update": job["t_update"],
                    "t_create": job["t_create"],
                    "display_job_id": job["display_job_id"],
                    "work_location_option": job["work_location_option"],
                    "canonicalPositionUrl": job["canonicalPositionUrl"],
                }
            start += 10
            positions = self._make_request(start)["positions"]


if __name__ == "__main__":
    se = Siemens()
    for job in se.get_jobs():
        print(job)

