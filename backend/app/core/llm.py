from anthropic import Anthropic, AsyncAnthropic

from app.core.config import settings

_async_client: AsyncAnthropic | None = None
_sync_client: Anthropic | None = None


def get_client() -> AsyncAnthropic:
    global _async_client
    if _async_client is None:
        _async_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _async_client


def get_sync_client() -> Anthropic:
    global _sync_client
    if _sync_client is None:
        _sync_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _sync_client