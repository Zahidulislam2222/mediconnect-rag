"""Bounded current-source ingestion. Acceptance is not completed background indexing."""
import argparse
from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import time
from typing import TypedDict

import requests

from ingestion_config import IngestionSettings, load_settings
from ingestion_environment import merged_environment
from ingestion_protocol import API_KEY_HEADER, TEXT_ROUTE, accepted, text_payload


@dataclass(frozen=True)
class Document:
    source: str
    text: str


class Summary(TypedDict):
    status: str
    planned: int
    accepted: int
    stage: str


def preflight(settings: IngestionSettings) -> list[Document]:
    documents: list[Document] = []
    identities = set()
    total = 0
    def enumeration_failed(error: OSError) -> None:
        raise error

    for source in settings.sources:
        if not source.is_dir():
            raise ValueError('Missing ingestion source')
        count_before = len(documents)
        for directory, folders, names in os.walk(source, followlinks=False, onerror=enumeration_failed):
            parent = Path(directory)
            if any((parent / name).is_symlink() for name in folders):
                raise ValueError('Symlink directory in ingestion source')
            folders[:] = sorted(name for name in folders if settings.output is None
                                or not (parent / name).is_relative_to(settings.output))
            for name in sorted(names):
                path = parent / name
                if path.suffix != '.md':
                    continue
                before = path.lstat()
                if not stat.S_ISREG(before.st_mode) or before.st_size < 1 or before.st_size > settings.max_file_bytes:
                    raise ValueError('Invalid source file')
                identity = path.relative_to(settings.root).as_posix()
                if identity in identities or len(documents) >= settings.max_files:
                    raise ValueError('Duplicate source or too many documents')
                with path.open('rb') as stream:
                    opened = os.fstat(stream.fileno())
                    raw = stream.read(settings.max_file_bytes + 1)
                    after = os.fstat(stream.fileno())
                signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
                if signature(before) != signature(opened) or signature(opened) != signature(after) or len(raw) != before.st_size:
                    raise ValueError('Source changed during preflight')
                total += len(raw)
                text = raw.decode('utf-8')
                if not text.strip() or total > settings.max_total_bytes:
                    raise ValueError('Empty source or aggregate limit exceeded')
                documents.append(Document(identity, text))
                identities.add(identity)
        if len(documents) == count_before:
            raise ValueError('Empty required ingestion source')
    return sorted(documents, key=lambda item: item.source)


def augment(documents: list[Document], settings: IngestionSettings) -> list[Document]:
    # Reuse the existing HTTPS generation boundary; only current preflight bytes are sent.
    spec = importlib.util.spec_from_file_location('hyde_generation', Path(__file__).with_name('generate-questions.py'))
    if spec is None or spec.loader is None:
        raise ValueError('Generation module unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hyde = module.load_settings()
    generated = []
    total = 0
    for document in documents:
        questions = module.generate_questions(document.text, document.source, hyde.api_key, hyde.model)
        if not questions:
            raise ValueError('Generation failed')
        text = document.text + hyde.questions_heading + ''.join(f'- {q}\n' for q in questions)
        size = len(text.encode('utf-8'))
        total += size
        if size > settings.max_file_bytes or total > settings.max_total_bytes:
            raise ValueError('Generated content exceeds limits')
        generated.append(Document(document.source, text))
        time.sleep(hyde.pacing_seconds)
    # No existing output is changed until every generation has succeeded.
    if settings.output is None:
        raise ValueError('HyDE output is not configured')
    for document in generated:
        target = settings.output / document.source
        # Operator owns a quiescent source/output tree; never follow existing symlinks.
        for path in (target, *target.parents):
            if path.is_symlink():
                raise ValueError('Symlink output is forbidden')
            if path == settings.root:
                break
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                         prefix='.augmentation-', delete=False) as stream:
            stream.write(document.text)
            temporary = Path(stream.name)
        temporary.replace(target)
    return generated


def submit(session: requests.Session, settings: IngestionSettings, document: Document) -> None:
    with session.post(settings.base_url + TEXT_ROUTE,
                      json=text_payload(document.text, document.source),
                      headers={API_KEY_HEADER: settings.api_key},
                      timeout=settings.timeout_seconds, allow_redirects=False, stream=True) as response:
        if response.status_code != 200:
            raise ValueError('Upload rejected')
        raw = bytearray()
        for chunk in response.iter_content(chunk_size=settings.max_response_bytes + 1):
            raw.extend(chunk)
            if len(raw) > settings.max_response_bytes:
                raise ValueError('Oversized response')
        if not accepted(json.loads(raw)):
            raise ValueError('Upload not acknowledged')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, choices=('medical', 'codebase', 'hyde'))
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--plan', action='store_true')
    modes.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    state: Summary = {'status': 'FAILED', 'planned': 0, 'accepted': 0, 'stage': 'CONFIG'}
    try:
        root = Path(__file__).resolve().parents[1]
        environment = merged_environment(root / 'configs/.env', dict(os.environ))
        settings = load_settings(root, args.profile, environment, args.execute)
        state['stage'] = 'PREFLIGHT'
        documents = preflight(settings)
        state['planned'] = len(documents)
        if args.plan:
            state['status'] = 'PLAN_READY'
        else:
            if args.profile == 'hyde':
                state['stage'] = 'GENERATION'
                os.environ.update(environment)
                documents = augment(documents, settings)
            state['stage'] = 'SUBMISSION'
            with requests.Session() as session:
                # Avoid implicit .netrc credentials and environment proxies for private content.
                session.trust_env = False
                for document in documents:
                    submit(session, settings, document)
                    state['accepted'] += 1
            state['status'] = 'ACCEPTED'
        state['stage'] = 'COMPLETE'
    except (OSError, ValueError, KeyError, TypeError, requests.RequestException):
        # Exception bodies can contain private content or credentials.
        state['status'] = 'FAILED'
    print(json.dumps(state))
    return 0 if state['status'] in ('PLAN_READY', 'ACCEPTED') else 1


if __name__ == '__main__':
    raise SystemExit(main())
