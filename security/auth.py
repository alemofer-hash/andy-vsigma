from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from config import AppConfig


ALLOWED_ROLES = {"viewer", "exporter", "admin"}


@dataclass(frozen=True)
class UserContext:
    user_id: str
    role: str
    can_export: bool
    is_admin: bool
    source: str


def _sanitize_role(role: str) -> str:
    r = str(role or "").strip().lower()
    return r if r in ALLOWED_ROLES else "viewer"


def _header_value(headers: Mapping[str, str], key: str) -> str:
    target = key.lower()
    for hk, hv in headers.items():
        if str(hk).lower() == target:
            return str(hv)
    return ""


def get_user_context(config: AppConfig, headers: Mapping[str, str] | None = None) -> UserContext:
    headers = headers or {}
    if config.is_prod:
        role = _sanitize_role(_header_value(headers, config.auth_role_header))
        user = _header_value(headers, config.auth_user_header) or "unknown"
        # Fail-closed: sem header de role valido, exportacao fica bloqueada.
        can_export = role in {"exporter", "admin"}
        return UserContext(
            user_id=user[:64],
            role=role,
            can_export=can_export,
            is_admin=role == "admin",
            source="proxy_header",
        )

    role = _sanitize_role(config.role_env)
    user = (config.user_env or "anonymous")[:64]
    return UserContext(
        user_id=user,
        role=role,
        can_export=role in {"exporter", "admin"},
        is_admin=role == "admin",
        source="env",
    )
