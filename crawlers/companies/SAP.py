import re
import textwrap
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup


BASE_URL = (
  "https://jobs.sap.com/search/?"
  "createNewAlert=false&"
  "q=AI+Data&"
  "locationsearch=&"
  "optionsFacetsDD_department=&"
  "optionsFacetsDD_customfield3=Professional&"
  "optionsFacetsDD_country=DE"
)

headers = {
  "User-Agent": "Mozilla/5.0",
  # Avoid urllib3/requests zstd decode issues by not advertising zstd support.
  "Accept-Encoding": "gzip, deflate",
}


def build_url(base_url: str, *, startrow: int) -> str:
  parts = urlsplit(base_url)
  q = parse_qs(parts.query, keep_blank_values=True)
  q["startrow"] = [str(startrow)]
  new_query = urlencode(q, doseq=True)
  return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def fetch_page(base_url: str, *, startrow: int) -> str:
  page_url = build_url(base_url, startrow=startrow)
  r = requests.get(page_url, headers=headers, timeout=30)
  r.raise_for_status()
  return r.text


def parse_jobs(html: str):
  soup = BeautifulSoup(html, "html.parser")

  jobs = []
  # SAP search pages include job links like /job/<title>-<location>/<job_id>/
  for a in soup.select('a[href*="/job/"]'):
    href = a.get("href")
    if not href or "/job/" not in href:
      continue
    full = urljoin("https://jobs.sap.com", href)
    text = a.get_text(" ", strip=True)

    # Extract numeric job id from the URL (last path segment before trailing slash)
    m = re.search(r"/job/.+/(\d+)/?", full)
    job_id = m.group(1) if m else ""

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


if __name__ == "__main__":
  PAGE_SIZE = 25
  MAX_PAGES = 200

  all_jobs = []
  seen_links = set()
  startrow = 0
  pages = 0

  while pages < MAX_PAGES:
    html = fetch_page(BASE_URL, startrow=startrow)
    jobs = parse_jobs(html)
    pages += 1

    if not jobs:
      break

    new_in_page = 0
    for j in jobs:
      if j["link"] in seen_links:
        continue
      seen_links.add(j["link"])
      all_jobs.append(j)
      new_in_page += 1

    if new_in_page == 0:
      break

    startrow += PAGE_SIZE

    # If this page has fewer than a full page, it's probably the last page.
    if len(jobs) < PAGE_SIZE:
      break

  print(f"loaded {len(all_jobs)} jobs (pages={pages}, startrow_end={startrow})")

  idx_w = len(str(len(all_jobs)))
  id_w = max(6, max((len(j["id"]) for j in all_jobs if j.get("id")), default=6))
  title_w = 70

  header = f"{'#':>{idx_w}}  {'JOB_ID':<{id_w}}  {'TITLE':<{title_w}}  LINK"
  print(header)
  print("-" * len(header))

  for i, j in enumerate(all_jobs, start=1):
    title = textwrap.shorten(j.get("title", ""), width=title_w, placeholder="…")
    job_id = j.get("id", "")
    link = j.get("link", "")
    print(f"{i:>{idx_w}}  {job_id:<{id_w}}  {title:<{title_w}}  {link}")
