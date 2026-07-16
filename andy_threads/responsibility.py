from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .models import AndyThread, ThreadKind, ThreadPriority
from .references import AndyThreadReference, ThreadEntityType
from .sector_lens import (
    SectorId,
    can_sector_resolve,
    consulted_sectors_for_thread_kind,
    get_sector_lens,
    owner_sector_for_thread_kind,
)


@dataclass(frozen=True)
class ResponsibilityRule:
    kind: ThreadKind
    owner_sector: SectorId
    consulted_sectors: tuple[SectorId, ...]
    severity_hint: ThreadPriority = ThreadPriority.NORMAL


@dataclass(frozen=True)
class ResponsibilityDecision:
    kind: ThreadKind
    owner_sector: SectorId
    consulted_sectors: tuple[SectorId, ...]
    can_resolve_sectors: tuple[SectorId, ...]
    missing_context: tuple[str, ...]
    routing_notes: tuple[str, ...]
    severity_hint: ThreadPriority


class ResponsibilityMatrix:
    def route(self, kind: ThreadKind | str, reference: AndyThreadReference) -> ResponsibilityDecision:
        return route_thread(ThreadKind(kind), reference)


def classify_thread_kind(reference: AndyThreadReference, hints: Mapping[str, Any] | None = None) -> ThreadKind:
    active_hints = dict(hints or {})
    if active_hints.get("thread_kind"):
        return ThreadKind(str(active_hints["thread_kind"]))
    text = " ".join(str(value).lower() for value in active_hints.values() if value is not None)
    quality = str(reference.quality_flag or "").lower()
    if "rls" in text or reference.entity_type == ThreadEntityType.BI_REPORT_PAGE:
        return ThreadKind.ACCESS_RLS_ISSUE if "rls" in text else ThreadKind.BI_DATASET_ISSUE
    if "parity" in text or reference.entity_type == ThreadEntityType.PARITY_CHECK:
        return ThreadKind.PARITY_DESKTOP_BI
    if "invers" in text:
        return ThreadKind.POWER_INVERSION
    if "cadence" in text or "cadencia" in text or reference.source_cadence:
        return ThreadKind.CADENCE_ISSUE
    if "gap" in quality or "lacuna" in text:
        return ThreadKind.MEASUREMENT_GAP
    if reference.entity_type == ThreadEntityType.POWER_FLOW_EVENT:
        return ThreadKind.LOAD_FLOW_ANOMALY
    if reference.entity_type == ThreadEntityType.QUALITY_FLAG:
        return ThreadKind.DATA_QUALITY
    return ThreadKind.GENERAL_REVIEW


def route_thread(kind: ThreadKind | str, reference: AndyThreadReference) -> ResponsibilityDecision:
    active_kind = ThreadKind(kind)
    owner = owner_sector_for_thread_kind(active_kind)
    consulted = consulted_sectors_for_thread_kind(active_kind)
    resolvers = tuple(sector for sector in SectorId if can_sector_resolve(sector, active_kind))
    missing = tuple(field for field in required_context_for_kind(active_kind) if not getattr(reference, field, None))
    notes = ("deny_by_default_policy_required", "technical_reference_required")
    severity = ThreadPriority.HIGH if active_kind in {ThreadKind.POWER_INVERSION, ThreadKind.ACCESS_RLS_ISSUE} else ThreadPriority.NORMAL
    return ResponsibilityDecision(active_kind, owner, consulted, resolvers, missing, notes, severity)


def required_context_for_kind(kind: ThreadKind | str) -> list[str]:
    owner = owner_sector_for_thread_kind(kind)
    return list(get_sector_lens(owner).required_context_fields)


def validate_thread_responsibility(thread: AndyThread) -> list[str]:
    failures: list[str] = []
    decision = route_thread(thread.kind, thread.reference)
    if thread.owner_sector and thread.owner_sector != decision.owner_sector.value:
        failures.append("owner_sector_mismatch")
    if decision.missing_context:
        failures.append("missing_context:" + ",".join(decision.missing_context))
    return failures
