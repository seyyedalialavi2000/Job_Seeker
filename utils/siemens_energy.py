from requests import get
from bs4 import BeautifulSoup as bs


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
            "lterMode=1&folderRecordsPerPage=20&"
    
    def _make_request(self):
        response = get(url=self.url, headers=self.headers)
        response.raise_for_status()
        return response.text

    def get_jobs(self):
        soup = bs(self._make_request(), 'html.parser')
        for job in soup.select('.article.article--result summary.article__header a'):
            yield {
                "url": job.get("href"),
                "title": job.text.strip()
            }


if __name__ == "__main__":
    se = SiemensEnergy()
    for job in se.get_jobs():
        print(job)

