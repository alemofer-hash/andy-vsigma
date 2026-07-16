from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .models import AndyThread, ThreadKind
from .occurrences import Occurrence
from .references import AndyThreadReference
from .responsibility import route_thread
from .sector_lens import SectorId, can_sector_resolve


class ThreadAction(str, Enum):
    CREATE_THREAD = "CREATE_THREAD"
    READ_THREAD = "READ_THREAD"
    COMMENT = "COMMENT"
    CHANGE_STATUS = "CHANGE_STATUS"
    CREATE_DECISION = "CREATE_DECISION"
    EXPORT_THREAD = "EXPORT_THREAD"
    ARCHIVE_THREAD = "ARCHIVE_THREAD"


class OccurrenceAction(str, Enum):
    CREATE_OCCURRENCE = "CREATE_OCCURRENCE"
    READ_OCCURRENCE = "READ_OCCURRENCE"
    COMMENT_OCCURRENCE = "COMMENT_OCCURRENCE"
    CHANGE_OCCURRENCE_STATUS = "CHANGE_OCCURRENCE_STATUS"
    EXPORT_OCCURRENCE = "EXPORT_OCCURRENCE"
    ARCHIVE_OCCURRENCE = "ARCHIVE_OCCURRENCE"


@dataclass(frozen=True)
class MockThreadUserContext:
    subject: str
    sector_id: SectorId | str
    roles: tuple[str, ...] = field(default_factory=tuple)
    states: tuple[str, ...] = field(default_factory=tuple)
    distributors: tuple[str, ...] = field(default_factory=tuple)
    substations: tuple[str, ...] = field(default_factory=tuple)
    feeders: tuple[str, ...] = field(default_factory=tuple)
    can_export_threads: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "sector_id", SectorId(self.sector_id))


@dataclass(frozen=True)
class ThreadAccessRequest:
    action: ThreadAction | str
    user: MockThreadUserContext | None
    reference: AndyThreadReference | None = None
    thread: AndyThread | None = None
    kind: ThreadKind | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", ThreadAction(self.action))
        if self.kind is not None:
            object.__setattr__(self, "kind", ThreadKind(self.kind))


@dataclass(frozen=True)
class OccurrenceAccessRequest:
    action: OccurrenceAction | str
    user: MockThreadUserContext | None
    occurrence: Occurrence | None = None
    reference: AndyThreadReference | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", OccurrenceAction(self.action))


@dataclass(frozen=True)
class ThreadAccessDecision:
    allowed: bool
    reason: str
    action: ThreadAction
    subject: str = ""
    audit_required: bool = True


@dataclass(frozen=True)
class OccurrenceAccessDecision:
    allowed: bool
    reason: str
    action: OccurrenceAction
    subject: str = ""
    audit_required: bool = True


class ThreadPolicy:
    def evaluate(self, request: ThreadAccessRequest) -> ThreadAccessDecision:
        return evaluate_thread_access(request)


def evaluate_thread_access(request: ThreadAccessRequest) -> ThreadAccessDecision:
    if request.user is None:
        return _deny(request, "identity_required")
    ref = request.reference or (request.thread.reference if request.thread else None)
    if ref is None:
        return _deny(request, "technical_reference_required")
    kind = ThreadKind(request.kind or (request.thread.kind if request.thread else ThreadKind.GENERAL_REVIEW))
    if not _scope_matches(request.user, ref):
        return _deny(request, "reference_outside_user_scope")
    routing = route_thread(kind, ref)
    sector = request.user.sector_id
    if request.action in {ThreadAction.CREATE_THREAD, ThreadAction.CHANGE_STATUS}:
        return _allow(request, "owner_scope_allowed") if sector == routing.owner_sector else _deny(request, "owner_sector_required")
    if request.action == ThreadAction.READ_THREAD:
        if sector == routing.owner_sector or sector in routing.consulted_sectors or can_sector_resolve(sector, kind):
            return _allow(request, "sector_scope_allowed")
        return _deny(request, "sector_not_in_thread_scope")
    if request.action == ThreadAction.COMMENT:
        if sector == routing.owner_sector or sector in routing.consulted_sectors:
            return _allow(request, "comment_allowed_for_owner_or_consulted")
        return _deny(request, "comment_requires_owner_or_consulted_sector")
    if request.action in {ThreadAction.CREATE_DECISION, ThreadAction.ARCHIVE_THREAD}:
        return _allow(request, "resolver_allowed") if can_sector_resolve(sector, kind) else _deny(request, "resolver_sector_required")
    if request.action == ThreadAction.EXPORT_THREAD:
        return _allow(request, "explicit_export_permission") if request.user.can_export_threads else _deny(request, "export_permission_required")
    return _deny(request, "unknown_action")


