import json
import time
import urllib.parse
import urllib.request

from app.db import get_connection, init_geocoding_schema

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "restaurant-rag-chatbot/1.0 (internal tool, not for redistribution)"
RATE_LIMIT_SECONDS = 1.1


def geocode(name: str, location: str) -> tuple[float, float] | None:
    query = f"{name}, {location}, Ahmedabad, India"
    url = f"{NOMINATIM_URL}?{urllib.parse.urlencode({'q': query, 'format': 'json', 'limit': 1})}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            results = json.loads(response.read())
    except Exception:
        return None
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


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
