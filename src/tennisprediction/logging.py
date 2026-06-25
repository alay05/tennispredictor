from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar

from tennisprediction.config import Settings, get_settings

__all__ = ["audit_context", "bind_audit_context", "configure_logging"]

_AUDIT_CONTEXT: ContextVar[dict[str, object] | None] = ContextVar(
    "tennisprediction_audit_context",
    default=None,
)
_AUDIT_FIELDS = (
    "run_id",
    "command",
    "stage",
    "artifact_run_id",
    "market_ticker",
    "mapping_state",
    "mapping_confidence",
    "decision_state",
    "rejection_reason",
)
_DEFAULT_AUDIT_VALUES = {field: "-" for field in _AUDIT_FIELDS}
_REDACTED_VALUE = "[REDACTED]"
_SENSITIVE_FIELD_NAMES = {
    "access_key",
    "authorization",
    "auth_header",
    "private_key",
    "private_key_path",
    "request_signed_payload",
}
LOG_FORMAT = (
    "%(asctime)s %(levelname)s [%(name)s] "
    "run_id=%(run_id)s command=%(command)s stage=%(stage)s "
    "artifact_run_id=%(artifact_run_id)s market_ticker=%(market_ticker)s "
    "mapping_state=%(mapping_state)s mapping_confidence=%(mapping_confidence)s "
    "decision_state=%(decision_state)s rejection_reason=%(rejection_reason)s "
    "%(message)s"
)
_STANDARD_LOG_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__)


class _AuditContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = _current_audit_context()
        for field, default_value in _DEFAULT_AUDIT_VALUES.items():
            value = getattr(record, field, None)
            if value in (None, "") and field in context:
                setattr(record, field, context[field])
            elif value in (None, ""):
                setattr(record, field, default_value)

        for field in _SENSITIVE_FIELD_NAMES:
            if hasattr(record, field):
                setattr(record, field, _REDACTED_VALUE)
        return True


class _AuditFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        extra_parts: list[str] = []
        for key in sorted(record.__dict__):
            if key in _STANDARD_LOG_RECORD_FIELDS or key in _AUDIT_FIELDS:
                continue
            if key.startswith("_"):
                continue
            extra_parts.append(f"{key}={record.__dict__[key]}")
        if not extra_parts:
            return rendered
        return f"{rendered} {' '.join(extra_parts)}"


class _AuditLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    def process(
        self,
        msg: object,
        kwargs: Mapping[str, object],
    ) -> tuple[object, dict[str, object]]:
        extras = dict(_current_audit_context())
        if self.extra:
            extras.update(dict(self.extra))

        processed_kwargs = dict(kwargs)
        record_extra = processed_kwargs.get("extra")
        if isinstance(record_extra, Mapping):
            extras.update(dict(record_extra))
        processed_kwargs["extra"] = extras
        return msg, processed_kwargs


@contextmanager
def audit_context(**context: object) -> Iterator[None]:
    merged_context = _current_audit_context()
    merged_context.update({key: value for key, value in context.items() if value is not None})
    token = _AUDIT_CONTEXT.set(merged_context)
    try:
        yield
    finally:
        _AUDIT_CONTEXT.reset(token)


def bind_audit_context(
    logger: logging.Logger,
    /,
    **context: object,
) -> logging.LoggerAdapter[logging.Logger]:
    return _AuditLoggerAdapter(
        logger,
        {key: value for key, value in context.items() if value is not None},
    )


def _current_audit_context() -> dict[str, object]:
    current = _AUDIT_CONTEXT.get()
    if current is None:
        return {}
    return dict(current)


def configure_logging(settings: Settings | None = None) -> logging.Logger:
    resolved_settings = settings or get_settings()
    level = getattr(logging, resolved_settings.log_level)
    formatter = _AuditFormatter(LOG_FORMAT)
    audit_log_path = resolved_settings.reports_dir / "audit" / "operations.log"
    audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_AuditContextFilter())

    file_handler = logging.FileHandler(audit_log_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(_AuditContextFilter())

    logger = logging.getLogger("tennisprediction")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger
