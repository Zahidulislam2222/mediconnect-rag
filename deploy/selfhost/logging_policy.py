"""Discard request-derived text before it reaches any Python log handler."""
import logging
from collections.abc import Callable
from typing import Any

# Fixed security event label: never interpolate upstream messages or exceptions.
RUNTIME_EVENT_LABEL = 'RAG runtime event'


def install_private_logging() -> None:
    original = logging.getLogRecordFactory()

    def safe_record(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = original(*args, **kwargs)
        record.msg = RUNTIME_EVENT_LABEL
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return record

    logging.setLogRecordFactory(safe_record)


def without_access_logging(configure: Callable[[], None]) -> Callable[[], None]:
    def apply() -> None:
        configure()
        logging.getLogger('uvicorn.access').disabled = True
    return apply
