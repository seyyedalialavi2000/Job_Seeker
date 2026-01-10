import textwrap

import requests


API_URL = "https://www.accenture.com/api/accenture/jobsearch/result"

BASE_PAYLOAD = {
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

headers = {
	"User-Agent": "Mozilla/5.0",
	# Avoid urllib3/requests zstd decode issues by not advertising zstd support.
	"Accept-Encoding": "gzip, deflate",
}


def fetch_page(*, start_index: int, max_result_size: int):
	payload = dict(BASE_PAYLOAD)
	payload["startIndex"] = str(start_index)
	payload["maxResultSize"] = str(max_result_size)
	r = requests.post(API_URL, headers=headers, data=payload, timeout=30)
	r.raise_for_status()
	j = r.json()
	jobs = j.get("data") or []
	total = j.get("total")
	return jobs, total


def job_key(job: dict) -> str:
	return str(job.get("jobId") or job.get("requisitionId") or "")


def job_link(job: dict) -> str:
	return str(job.get("jobDetailUrl") or "")


def job_locations(job: dict) -> str:
	locs = job.get("jobCityState")
	if isinstance(locs, list):
		return ", ".join(locs)
	return str(locs or "")


if __name__ == "__main__":
	PAGE_SIZE = 25
	MAX_PAGES = 200

	all_jobs = []
	seen = set()
	start = 0
	pages = 0
	total_available = None

	while pages < MAX_PAGES:
		jobs, total = fetch_page(start_index=start, max_result_size=PAGE_SIZE)
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

		if new_in_page == 0:
			break

		start += len(jobs)

		if total_available is not None and len(all_jobs) >= total_available:
			break
		if len(jobs) < PAGE_SIZE:
			break

	print(f"loaded {len(all_jobs)} jobs (pages={pages}, start_end={start}, total_available={total_available})")

	idx_w = len(str(len(all_jobs)))
	id_w = max(8, max((len(job_key(j)) for j in all_jobs), default=8))
	loc_w = 45
	title_w = 60

	header = f"{'#':>{idx_w}}  {'JOB_ID':<{id_w}}  {'LOCATION':<{loc_w}}  {'TITLE':<{title_w}}"
	print(header)
	print("-" * len(header))

	for i, job in enumerate(all_jobs, start=1):
		jid = job_key(job)
		loc = textwrap.shorten(job_locations(job), width=loc_w, placeholder="…")
		title = textwrap.shorten(str(job.get("title") or ""), width=title_w, placeholder="…")
		link = job_link(job)
		print(f"{i:>{idx_w}}  {jid:<{id_w}}  {loc:<{loc_w}}  {title:<{title_w}}")
		print(f"{'':>{idx_w}}  LINK: {link}")
