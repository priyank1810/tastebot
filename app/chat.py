from openai import AzureOpenAI

from app.config import settings
from app.retrieval import RetrievedRestaurant

SYSTEM_PROMPT = (
    "You are a restaurant recommendation assistant. Recommend restaurants "
    "ONLY from the CANDIDATES list below. If none fit the user's request well, "
    "say so plainly and offer the closest options instead of inventing a fit. "
    "Never mention a restaurant that is not in CANDIDATES."
)


def build_context(candidates: list[RetrievedRestaurant]) -> str:
    if not candidates:
        return "CANDIDATES: (none found)"
    lines = ["CANDIDATES:"]
    for c in candidates:
        tags = ", ".join(c.dietary_tags) if c.dietary_tags else "none"
        lines.append(
            f"- {c.name} | cuisine: {c.cuisine} | budget: {c.budget} | "
            f"location: {c.location} | dietary: {tags} | rating: {c.rating}"
        )
    return "\n".join(lines)


def get_reply(
    history: list[dict],
    user_message: str,
    candidates: list[RetrievedRestaurant],
    client=None,
) -> str:
    client = client or AzureOpenAI(
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
    )
    context = build_context(candidates)
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": f"{context}\n\nUser: {user_message}"}]
    )
    response = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        max_tokens=500,
        messages=messages,
    )
    return response.choices[0].message.content
