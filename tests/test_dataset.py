from app.ingest import ingest_csv


def test_sample_dataset_ingests_with_no_skipped_rows(db_conn):
    result = ingest_csv("data/restaurants.csv", conn=db_conn)
    assert result["skipped"] == []
    assert result["inserted"] == 30
