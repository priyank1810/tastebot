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


def search(
    conn, query: str, top_k: int = 6, filters: dict | None = None
) -> list[RetrievedRestaurant]:
    filters = filters or {}
    query_vector = Vector(embed(query)).to_numpy()

    where_clauses = []
    where_params = []
    if filters.get("cuisine"):
        where_clauses.append("cuisine = ANY(%s)")
        where_params.append(filters["cuisine"])
    if filters.get("budget"):
        where_clauses.append("budget = ANY(%s)")
        where_params.append(filters["budget"])
    if filters.get("location"):
        where_clauses.append("location = ANY(%s)")
        where_params.append(filters["location"])
    if filters.get("dietary_tags"):
        where_clauses.append("dietary_tags && %s")
        where_params.append(filters["dietary_tags"])

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT name, cuisine, budget, location, dietary_tags, description, rating,
                   embedding <=> %s AS distance
            FROM restaurants
            {where_sql}
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            [query_vector, *where_params, query_vector, top_k],
        )
        rows = cur.fetchall()

    return [
        RetrievedRestaurant(
            name=row[0], cuisine=row[1], budget=row[2], location=row[3],
            dietary_tags=row[4] or [], description=row[5],
            rating=float(row[6]) if row[6] is not None else None,
            distance=float(row[7]),
        )
        for row in rows
    ]


def get_filter_options(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT cuisine FROM restaurants ORDER BY cuisine")
        cuisines = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT budget FROM restaurants ORDER BY budget")
        budgets = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT location FROM restaurants ORDER BY location")
        locations = [r[0] for r in cur.fetchall()]
        cur.execute(
            "SELECT DISTINCT unnest(dietary_tags) AS tag FROM restaurants ORDER BY tag"
        )
        dietary_tags = [r[0] for r in cur.fetchall()]
    return {
        "cuisine": cuisines,
        "budget": budgets,
        "location": locations,
        "dietary_tags": dietary_tags,
    }
