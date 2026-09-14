import csv
import sys

from pgvector.utils import Vector

from app.db import get_connection, init_schema
from app.embeddings import embed
from app.validate import Restaurant, ValidationError, validate_row


def build_text(r: Restaurant) -> str:
    tags = ", ".join(r.dietary_tags) if r.dietary_tags else "none"
    return (
        f"{r.name} serves {r.cuisine} cuisine in {r.location}. "
        f"Budget: {r.budget}. Dietary: {tags}. {r.description}"
    )


def ingest_csv(path: str, conn=None) -> dict:
    conn = conn or get_connection()
    init_schema(conn)
    inserted = 0
    skipped = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with conn.cursor() as cur:
            for line_no, row in enumerate(reader, start=2):  # header is line 1
                try:
                    r = validate_row(row)
                except ValidationError as e:
                    skipped.append((line_no, str(e)))
                    continue

                text = build_text(r)
                vector = embed(text)
                cur.execute(
                    """
                    INSERT INTO restaurants
                        (name, cuisine, budget, location, dietary_tags, description, rating, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (r.name, r.cuisine, r.budget, r.location, r.dietary_tags,
                     r.description, r.rating, Vector(vector).to_numpy()),
                )
                inserted += 1

    conn.commit()
    for line_no, reason in skipped:
        print(f"skipped row {line_no}: {reason}", file=sys.stderr)
    return {"inserted": inserted, "skipped": skipped}


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/restaurants.csv"
    result = ingest_csv(csv_path)
    print(f"inserted {result['inserted']} rows, skipped {len(result['skipped'])}")
