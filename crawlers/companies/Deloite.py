import re
import textwrap
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://job.deloitte.com/ai-data-analytics-jobs-_pr1"

headers = {
  "User-Agent": "Mozilla/5.0",
  # Avoid urllib3/requests zstd decode issues by not advertising zstd support.
  "Accept-Encoding": "gzip, deflate",
}


def build_url(base_url: str, *, page: int) -> str:
  parts = urlsplit(base_url)
  q = parse_qs(parts.query, keep_blank_values=True)
  if page <= 1:
    q.pop("page", None)
  else:
    q["page"] = [str(page)]
  new_query = urlencode(q, doseq=True)
  return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def fetch_html(url: str) -> str:
  r = requests.get(url, headers=headers, timeout=30)
  r.raise_for_status()
  return r.text


def parse_listing_jobs(html: str):
  soup = BeautifulSoup(html, "html.parser")
  jobs = []
  for a in soup.select('a[href^="/job-"]'):
    href = a.get("href")
    title = a.get_text(" ", strip=True)
    if not href or not title:
      continue
    link = urljoin("https://job.deloitte.com", href)
    # job id is usually after the last underscore: ...-_49507
    m = re.search(r"_([0-9]{3,})$", href)
    job_id = m.group(1) if m else ""
    jobs.append({"title": title, "id": job_id, "link": link})

  # de-dupe by link
  seen = set()
  out = []
  for j in jobs:
    if j["link"] in seen:
      continue
    seen.add(j["link"])
    out.append(j)
  return out


def parse_job_locations(job_html: str) -> str:
  soup = BeautifulSoup(job_html, "html.parser")
  # On Deloitte pages, location block often contains the label 'STANDORT'
  pill = soup.select_one('[class*=location], [class*=standort], [data-testid*=location]')
  if pill:
    text = pill.get_text(" ", strip=True)
    text = re.sub(r"^STANDORT\s*", "", text, flags=re.IGNORECASE).strip()
    return text

  # Fallback: find 'STANDORT' label and take the next text blob
  label = soup.find(string=lambda s: isinstance(s, str) and s.strip().upper() == "STANDORT")
  if label:
    nxt = label.parent.find_next(string=True)
    if nxt:
      return str(nxt).strip()
  return ""


if __name__ == "__main__":
  MAX_PAGES = 200
  FETCH_JOB_DETAILS = True

  all_jobs = []
  seen = set()
  pages = 0
  page = 1

  while pages < MAX_PAGES:
    page_url = build_url(BASE_URL, page=page)
    html = fetch_html(page_url)
    jobs = parse_listing_jobs(html)
    pages += 1

    if not jobs:
      break

    new_in_page = 0
    for j in jobs:
      if j["link"] in seen:
        continue
      seen.add(j["link"])
      all_jobs.append(j)
      new_in_page += 1

    if new_in_page == 0:
      break

    # If we got fewer than 10 jobs, it's probably the last page.
    if len(jobs) < 10:
      break

    page += 1

  if FETCH_JOB_DETAILS:
    for j in all_jobs:
      try:
        job_html = fetch_html(j["link"])
        j["location"] = parse_job_locations(job_html)
      except Exception:
        j["location"] = ""

  print(f"loaded {len(all_jobs)} jobs (pages={pages}, page_end={page})")

  idx_w = len(str(len(all_jobs)))
  id_w = max(5, max((len(j.get("id", "")) for j in all_jobs), default=5))
  loc_w = 40
  title_w = 60

  header = f"{'#':>{idx_w}}  {'JOB_ID':<{id_w}}  {'LOCATION':<{loc_w}}  {'TITLE':<{title_w}}  LINK"
  print(header)
  print("-" * len(header))

  for i, j in enumerate(all_jobs, start=1):
    title = textwrap.shorten(j.get("title", ""), width=title_w, placeholder="…")
    loc = textwrap.shorten(j.get("location", ""), width=loc_w, placeholder="…")
    jid = j.get("id", "")
    link = j.get("link", "")
    print(f"{i:>{idx_w}}  {jid:<{id_w}}  {loc:<{loc_w}}  {title:<{title_w}}  {link}")