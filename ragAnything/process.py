"""Explicit, bounded document processing; failures never become success summaries."""
import argparse
import asyncio
import contextlib
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

from settings import QUERY_MODES, ProcessorSettings, load_settings


def document_id(path: Path, input_root: Path, max_file_bytes: int) -> str:
    with path.open('rb') as stream:
        content = stream.read(max_file_bytes + 1)
    if not content or len(content) > max_file_bytes:
        raise ValueError('Document changed after preflight')
    source = path.relative_to(input_root).as_posix().encode('utf-8')
    return 'doc-' + hashlib.sha256(source + b'\0' + content).hexdigest()


def source_files(selected: str | None, directory: bool, settings: ProcessorSettings) -> list[Path]:
    if selected is None:
        return []
    path = Path(selected)
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Symlink source rejected')
    path = path.resolve()
    if not path.is_relative_to(settings.input_root) or (directory and not path.is_dir()):
        raise ValueError('Invalid processor source')
    files = []
    total = 0
    for candidate in path.rglob('*') if directory else [path]:
        if candidate.is_symlink():
            raise ValueError('Symlink source rejected')
        if candidate.is_dir():
            continue
        if candidate.suffix.lower() not in settings.extensions:
            if directory:
                continue
            raise ValueError('Unsupported processor source')
        if not candidate.is_file():
            raise ValueError('Invalid processor source')
        size = candidate.stat().st_size
        total += size
        if not 0 < size <= settings.max_file_bytes or total > settings.max_total_bytes:
            raise ValueError('Processor source byte limit exceeded')
        files.append(candidate)
        if len(files) > settings.max_files:
            raise ValueError('Processor source count limit exceeded')
    if not files:
        raise ValueError('No supported current documents')
    return sorted(files)


@contextlib.contextmanager
def private_sdk_output():
    """SDK logs can include source content/provider errors; emit our safe summary only."""
    previous = logging.root.manager.disable
    with open(os.devnull, 'w', encoding='utf-8') as sink:
        logging.disable(logging.CRITICAL)
        try:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                yield
        finally:
            logging.disable(previous)


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAG-Anything Document Processor")
    parser.add_argument('file', nargs='?')
    parser.add_argument('--dir')
    parser.add_argument('--query', '-q')
    parser.add_argument('--mode', choices=sorted(QUERY_MODES))
    execution = parser.add_mutually_exclusive_group(required=True)
    execution.add_argument('--plan', action='store_true')
    execution.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    completed = 0
    attempted = 0
    stage = 'PREFLIGHT'
    error_logger = logging.getLogger('mediconnect.processor.cli')
    error_logger.handlers = [logging.StreamHandler(sys.stderr)]
    error_logger.propagate = False
    error_logger.setLevel(logging.ERROR)
    try:
        if args.file and args.dir or not any([args.file, args.dir, args.query]):
            raise ValueError('Choose one document source or a query')
        settings = load_settings(execute=args.execute)
        if args.query is not None and (not args.query.strip() or len(args.query) > settings.max_query_characters):
            raise ValueError('Invalid processor query')
        files = source_files(args.file or args.dir, bool(args.dir), settings)
        if args.plan:
            print(json.dumps({'status': 'PLANNED', 'documents': len(files), 'query': args.query is not None,
                              'provider_calls': 0}))
            return 0
        with private_sdk_output():
            stage = 'INITIALIZATION'
            from config import create_rag
            runtime = create_rag(settings)
            try:
                await runtime.initialize()
                stage = 'PROCESSING'
                for path in files:
                    attempted += 1
                    relative = path.relative_to(settings.input_root)
                    output = settings.output_dir / relative.parent / relative.name
                    identity = document_id(path, settings.input_root, settings.max_file_bytes)
                    await runtime.process_document(str(path), str(output), identity, settings.parse_method)
                    completed += 1
                answer = None
                if args.query is not None:
                    stage = 'QUERY'
                    answer = await runtime.query(args.query, mode=args.mode or settings.query_mode)
                    if not isinstance(answer, str) or not answer.strip():
                        raise RuntimeError('Query result unavailable')
                stage = 'FINALIZATION'
            finally:
                await runtime.finalize()
        result = {'status': 'PROCESSED', 'attempted': attempted, 'completed': completed}
        if answer is not None:
            result.update(status='ANSWERED', answer=answer)
        print(json.dumps(result))
        return 0
    except Exception:
        # The CLI boundary logs only our metadata, never exception text/tracebacks.
        error_logger.exception(json.dumps({'status': 'FAILED', 'stage': stage, 'attempted': attempted,
                               'completed': completed, 'automatic_retry': False}), exc_info=False)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
