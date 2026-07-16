from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class AccessPrincipal:
    subject: str
    roles: tuple[str, ...] = field(default_factory=tuple)
    groups: tuple[str, ...] = field(default_factory=tuple)
    distributors: tuple[str, ...] = field(default_factory=tuple)
    states: tuple[str, ...] = field(default_factory=tuple)
    sources: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_claims(cls, claims: Mapping[str, Any]) -> "AccessPrincipal":
        return cls(
            subject=str(claims.get("subject", "")).strip(),
            roles=_as_tuple(claims.get("roles")),
            groups=_as_tuple(claims.get("groups")),
            distributors=_as_tuple(claims.get("distributor_scope")),
            states=_as_tuple(claims.get("state_scope")),
            sources=_as_tuple(claims.get("source_scope")),
        )


@dataclass(frozen=True)
class AccessScope:
    distributor: str | None = None
    state: str | None = None
    source_id: str | None = None
    substation: str | None = None
    profile: str | None = None


@dataclass(frozen=True)
class AccessEvaluation:
    allowed: bool
    reason: str
    principal_subject: str
    scope: AccessScope
    audit_required: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "principal_subject": self.principal_subject,
            "scope": self.scope.__dict__,
            "audit_required": self.audit_required,
        }


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if str(item))
    return (str(value),)
