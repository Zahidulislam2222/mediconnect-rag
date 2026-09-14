"""Validated configuration boundary for local HyDE ingestion tooling."""
from dataclasses import dataclass, field
from pathlib import Path
import json
import os


@dataclass(frozen=True)
class HydeSettings:
    api_key: str = field(repr=False)
    model: str
    api_base: str
    api_version: str
    timeout_seconds: int
    content_characters: int
    max_output_tokens: int
    temperature: float
    question_count: int
    prompt: str


def load_settings() -> HydeSettings:
    folder = Path(__file__).resolve().parents[1] / 'config'
    data = json.loads((folder / 'hyde.json').read_text(encoding='utf-8'))
    model = os.environ.get('HYDE_MODEL', '').strip()
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key:
        raise ValueError('GEMINI_API_KEY must be configured before provider use')
    if not model:
        raise ValueError('HYDE_MODEL must be configured before provider use')
    for name in ['timeout_seconds', 'content_characters', 'max_output_tokens', 'question_count']:
        if type(data.get(name)) is not int or data[name] <= 0:
            raise ValueError(f'Invalid HyDE configuration: {name}')
    if not isinstance(data.get('temperature'), (int, float)) or not 0 <= data['temperature'] <= 2:
        raise ValueError('Invalid HyDE temperature')
    for name in ['api_base', 'api_version']:
        if not isinstance(data.get(name), str) or not data[name].strip():
            raise ValueError(f'Invalid HyDE configuration: {name}')
    return HydeSettings(api_key=api_key, model=model, prompt=(folder / 'hyde-prompt.txt').read_text(encoding='utf-8'), **data)
