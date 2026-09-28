from unittest.mock import MagicMock, patch

from app.core.embeddings import embed_texts, insight_embedding_input


def test_insight_embedding_input_includes_quote() -> None:
    assert insight_embedding_input("pain", "verbatim") == "pain\n\nverbatim"
    assert insight_embedding_input("pain", None) == "pain"
    assert insight_embedding_input("pain", "  ") == "pain"


@patch("app.core.embeddings.get_embedding_client")
def test_embed_texts_returns_in_input_order(mock_client: MagicMock) -> None:
    item0 = MagicMock(index=1, embedding=[0.2])
    item1 = MagicMock(index=0, embedding=[0.1])
    mock_client.return_value.embeddings.create.return_value.data = [item0, item1]
    with patch("app.core.embeddings.settings") as settings:
        settings.OPENAI_API_KEY = "test"
        settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        settings.EMBEDDING_DIMENSIONS = 1536
        assert embed_texts(["a", "b"]) == [[0.1], [0.2]]