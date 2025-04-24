from requests import get
from datetime import datetime
from bs4 import BeautifulSoup as bs

from schemas import Job


class Fraunhofer:
    def __init__(self):
        self.url = "https://iisfraunhofer.softgarden.io/en/vacancies"
    
    def _make_request(self):
        response = get(self.url)
        response.raise_for_status()
        return response.text
    
    def get_jobs(self):
        soup = bs(self._make_request(), "html.parser")
        for job in soup.select(".matchElement:has(.matchValue.audience:-soup" \
                               "-contains('Student')):has(.location-view-ite" \
                                "m:-soup-contains('Erlangen'), .location-vie" \
                                "w-item:-soup-contains('Nürnberg'))"):
            yield Job(
                title = job.select_one("a").text,
                url = "https://iisfraunhofer.softgarden.io" + job.select_one("a").get("href")[2:],
                location = job.select_one(".location-view-item").text,
                create_time=datetime.strptime(job.select_one(".date").text, "%m/%d/%y")
            )

