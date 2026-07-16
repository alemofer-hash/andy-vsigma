from __future__ import annotations

import logging
from typing import Any, Mapping


def handle_user_error(exc: Exception, correlation_id: str, is_prod: bool) -> str:
    if is_prod:
        return f"Ocorreu um erro. ID: {correlation_id}"
    msg = str(exc).strip() or exc.__class__.__name__
    if len(msg) > 240:
        msg = msg[:240] + "..."
    return f"Erro: {msg} | ID: {correlation_id}"


def log_exception(exc: Exception, correlation_id: str, context: Mapping[str, Any] | None = None) -> None:
    ctx = dict(context or {})
    logging.exception("cid=%s context=%s error=%s", correlation_id, ctx, exc)
