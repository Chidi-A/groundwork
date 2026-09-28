from openai import OpenAI

from app.core.config import settings

_client: OpenAI | None = None


def get_embedding_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def insight_embedding_input(text: str, source_quote: str | None = None) -> str:
    quote = (source_quote or "").strip()
    if quote:
        return f"{text.strip()}\n\n{quote}"
    return text.strip()


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    response = get_embedding_client().embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )
    by_index = {item.index: item.embedding for item in response.data}
    return [by_index[i] for i in range(len(texts))]