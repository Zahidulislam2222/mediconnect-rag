"""Typed, validated operator configuration; no network or secret logging."""
from dataclasses import dataclass, field
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class IngestionSettings:
    root: Path
    sources: tuple[Path, ...]
    output: Path | None
    base_url: str
    api_key: str = field(repr=False)
    timeout_seconds: int
    max_files: int
    max_file_bytes: int
    max_total_bytes: int
    max_response_bytes: int


def contained(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or path == Path('.'):
        raise ValueError('Invalid relative ingestion path')
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlinks are not ingestion sources or outputs')
    if not current.resolve().is_relative_to(root):
        raise ValueError('Ingestion path escapes project')
    return current


def load_settings(root: Path, profile: str, env: dict[str, str], execute: bool) -> IngestionSettings:
    root = root.resolve()
    data = json.loads((root / 'config/ingestion.json').read_text(encoding='utf-8'))
    selected = data['profiles'][profile]
    values = {}
    for key in ('timeout_seconds', 'max_files', 'max_file_bytes', 'max_total_bytes', 'max_response_bytes'):
        value = data[key]
        if type(value) is not int or value <= 0:
            raise ValueError('Invalid ingestion limit')
        values[key] = value
    names = selected['sources']
    if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
        raise ValueError('Invalid ingestion sources')
    sources = tuple(contained(root, name) for name in names)
    if len(set(sources)) != len(sources):
        raise ValueError('Duplicate ingestion sources')
    output = contained(root, selected['output']) if selected['output'] else None
    if output and any(source.is_relative_to(output) for source in sources):
        raise ValueError('Output cannot contain a source')
    url = env.get(selected['target_environment'], '').strip().rstrip('/')
    endpoint = urlsplit(url)
    loopback = endpoint.hostname == 'localhost'
    if endpoint.hostname and not loopback:
        try:
            loopback = ipaddress.ip_address(endpoint.hostname).is_loopback
        except ValueError:
            loopback = False
    if (not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query
            or endpoint.fragment or endpoint.path or any(c.isspace() for c in url)
            or (endpoint.scheme != 'https' and not (endpoint.scheme == 'http' and loopback))):
        raise ValueError('Configure an HTTPS or loopback ingestion origin')
    key = env.get('LIGHTRAG_API_KEY', '')
    if (execute and not key.strip()) or any(c in key for c in '\r\n\0'):
        raise ValueError('Configure a valid LightRAG API key')
    return IngestionSettings(root, sources, output, url, key, **values)