def require_thread_access(request: ThreadAccessRequest) -> ThreadAccessDecision:
    decision = evaluate_thread_access(request)
    if not decision.allowed:
        raise PermissionError(decision.reason)
    return decision


def evaluate_occurrence_access(request: OccurrenceAccessRequest) -> OccurrenceAccessDecision:
    if request.user is None:
        return _deny_occurrence(request, "identity_required")
    ref = request.reference or (request.occurrence.reference if request.occurrence else None)
    if ref is None:
        return _deny_occurrence(request, "technical_reference_required")
    if not _scope_matches(request.user, ref):
        return _deny_occurrence(request, "reference_outside_user_scope")
    if request.occurrence is None:
        return _deny_occurrence(request, "occurrence_required")

    sector = request.user.sector_id
    owner_sector = request.occurrence.owner_sector
    target_sector = request.occurrence.target_sector
    is_owner = sector == owner_sector
    is_target = target_sector is not None and sector == target_sector

    if request.action == OccurrenceAction.CREATE_OCCURRENCE:
        return (
            _allow_occurrence(request, "owner_scope_allowed")
            if is_owner
            else _deny_occurrence(request, "owner_sector_required")
        )
    if request.action == OccurrenceAction.READ_OCCURRENCE:
        return (
            _allow_occurrence(request, "sector_scope_allowed")
            if is_owner or is_target
            else _deny_occurrence(request, "sector_not_in_occurrence_scope")
        )
    if request.action == OccurrenceAction.COMMENT_OCCURRENCE:
        return (
            _allow_occurrence(request, "comment_allowed_for_owner_or_target")
            if is_owner or is_target
            else _deny_occurrence(request, "comment_requires_owner_or_target_sector")
        )
    if request.action == OccurrenceAction.CHANGE_OCCURRENCE_STATUS:
        return (
            _allow_occurrence(request, "owner_or_target_status_allowed")
            if is_owner or is_target
            else _deny_occurrence(request, "status_change_requires_owner_or_target_sector")
        )
    if request.action == OccurrenceAction.ARCHIVE_OCCURRENCE:
        return (
            _allow_occurrence(request, "owner_archive_allowed")
            if is_owner
            else _deny_occurrence(request, "owner_sector_required")
        )
    if request.action == OccurrenceAction.EXPORT_OCCURRENCE:
        return (
            _allow_occurrence(request, "explicit_export_permission")
            if request.user.can_export_threads
            else _deny_occurrence(request, "export_permission_required")
        )
    return _deny_occurrence(request, "unknown_action")


def require_occurrence_access(request: OccurrenceAccessRequest) -> OccurrenceAccessDecision:
    decision = evaluate_occurrence_access(request)
    if not decision.allowed:
        raise PermissionError(decision.reason)
    return decision


def _scope_matches(user: MockThreadUserContext, ref: AndyThreadReference) -> bool:
    if "*" in user.substations or not user.substations:
        se_ok = True
    else:
        se_ok = bool(ref.se and ref.se in user.substations)
    if "*" in user.feeders or not user.feeders:
        feeder_ok = True
    else:
        feeder = ref.bay_or_feeder or ref.bay or ref.alimentador
        feeder_ok = bool(feeder and feeder in user.feeders)
    return se_ok and feeder_ok


def _allow(request: ThreadAccessRequest, reason: str) -> ThreadAccessDecision:
    return ThreadAccessDecision(True, reason, request.action, request.user.subject if request.user else "")


def _deny(request: ThreadAccessRequest, reason: str) -> ThreadAccessDecision:
    return ThreadAccessDecision(False, reason, request.action, request.user.subject if request.user else "")


def _allow_occurrence(request: OccurrenceAccessRequest, reason: str) -> OccurrenceAccessDecision:
    return OccurrenceAccessDecision(True, reason, request.action, request.user.subject if request.user else "")


def _deny_occurrence(request: OccurrenceAccessRequest, reason: str) -> OccurrenceAccessDecision:
    return OccurrenceAccessDecision(False, reason, request.action, request.user.subject if request.user else "")
