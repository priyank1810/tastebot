from app import geocode
from app.ingest import ingest_csv

CSV_CONTENT = """name,cuisine,budget,location,dietary_tags,description,rating
Test Cafe,cafe,mid,navrangpura,vegetarian,A cafe.,
Unfindable Place,cafe,mid,nowhereville,vegetarian,Will not geocode.,
"""


def fake_geocode(name, location):
    if name == "Test Cafe":
        return (23.03, 72.56)
    return None


def test_run_updates_lat_lon_and_skips_failures(db_conn, tmp_path, monkeypatch):
    monkeypatch.setattr(geocode, "geocode", fake_geocode)
    monkeypatch.setattr(geocode, "RATE_LIMIT_SECONDS", 0)
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    result = geocode.run(db_conn)

    assert result == {"geocoded": 1, "failed": 1}
    with db_conn.cursor() as cur:
        cur.execute("SELECT name, lat, lon FROM restaurants ORDER BY name")
        rows = cur.fetchall()
    assert rows == [
        ("Test Cafe", 23.03, 72.56),
        ("Unfindable Place", None, None),
    ]


def test_run_skips_already_geocoded_rows(db_conn, tmp_path, monkeypatch):
    calls = []

    def counting_geocode(name, location):
        calls.append(name)
        return (1.0, 2.0)

    monkeypatch.setattr(geocode, "geocode", counting_geocode)
    monkeypatch.setattr(geocode, "RATE_LIMIT_SECONDS", 0)
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    geocode.run(db_conn)
    calls.clear()
    result = geocode.run(db_conn)

    assert result == {"geocoded": 0, "failed": 0}
    assert calls == []
