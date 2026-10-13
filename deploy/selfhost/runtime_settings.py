"""Typed environment boundary for the pinned local-provider runtime patch."""
import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class RuntimeSettings:
    embedding_timeout_seconds: int
    provider_origin: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> 'RuntimeSettings':
        env = os.environ if environment is None else environment
        raw = env.get('SELFHOST_EMBEDDING_TIMEOUT_SECONDS', '')
        if not raw.isdecimal() or int(raw) <= 0:
            raise ValueError('A positive embedding deadline is required')
        origin = env.get('EMBEDDING_BINDING_HOST', '')
        parsed = urlsplit(origin)
        if any(c.isspace() for c in origin) or parsed.port is None or not 0 < parsed.port < 65536:
            raise ValueError('A valid local model port is required')
        if (parsed.scheme != 'http' or parsed.hostname != 'ollama' or parsed.username or parsed.password
                or parsed.path not in ['', '/'] or parsed.query or parsed.fragment):
            raise ValueError('Embedding requests must use the local model service')
        if env.get('LLM_BINDING') != 'ollama' or env.get('EMBEDDING_BINDING') != 'ollama':
            raise ValueError('Only local model bindings are permitted')
        if env.get('LLM_BINDING_HOST') != origin:
            raise ValueError('Local model origins must agree')
        if not env.get('AUTH_ACCOUNTS') or not env.get('LIGHTRAG_API_KEY') or not env.get('TOKEN_SECRET'):
            raise ValueError('Authenticated workspace configuration is required')
        return cls(int(raw), origin)
