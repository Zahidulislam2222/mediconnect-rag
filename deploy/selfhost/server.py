"""Keep the pinned server's local embeddings bounded; no alternate providers."""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from logging_policy import install_private_logging, without_access_logging
from runtime_settings import RuntimeSettings


def bounded_embedding(function: Callable[..., Awaitable[Any]], settings: RuntimeSettings) -> Callable[..., Awaitable[Any]]:
    async def embed(texts: list[str], embed_model: str, **kwargs: Any) -> Any:
        if kwargs.get('host') != settings.provider_origin:
            raise ValueError('Unexpected embedding origin')
        kwargs['timeout'] = settings.embedding_timeout_seconds
        async with asyncio.timeout(settings.embedding_timeout_seconds):
            return await function(texts, embed_model, **kwargs)
    return embed


def main() -> None:
    settings = RuntimeSettings.from_environment()
    install_private_logging()
    from lightrag.llm import ollama
    ollama.ollama_embed = bounded_embedding(ollama.ollama_embed, settings)
    from lightrag.api import lightrag_server
    lightrag_server.configure_logging = without_access_logging(lightrag_server.configure_logging)
    lightrag_server.main()


if __name__ == '__main__':
    main()
