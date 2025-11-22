import os
from typing import List, Optional
import httpx
from dotenv import load_dotenv
load_dotenv()



TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")


class TicketmasterError(Exception):
    """Custom exception for Ticketmaster-related errors."""
    pass


async def fetch_ticketmaster_events(
    lat: float,
    lon: float,
    radius_km: float = 20.0,
    keyword: Optional[str] = None,
    size: int = 20,
) -> List[dict]:
    """
    Call Ticketmaster Discovery API and return a normalized list of events.

    Args:
        lat: Latitude of the search location.
        lon: Longitude of the search location.
        radius_km: Search radius in kilometers.
        keyword: Optional keyword to filter events (e.g. "social", "music").
        size: Maximum number of events to fetch.

    Returns:
        List of dicts, each representing a simplified event.
    """
    if not TICKETMASTER_API_KEY:
        raise TicketmasterError("TICKETMASTER_API_KEY is not set in environment")

    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"

    radius_int = int(radius_km)
    if radius_int < 0:
        radius_int = 0
    if radius_int > 19999:
        radius_int = 19999

    params = {
        "apikey": TICKETMASTER_API_KEY,
        "latlong": f"{lat},{lon}",
        "radius": radius_int,   # 👈 now always an int
        "unit": "km",
        "size": size,
        "sort": "date,asc",
        "locale": "*",
    }

    if keyword:
        params["keyword"] = keyword

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(base_url, params=params)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise TicketmasterError(
                f"Ticketmaster API error: {e.response.status_code} {e.response.text}"
            ) from e

        data = resp.json()

    events_raw = data.get("_embedded", {}).get("events", [])
    events: List[dict] = []

    for ev in events_raw:
        venues = ev.get("_embedded", {}).get("venues") or [{}]
        venue = venues[0]

        classifications = ev.get("classifications") or [{}]
        classification = classifications[0]

        events.append(
            {
                "id": ev.get("id"),
                "name": ev.get("name"),
                "url": ev.get("url"),
                "start_date_time": ev.get("dates", {}).get("start", {}).get("dateTime"),
                "local_date": ev.get("dates", {}).get("start", {}).get("localDate"),
                "local_time": ev.get("dates", {}).get("start", {}).get("localTime"),
                "venue_name": venue.get("name"),
                "city": (venue.get("city") or {}).get("name"),
                "country": (venue.get("country") or {}).get("name"),
                "segment": (classification.get("segment") or {}).get("name"),
                "genre": (classification.get("genre") or {}).get("name"),
            }
        )

    return events
