from app.ingest import ingest_csv
from app.retrieval import get_filter_options, search

CSV_CONTENT = """name,cuisine,budget,location,dietary_tags,description,rating
Pasta Palace,italian,mid,downtown,vegetarian,Fresh handmade pasta and pizza,4.5
Sushi Spot,japanese,premium,downtown,pescatarian,Fresh nigiri and sashimi,4.7
Taco Town,mexican,budget,eastside,gluten_free,Street tacos and salsa,4.0
Curry Corner,indian,mid,southside,vegetarian;vegan,Rich curries and biryani,4.3
Burger Joint,american,budget,southside,none,Smash burgers and fries,4.1
Vegan Bowl,vegan,mid,uptown,vegan;gluten_free,Plant-based bowls,4.4
Ramen House,japanese,budget,downtown,none,Tonkotsu ramen bowls,4.2
Pizza Place,italian,budget,eastside,vegetarian,Wood-fired pizza slices,4.0
"""

def test_search_returns_top_six_ordered_by_distance(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    results = search(db_conn, "cheap italian pizza", top_k=6)

    assert len(results) == 6
    distances = [r.distance for r in results]
    assert distances == sorted(distances)
    names = [r.name for r in results]
    assert "Pizza Place" in names[:3] or "Pasta Palace" in names[:3]
    # rating must be a plain float (JSON-serializable), not a Decimal
    assert all(isinstance(r.rating, float) for r in results)


def test_search_filters_by_cuisine(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    results = search(db_conn, "something tasty", top_k=6, filters={"cuisine": ["mexican"]})

    assert len(results) == 1
    assert results[0].name == "Taco Town"


def test_search_filters_by_budget_and_dietary_tags(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    results = search(
        db_conn, "something tasty", top_k=6,
        filters={"budget": ["mid"], "dietary_tags": ["vegan"]},
    )

    names = {r.name for r in results}
    assert names == {"Curry Corner", "Vegan Bowl"}


def test_search_with_no_matching_filters_returns_empty(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    results = search(db_conn, "anything", top_k=6, filters={"cuisine": ["klingon"]})

    assert results == []


def test_search_with_no_filters_arg_behaves_as_before(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    results = search(db_conn, "cheap italian pizza", top_k=6)

    assert len(results) == 6


def test_get_filter_options_returns_distinct_values(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    options = get_filter_options(db_conn)

    assert set(options.keys()) == {"cuisine", "budget", "location", "dietary_tags"}
    assert "italian" in options["cuisine"]
    assert "mexican" in options["cuisine"]
    assert "mid" in options["budget"]
    assert "downtown" in options["location"]
    assert "vegetarian" in options["dietary_tags"]
    assert "vegan" in options["dietary_tags"]
