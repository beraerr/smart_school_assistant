"""Sorgu olayları için tek satır JSON log.

Yazılan alanlar sabittir. Kimlik doğrulama jetonu ve API anahtarı bu kayda girmez.
"""

import json
import logging
from typing import Any

QUERY_LOGGER_NAME = "school.query"

query_logger = logging.getLogger(QUERY_LOGGER_NAME)


def configure_logging() -> None:
    """JSON satırını olduğu gibi yazan tek bir konsol işleyicisi kurar."""
    query_logger.setLevel(logging.INFO)
    if not any(getattr(handler, "_school_query_json", False) for handler in query_logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler._school_query_json = True  # type: ignore[attr-defined]
        query_logger.addHandler(handler)
    query_logger.propagate = False


def log_query(
    *,
    event: str,
    user: str,
    role: str,
    row_count: int,
    llm_calls: int,
    tool_calls: int,
    llm_ms: int,
    db_ms: int,
    rate_limited: bool,
    sql: list[str] | None = None,
) -> None:
    """Tek bir sorgu olayını JSON olarak yazar.

    Cevap metni ve kimlik doğrulama jetonu bu kayda girmez.
    sql yalnızca çalışan sorgular varsa eklenir.
    """
    payload: dict[str, Any] = {
        "event": event,
        "user": user,
        "role": role,
        "row_count": row_count,
        "llm_calls": llm_calls,
        "tool_calls": tool_calls,
        "llm_ms": llm_ms,
        "db_ms": db_ms,
        "rate_limited": rate_limited,
    }
    if sql:
        payload["sql"] = sql
    query_logger.info(json.dumps(payload, ensure_ascii=False))


configure_logging()
