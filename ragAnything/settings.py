"""Single validated configuration boundary for the optional document processor."""
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

# These names are defined by the pinned RAG-Anything parser/query contracts.
QUERY_MODES = frozenset({'naive', 'local', 'global', 'hybrid'})
PARSERS = frozenset({'mineru', 'docling', 'paddleocr'})
PARSE_METHODS = frozenset({'auto', 'ocr', 'txt'})
IMAGE_MIME_TYPES = frozenset({'image/png', 'image/jpeg', 'image/webp', 'image/gif'})


@dataclass(frozen=True)
class ProviderSettings:
    base_url: str
    api_version: str
    timeout_ms: int
    max_output_tokens: int
    temperature: float
    max_response_characters: int
    max_text_characters: int
    max_image_bytes: int
    max_embedding_batch: int
    image_mime_type: str


@dataclass(frozen=True)
class ProcessorSettings:
    input_root: Path
    working_dir: Path
    output_dir: Path
    parser: str
    parse_method: str
    query_mode: str
    extensions: tuple[str, ...]
    max_files: int
    max_file_bytes: int
    max_total_bytes: int
    max_query_characters: int
    embedding_max_tokens: int
    tokenizer_model: str
    enable_image_processing: bool
    enable_table_processing: bool
    enable_equation_processing: bool
    api_key: str = field(repr=False)
    llm_model: str
    embedding_model: str
    embedding_dim: int
    provider: ProviderSettings


def load_settings(env: Mapping[str, str] | None = None, *, execute: bool = True) -> ProcessorSettings:
    env = os.environ if env is None else env
    policy = Path(env.get('RAGANYTHING_POLICY_FILE', str(Path(__file__).with_name('processor.json'))))
    data = json.loads(policy.read_text(encoding='utf-8'))
    values: dict[str, Any] = {}
    for name in ['max_files', 'max_file_bytes', 'max_total_bytes', 'max_query_characters', 'embedding_max_tokens']:
        value = data[name]
        if type(value) is not int or value <= 0:
            raise ValueError('Invalid processor limit')
        values[name] = value
    for name in ['enable_image_processing', 'enable_table_processing', 'enable_equation_processing']:
        if type(data[name]) is not bool:
            raise ValueError('Invalid processor feature flag')
        values[name] = data[name]
    for name, allowed in [('parser', PARSERS), ('parse_method', PARSE_METHODS), ('query_mode', QUERY_MODES)]:
        if data[name] not in allowed:
            raise ValueError('Invalid processor mode')
        values[name] = data[name]
    tokenizer = data['tokenizer_model']
    if not isinstance(tokenizer, str) or not tokenizer.strip() or any(c.isspace() for c in tokenizer):
        raise ValueError('Invalid tokenizer configuration')
    values['tokenizer_model'] = tokenizer
    extensions = data['extensions']
    if (not isinstance(extensions, list) or not extensions
            or any(not isinstance(e, str) or not e.startswith('.') or not e[1:].isalnum() for e in extensions)
            or len(set(extensions)) != len(extensions)):
        raise ValueError('Invalid processor extensions')
    values['extensions'] = tuple(e.lower() for e in extensions)
    for name in ['input_root', 'working_dir', 'output_dir']:
        path = Path(env.get('RAGANYTHING_' + name.upper(), data[name]))
        if not path.is_absolute() or any(parent.is_symlink() for parent in [path, *path.parents]):
            raise ValueError('Processor roots must be absolute and have no symlinks')
        values[name] = path.resolve()
    roots = [values[name] for name in ['input_root', 'working_dir', 'output_dir']]
    if any(a.is_relative_to(b) for i, a in enumerate(roots) for j, b in enumerate(roots) if i != j):
        raise ValueError('Processor input/output/storage roots must be separate')
    for field_name, env_name in [('api_key', 'GEMINI_API_KEY'), ('llm_model', 'LLM_MODEL'), ('embedding_model', 'EMBEDDING_MODEL')]:
        value = env.get(env_name, '').strip()
        if (execute and not value) or any(c in value for c in '\r\n\0'):
            raise ValueError('Missing or invalid processor provider configuration')
        values[field_name] = value
    dimension = env.get('EMBEDDING_DIM', '')
    if dimension and (not dimension.isdecimal() or int(dimension) <= 0):
        raise ValueError('Invalid processor embedding dimension')
    if execute and not dimension:
        raise ValueError('Missing processor embedding dimension')
    values['embedding_dim'] = int(dimension) if dimension else 0
    provider = dict(data['provider'])
    provider['base_url'] = env.get('RAGANYTHING_API_BASE', provider['base_url'])
    provider['api_version'] = env.get('RAGANYTHING_API_VERSION', provider['api_version'])
    endpoint = urlsplit(provider['base_url'])
    if (endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.password
            or endpoint.query or endpoint.fragment or endpoint.path not in ['', '/']
            or any(c.isspace() for c in provider['base_url'])):
        raise ValueError('Invalid processor provider origin')
    if not re.fullmatch(r'v[0-9]+(?:alpha|beta)?', provider['api_version']):
        raise ValueError('Invalid processor API version')
    for name in ['timeout_ms', 'max_output_tokens', 'max_response_characters', 'max_text_characters',
                 'max_image_bytes', 'max_embedding_batch']:
        if type(provider[name]) is not int or provider[name] <= 0:
            raise ValueError('Invalid processor provider limit')
    if type(provider['temperature']) not in [int, float] or not 0 <= provider['temperature'] <= 2:
        raise ValueError('Invalid processor temperature')
    if provider['image_mime_type'] not in IMAGE_MIME_TYPES:
        raise ValueError('Invalid processor image type')
    values['provider'] = ProviderSettings(**provider)
    return ProcessorSettings(**values)
