import requests
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit


BASE_API_URL = (
	"https://apply.careers.microsoft.com/api/pcsx/search?"
	"domain=microsoft.com&"
	"query=&"
	"location=germany&"
	"start=0&"
	"sort_by=distance&"
	"filter_profession=data+center&"
	"filter_profession=software+engineering&"
	"filter_profession=research%252C%2520applied%252C%2520%2526%2520data%2520sciences&"
	"filter_profession=program+management"
)

JOB_BASE_URL = "https://jobs.careers.microsoft.com"

headers = {
	"User-Agent": "Mozilla/5.0",
}


def build_url(base_url: str, *, start: int) -> str:
	parts = urlsplit(base_url)
	q = parse_qs(parts.query, keep_blank_values=True)
	q["start"] = [str(start)]
	new_query = urlencode(q, doseq=True)
	return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def fetch_positions(base_url: str, *, start: int):
	page_url = build_url(base_url, start=start)
	r = requests.get(page_url, headers=headers, timeout=30)
	r.raise_for_status()

	payload = r.json()
	data = payload.get("data") or {}
	positions = data.get("positions") or []
	total = data.get("count")
	return positions, total


def position_key(pos: dict) -> str:
	return str(pos.get("id") or pos.get("atsJobId") or pos.get("displayJobId") or "")


def position_link(pos: dict) -> str:
	path = pos.get("positionUrl")
	if not path:
		return ""
	if isinstance(path, str) and path.startswith("http"):
		return path
	if isinstance(path, str) and path.startswith("/"):
		return f"{JOB_BASE_URL}{path}"
	return str(path)


def format_position(pos: dict) -> str:
	title = pos.get("name") or "(no title)"
	pos_id = position_key(pos)
	locations = pos.get("locations") or []
	location_str = ", ".join(locations[:3]) if isinstance(locations, list) else str(locations)
	link = position_link(pos)
	parts = [title, location_str, pos_id, link]
	return " | ".join([p for p in parts if p])


if __name__ == "__main__":
	MAX_PAGES = 200

	all_positions = []
	seen = set()
	start = 0
	pages = 0
	total_available = None

	while pages < MAX_PAGES:
		positions, total = fetch_positions(BASE_API_URL, start=start)
		pages += 1

		if total_available is None and isinstance(total, int):
			total_available = total

		if not positions:
			break

		new_in_page = 0
		for pos in positions:
			key = position_key(pos)
			if key and key in seen:
				continue
			if key:
				seen.add(key)
			all_positions.append(pos)
			new_in_page += 1

		if new_in_page == 0:
			break

		start += len(positions)

		if total_available is not None and len(all_positions) >= total_available:
			break

	print(
		f"loaded {len(all_positions)} jobs (pages={pages}, start_end={start}, total_available={total_available})"
	)
	for pos in all_positions:
		print(f"- {format_position(pos)}")
