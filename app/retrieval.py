from dataclasses import dataclass

from pgvector.utils import Vector

from app.embeddings import embed


@dataclass
class RetrievedRestaurant:
    name: str
    cuisine: str
    budget: str
    location: str
    dietary_tags: list[str]
    description: str
    rating: float | None
    distance: float


def search(conn, query: str, top_k: int = 6) -> list[RetrievedRestaurant]:
    query_vector = Vector(embed(query)).to_numpy()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT name, cuisine, budget, location, dietary_tags, description, rating,
                   embedding <=> %s AS distance
            FROM restaurants
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (query_vector, query_vector, top_k),
        )
        rows = cur.fetchall()

    return [
        RetrievedRestaurant(
            name=row[0], cuisine=row[1], budget=row[2], location=row[3],
            dietary_tags=row[4] or [], description=row[5], rating=row[6],
            distance=row[7],
        )
        for row in rows
    ]
