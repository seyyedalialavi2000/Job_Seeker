import requests
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

url = "https://www.amazon.jobs/en/search.json?category%5B%5D=operations-it-support-engineering&schedule_type_id%5B%5D=Full-Time&radius=24km&facets%5B%5D=normalized_country_code&facets%5B%5D=normalized_state_name&facets%5B%5D=normalized_city_name&facets%5B%5D=location&facets%5B%5D=business_category&facets%5B%5D=category&facets%5B%5D=schedule_type_id&facets%5B%5D=employee_class&facets%5B%5D=normalized_location&facets%5B%5D=job_function_id&facets%5B%5D=is_manager&facets%5B%5D=is_intern&offset=0&result_limit=10&sort=relevant&latitude=&longitude=&loc_group_id=&loc_query=Germany&base_query=&city=&country=DEU&region=&county=&query_options=&"
headers = {
  'Cookie': 'amazon_jobs_session=eHJ3dGxCZU5lL3hpcGxTd0xFMTN0cjZPY2JZRk1MTjhDRis1aVVoS0NkcEMxZ2xRUVo4a0Z6UEtPaGt2d3dZeUpueDVhUUU2d1lXcGFKV0Rma3Ftd3hvSk5udjFRQmJnbW5BUXJQZndCZHF5WG1Qa1RWdlZrcGlzbG9uSEZNMWpteHhvRGJQSmNqcHgrRTMxeGVYWU8rTDFXVy85NlU3VFcxQ25uR285Y1VydUxyS092Q1RlU0p2NnYyN2syd21hcVdVUEpvakNpd1dxWEtlOXVXem9ueDZ4UXZDc0d6RnNKNDRrMUUzVThUNE96czdNQ1MzVE1hSFh0MkVldDFCdjFBbDh2VWxhc1hpdFhIM0FMK2wrY0E4VkVlZHFGZ1ltaVhJaXlXNldDdm1BU3I4TEo4NlNpZFY3YXh4N2tEbnhJZ2xVeHk5TVovUHc0NUpYb2k5TXVQN0o0YmZvK1FBaDhUSmNnMnlsaXVvPS0tTVpUU21GUXBQQ2VlZVF3dnhqZ0ZtZz09--24ee8f6f4b6516d279026abed7b6b3d0a6f26cde; analytics_id=c0f699f2-518e-4deb-b66e-093967721374; preferred_locale=en-US; __Host-mons-sid=259-6939028-9925318; __Host-mons-st=mCO3TYsNlP6KXNQXqVv8hZpIU2r6PNcwbXAeBbBflwmQdLD/yWTgUqZ5bHNtUQBjv0QOvc2pw9UfFKp+eQ0pNFG6pXbN4vA4q0H1o3oJcY3ean5tdJXU7OHF+s10WenPQ7gh+TOVk0/1Ob1HQyWP7dr7rGu7G29rmJZsiACnKI2J1hnBCorfFPDS27KkzDKvPvSnAdIOSjKDybjT28B/qUCRP72wv0bxxO8XhB26CGRR0hAxykPpb+/j0ybOdannaB6qnIM/Fn8u2U4Pt/vTGQwQYBUyTeqQ6L9T0k4JAdBrUuGwupTGFzABDvrbQ2CsWOMeB2GHKEUWaovKRi53HhWZCZTA/PUoksF0VPBplR4=; __Host-mons-ubid=260-7204987-9465821'
}

# Avoid urllib3/requests zstd decode issues by not advertising zstd support.
headers.setdefault('Accept-Encoding', 'gzip, deflate')


def build_url(base_url: str, *, offset: int, result_limit: int) -> str:
  parts = urlsplit(base_url)
  q = parse_qs(parts.query, keep_blank_values=True)
  q['offset'] = [str(offset)]
  q['result_limit'] = [str(result_limit)]
  new_query = urlencode(q, doseq=True)
  return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def fetch_jobs(base_url: str, *, offset: int, result_limit: int):
  page_url = build_url(base_url, offset=offset, result_limit=result_limit)
  r = requests.get(page_url, headers=headers, timeout=30)
  r.raise_for_status()
  data = r.json()
  jobs = data.get('jobs') or data.get('results') or []
  total = (
    data.get('total_hits')
    or data.get('total')
    or data.get('hits')
    or data.get('count')
  )
  return jobs, total


def job_key(job: dict) -> str:
  return str(job.get('id') or job.get('job_id') or job.get('requisition_id') or '')


def job_link(job: dict) -> str:
  path = job.get('job_path') or job.get('url_next_step') or job.get('url')
  if not path:
    return ''
  if isinstance(path, str) and path.startswith('http'):
    return path
  if isinstance(path, str) and path.startswith('/'):
    return f"https://www.amazon.jobs{path}"
  return str(path)


def format_job(job: dict) -> str:
  title = job.get('title') or job.get('job_title') or '(no title)'
  location = job.get('location') or job.get('normalized_location') or '(no location)'
  jid = job_key(job)
  link = job_link(job)
  if link:
    return f"{title} | {location} | {jid} | {link}".strip()
  return f"{title} | {location} | {jid}".strip()


if __name__ == "__main__":
  # If you only want N jobs, set this to a number (e.g., 50). Use None for "all".
  TOTAL_JOBS_TO_LOAD = None
  PAGE_SIZE = 50
  MAX_PAGES = 200

  all_jobs = []
  seen = set()
  offset = 0
  pages = 0
  total_available = None

  while pages < MAX_PAGES:
    jobs, total = fetch_jobs(url, offset=offset, result_limit=PAGE_SIZE)
    pages += 1

    if total_available is None and isinstance(total, int):
      total_available = total

    if not jobs:
      break

    new_in_page = 0
    for job in jobs:
      key = job_key(job)
      if key and key in seen:
        continue
      if key:
        seen.add(key)
      all_jobs.append(job)
      new_in_page += 1

    # Stop if the server keeps returning the same results.
    if new_in_page == 0:
      break

    offset += len(jobs)

    if total_available is not None and len(all_jobs) >= total_available:
      break
    if TOTAL_JOBS_TO_LOAD is not None and len(all_jobs) >= TOTAL_JOBS_TO_LOAD:
      break

  if TOTAL_JOBS_TO_LOAD is not None:
    all_jobs = all_jobs[:TOTAL_JOBS_TO_LOAD]

  print(f"loaded {len(all_jobs)} jobs (pages={pages}, offset_end={offset}, total_available={total_available})")
  for job in all_jobs:
    print(f"- {format_job(job)}")



