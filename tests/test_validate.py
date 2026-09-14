import pytest
from app.validate import validate_row, ValidationError

def test_validate_row_parses_good_row():
    row = {
        "name": "Pasta Palace", "cuisine": "italian", "budget": "mid",
        "location": "downtown", "dietary_tags": "vegetarian;gluten_free",
        "description": "Fresh pasta", "rating": "4.5",
    }
    r = validate_row(row)
    assert r.name == "Pasta Palace"
    assert r.budget == "mid"
    assert r.dietary_tags == ["vegetarian", "gluten_free"]
    assert r.rating == 4.5

def test_validate_row_missing_name_raises():
    row = {"name": "", "cuisine": "italian", "budget": "mid", "location": "downtown"}
    with pytest.raises(ValidationError):
        validate_row(row)

def test_validate_row_bad_budget_raises():
    row = {"name": "X", "cuisine": "italian", "budget": "expensive", "location": "downtown"}
    with pytest.raises(ValidationError):
        validate_row(row)

def test_validate_row_defaults_missing_optional_fields():
    row = {"name": "X", "cuisine": "italian", "budget": "budget", "location": "downtown"}
    r = validate_row(row)
    assert r.dietary_tags == []
    assert r.description == ""
    assert r.rating is None
