from app.ingest import ingest_csv

CSV_CONTENT = """name,cuisine,budget,location,dietary_tags,description,rating
Good Place,italian,mid,downtown,vegetarian,Nice pasta spot,4.5
Bad Place,mexican,expensive,uptown,none,Bad budget value,4.0
,chinese,budget,eastside,none,Missing name,3.5
"""

def test_ingest_skips_invalid_rows(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)

    result = ingest_csv(str(csv_path), conn=db_conn)

    assert result["inserted"] == 1
    assert len(result["skipped"]) == 2
    with db_conn.cursor() as cur:
        cur.execute("SELECT name FROM restaurants")
        rows = cur.fetchall()
    assert rows == [("Good Place",)]
