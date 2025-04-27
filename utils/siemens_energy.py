import httpx
from bs4 import BeautifulSoup as bs

from schemas import Job


class SiemensEnergy:
    def __init__(self):
        self.headers = {
            'Host': 'jobs.siemens-energy.com',
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9" \
                ",image/avif,image/webp,image/apng,*/*;q=0.8,application/sig" \
                "ned-exchange;v=b3;q=0.7"
        }
        self.url = "https://jobs.siemens-energy.com/en_US/jobs/Jobs/?29454=9" \
            "64485&29454_format=11381&29457=102154&29457_format=11384&listFi" \
            "lterMode=1&folderSort=schemaField_3_146_3&folderSortDirection=D" \
            "ESC&folderRecordsPerPage=20&folderOffset={}"
    
    async def _make_request(self, offset=0):
        async with httpx.AsyncClient() as client:
            response = await client.get(url=self.url.format(offset), headers=self.headers)
            response.raise_for_status()
            return response.text

    async def get_jobs(self):
        offset = 0
        soup = bs(await self._make_request(offset), 'html.parser')
        while soup.select('.article--result summary.article__header a'):
            for job in soup.select('.article--result summary.article__header a'):
                yield Job(
                    title=job.text.strip(),
                    url=job.get("href"),
                    company="Siemens_Energy"
                )
            offset += 20
            soup = bs(await self._make_request(offset), 'html.parser')

