from dataclasses import dataclass

ALLOWED_BUDGETS = {"budget", "mid", "premium"}
REQUIRED_FIELDS = ["name", "cuisine", "budget", "location"]


@dataclass
class Restaurant:
    name: str
    cuisine: str
    budget: str
    location: str
    dietary_tags: list[str]
    description: str
    rating: float | None


class ValidationError(Exception):
    pass


def validate_row(row: dict) -> Restaurant:
    for field in REQUIRED_FIELDS:
        if not (row.get(field) or "").strip():
            raise ValidationError(f"missing required field: {field}")

    budget = row["budget"].strip().lower()
    if budget not in ALLOWED_BUDGETS:
        raise ValidationError(f"invalid budget: {row['budget']!r}")

    dietary_raw = row.get("dietary_tags") or ""
    dietary_tags = [t.strip() for t in dietary_raw.split(";") if t.strip()]

    rating_raw = (row.get("rating") or "").strip()
    rating = float(rating_raw) if rating_raw else None

    return Restaurant(
        name=row["name"].strip(),
        cuisine=row["cuisine"].strip(),
        budget=budget,
        location=row["location"].strip(),
        dietary_tags=dietary_tags,
        description=(row.get("description") or "").strip(),
        rating=rating,
    )
