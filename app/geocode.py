import json
import time
import urllib.parse
import urllib.request

from app.db import get_connection, init_geocoding_schema

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "restaurant-rag-chatbot/1.0 (internal tool, not for redistribution)"
RATE_LIMIT_SECONDS = 1.1

# Some location tags don't match Nominatim's spelling or administrative
# boundary for that area, so the plain "{area}, Ahmedabad, India" fallback
# finds nothing even though the place exists in OSM under a different name.
AREA_ALIASES = {
    "lal_darwaza": "Lal Darwaja, Gujarat, India",
    "vaishnodevi_circle": "Vaishno Devi Circle, Ahmedabad, India",
    "zundal": "Zundal, Gandhinagar, India",
}


def _build_queries(name: str, location: str) -> list[str]:
    area = location.replace("_", " ")
    queries = [f"{name}, {area}, Ahmedabad, India"]
    if location in AREA_ALIASES:
        queries.append(AREA_ALIASES[location])
    else:
        queries.append(f"{area}, Ahmedabad, India")
    return queries


def _fetch(query: str) -> list[dict] | None:
    url = f"{NOMINATIM_URL}?{urllib.parse.urlencode({'q': query, 'format': 'json', 'limit': 1})}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read())
    except Exception:
        return None


def geocode(name: str, location: str) -> tuple[float, float] | None:
    queries = _build_queries(name, location)
    for i, query in enumerate(queries):
        if i > 0:
            time.sleep(RATE_LIMIT_SECONDS)
        results = _fetch(query)
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    return None


def run(conn) -> dict:
    init_geocoding_schema(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, location FROM restaurants WHERE lat IS NULL")
        rows = cur.fetchall()

    geocoded = 0
    failed = 0
    for row_id, name, location in rows:
        coords = geocode(name, location)
        if coords is None:
            failed += 1
            time.sleep(RATE_LIMIT_SECONDS)
            continue
        lat, lon = coords
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE restaurants SET lat = %s, lon = %s WHERE id = %s",
                (lat, lon, row_id),
            )
        geocoded += 1
        time.sleep(RATE_LIMIT_SECONDS)

    conn.commit()
    return {"geocoded": geocoded, "failed": failed}


if __name__ == "__main__":
    conn = get_connection()
    result = run(conn)
    print(f"geocoded {result['geocoded']} rows, failed {result['failed']}")
