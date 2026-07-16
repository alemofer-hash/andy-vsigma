from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from andy_threads.context import context_from_query_filters
from andy_threads.emergency import EmergencyProblemDomain, EmergencySeverity, route_for_emergency_domain
from andy_threads.models import AndyThread, ThreadMessage, ThreadParticipant, ThreadPriority
from andy_threads.references import AndyThreadReference, reference_key, reference_public_summary
from andy_threads.store import ThreadStore

from desktop_app.models import DesktopRuntimeState, QueryFilters


@dataclass(frozen=True)
class DesktopThreadCreateResult:
    thread_id: str
    reference_key: str
    store_path: Path
    owner_sector: str
    priority: str
    kind: str


class DesktopThreadService:
    """Create local ANDY Threads from the active desktop query context."""

    def __init__(self, runtime_state: DesktopRuntimeState | None = None, *, root: str | Path | None = None) -> None:
        self.runtime_state = runtime_state
        self.store_path = self._resolve_store_path(runtime_state, root=root)
        self.store = ThreadStore(self.store_path)

    def create_thread_from_filters(
        self,
        filters: QueryFilters | Mapping[str, Any],
        *,
        title: str,
        body: str,
        severity: EmergencySeverity | str = EmergencySeverity.S1_PRODUCTIVITY_BLOCKER,
        domain: EmergencyProblemDomain | str = EmergencyProblemDomain.ELECTRICAL_PARAMETER,
        actor_subject: str = "desktop.local",
        actor_sector: str = "ENGINEERING",
        metadata: Mapping[str, Any] | None = None,
    ) -> DesktopThreadCreateResult:
        if not title.strip():
            raise ValueError("thread_title_required")
        if not body.strip():
            raise ValueError("thread_body_required")
        if not self._has_meaningful_filter_context(filters):
            raise ValueError("thread_requires_active_technical_recorte")

        active_domain = EmergencyProblemDomain(domain)
        active_severity = EmergencySeverity(severity)
        route = route_for_emergency_domain(active_domain)
        priority = self._priority_for_severity(active_severity, route.default_priority)
        reference = self._build_reference(filters, metadata=metadata)
        participant = ThreadParticipant(
            subject=actor_subject.strip() or "desktop.local",
            display_name="ANDY Desktop",
            sector_id=actor_sector.strip() or "ENGINEERING",
            roles=("desktop_user",),
        )
        thread_id = f"thread-{uuid4().hex}"
        message = ThreadMessage(
            message_id=f"msg-{uuid4().hex}",
            thread_id=thread_id,
            author=participant,
            body=body.strip(),
            metadata={
                "severity": active_severity.value,
                "domain": active_domain.value,
                "source": "desktop_recorte",
            },
        )
        thread = AndyThread(
            thread_id=thread_id,
            title=title.strip(),
            kind=route.thread_kind,
            reference=reference,
            created_by=participant,
            priority=priority,
            owner_sector=route.owner_sector.value,
            tags=("desktop", "recorte", active_domain.value.lower()),
            messages=[message],
        )
        self.store.create_thread(thread)
        self.store.add_message(message)
        return DesktopThreadCreateResult(
            thread_id=thread.thread_id,
            reference_key=reference_key(reference),
            store_path=self.store_path,
            owner_sector=route.owner_sector.value,
            priority=priority.value,
            kind=route.thread_kind.value,
        )

    def _build_reference(
        self,
        filters: QueryFilters | Mapping[str, Any],
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> AndyThreadReference:
        safe_metadata = self._runtime_metadata()
        safe_metadata.update(dict(metadata or {}))
        return context_from_query_filters(filters, safe_metadata)

    def _runtime_metadata(self) -> dict[str, Any]:
        state = self.runtime_state
        if state is None:
            return {"created_by_runtime": "desktop_thread_service"}
        return {
            "created_by_runtime": "desktop_thread_service",
            "catalog_status": state.catalog_status,
            "catalog_ready": state.catalog_ready,
            "source_mode": state.source_mode,
            "source_file_count": state.source_file_count,
            "db_exists": state.db_exists,
        }

    @staticmethod
    def _priority_for_severity(severity: EmergencySeverity, default: ThreadPriority) -> ThreadPriority:
        if severity == EmergencySeverity.S4_CRITICAL_DECISION_RISK:
            return ThreadPriority.CRITICAL
        if severity in {EmergencySeverity.S2_ENGINEERING_BLOCKER, EmergencySeverity.S3_OPERATIONAL_RISK}:
            return ThreadPriority.HIGH
        if severity == EmergencySeverity.S0_OBSERVATION:
            return ThreadPriority.NORMAL
        return default

    @staticmethod
    def _has_meaningful_filter_context(filters: QueryFilters | Mapping[str, Any]) -> bool:
        payload = dict(filters) if isinstance(filters, Mapping) else vars(filters)
        context_keys = (
            "ano",
            "anos_sel",
            "meses_sel",
            "dias_sel",
            "se_sel",
            "bay_sel",
            "equipamento_sel",
            "terminal_sel",
            "vars_sel",
            "source_cadence_sel",
            "ponto_id_like",
        )
        for key in context_keys:
            value = payload.get(key)
            if isinstance(value, (list, tuple, set)) and any(str(item).strip() for item in value):
                return True
            if value not in (None, "", [], (), {}):
                return True
        return False

    @staticmethod
    def _resolve_store_path(
        runtime_state: DesktopRuntimeState | None,
        *,
        root: str | Path | None = None,
    ) -> Path:
        if root is not None:
            base = Path(root)
        elif runtime_state is not None:
            base = Path(runtime_state.layout["workspace"])
        else:
            base = Path.cwd() / ".validation_tmp" / "andy_threads_desktop"
        return base / "ANDY_THREADS" / "threads.sqlite"


def thread_reference_summary(reference: AndyThreadReference) -> dict[str, Any]:
    return reference_public_summary(reference)
