from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from .models import ThreadKind, ThreadPriority
from .sector_lens import SectorId


class EmergencyProblemDomain(str, Enum):
    ELECTRICAL_PARAMETER = "ELECTRICAL_PARAMETER"
    MEASUREMENT_AVAILABILITY = "MEASUREMENT_AVAILABILITY"
    CADASTRE_MAPPING = "CADASTRE_MAPPING"
    ANALYTIC_DIVERGENCE = "ANALYTIC_DIVERGENCE"
    EXPORT_DASHBOARD = "EXPORT_DASHBOARD"
    BI_ACCESS = "BI_ACCESS"
    OPERATIONAL_EVENT = "OPERATIONAL_EVENT"
    TOOL_RUNTIME = "TOOL_RUNTIME"


class EmergencySeverity(str, Enum):
    S0_OBSERVATION = "S0_OBSERVATION"
    S1_PRODUCTIVITY_BLOCKER = "S1_PRODUCTIVITY_BLOCKER"
    S2_ENGINEERING_BLOCKER = "S2_ENGINEERING_BLOCKER"
    S3_OPERATIONAL_RISK = "S3_OPERATIONAL_RISK"
    S4_CRITICAL_DECISION_RISK = "S4_CRITICAL_DECISION_RISK"


class CommunicationDelayCause(str, Enum):
    MISSING_CONTEXT = "MISSING_CONTEXT"
    WRONG_OWNER = "WRONG_OWNER"
    UNVERIFIED_PARAMETER = "UNVERIFIED_PARAMETER"
    AMBIGUOUS_CADASTRE = "AMBIGUOUS_CADASTRE"
    DATASET_OR_REFRESH_ISSUE = "DATASET_OR_REFRESH_ISSUE"
    TOOL_RUNTIME_FAILURE = "TOOL_RUNTIME_FAILURE"
    NO_DECISION_RECORD = "NO_DECISION_RECORD"
    NO_ESCALATION_PATH = "NO_ESCALATION_PATH"


@dataclass(frozen=True)
class EmergencySla:
    severity: EmergencySeverity
    triage_minutes: int
    first_response_minutes: int
    decision_target_minutes: int | None
    requires_decision_record: bool


@dataclass(frozen=True)
class EmergencyThreadRoute:
    domain: EmergencyProblemDomain
    thread_kind: ThreadKind
    default_priority: ThreadPriority
    owner_sector: SectorId
    consulted_sectors: tuple[SectorId, ...]
    required_context_fields: tuple[str, ...]
    typical_delay_causes: tuple[CommunicationDelayCause, ...]


@dataclass(frozen=True)
class EmergencyReadinessItem:
    item_id: str
    label: str
    status: str
    weight: int
    evidence: str
    next_action: str


@dataclass(frozen=True)
class EmergencyReadinessReport:
    score: int
    max_score: int
    readiness_percent: float
    status: str
    items: tuple[EmergencyReadinessItem, ...] = field(default_factory=tuple)


EMERGENCY_SLA: dict[EmergencySeverity, EmergencySla] = {
    EmergencySeverity.S0_OBSERVATION: EmergencySla(EmergencySeverity.S0_OBSERVATION, 240, 480, None, False),
    EmergencySeverity.S1_PRODUCTIVITY_BLOCKER: EmergencySla(EmergencySeverity.S1_PRODUCTIVITY_BLOCKER, 120, 240, 1440, True),
    EmergencySeverity.S2_ENGINEERING_BLOCKER: EmergencySla(EmergencySeverity.S2_ENGINEERING_BLOCKER, 60, 120, 480, True),
    EmergencySeverity.S3_OPERATIONAL_RISK: EmergencySla(EmergencySeverity.S3_OPERATIONAL_RISK, 30, 60, 240, True),
    EmergencySeverity.S4_CRITICAL_DECISION_RISK: EmergencySla(EmergencySeverity.S4_CRITICAL_DECISION_RISK, 15, 30, 120, True),
}


EMERGENCY_ROUTES: dict[EmergencyProblemDomain, EmergencyThreadRoute] = {
    EmergencyProblemDomain.ELECTRICAL_PARAMETER: EmergencyThreadRoute(
        EmergencyProblemDomain.ELECTRICAL_PARAMETER,
        ThreadKind.LOAD_FLOW_ANOMALY,
        ThreadPriority.HIGH,
        SectorId.ENGINEERING,
        (SectorId.MEASUREMENT_DATA, SectorId.CADASTRE_ASSETS, SectorId.OPERATION),
        ("se", "bay_or_feeder", "equipamento", "terminal", "variavel", "period_start", "period_end"),
        (
            CommunicationDelayCause.UNVERIFIED_PARAMETER,
            CommunicationDelayCause.MISSING_CONTEXT,
            CommunicationDelayCause.NO_DECISION_RECORD,
        ),
    ),
    EmergencyProblemDomain.MEASUREMENT_AVAILABILITY: EmergencyThreadRoute(
        EmergencyProblemDomain.MEASUREMENT_AVAILABILITY,
        ThreadKind.MEASUREMENT_GAP,
        ThreadPriority.HIGH,
        SectorId.MEASUREMENT_DATA,
        (SectorId.ENGINEERING, SectorId.IT_BI_DATA),
        ("source_cadence", "variavel", "period_start", "period_end"),
        (CommunicationDelayCause.MISSING_CONTEXT, CommunicationDelayCause.DATASET_OR_REFRESH_ISSUE),
    ),
    EmergencyProblemDomain.CADASTRE_MAPPING: EmergencyThreadRoute(
        EmergencyProblemDomain.CADASTRE_MAPPING,
        ThreadKind.TERMINAL_MAPPING,
        ThreadPriority.NORMAL,
        SectorId.CADASTRE_ASSETS,
        (SectorId.ENGINEERING, SectorId.MEASUREMENT_DATA),
        ("se", "bay_or_feeder", "equipamento", "terminal"),
        (CommunicationDelayCause.AMBIGUOUS_CADASTRE, CommunicationDelayCause.WRONG_OWNER),
    ),
    EmergencyProblemDomain.ANALYTIC_DIVERGENCE: EmergencyThreadRoute(
        EmergencyProblemDomain.ANALYTIC_DIVERGENCE,
        ThreadKind.PARITY_DESKTOP_BI,
        ThreadPriority.CRITICAL,
        SectorId.ENGINEERING,
        (SectorId.IT_BI_DATA,),
        ("lote_id", "dataset_version", "filter_hash", "query_signature"),
        (CommunicationDelayCause.UNVERIFIED_PARAMETER, CommunicationDelayCause.NO_DECISION_RECORD),
    ),
    EmergencyProblemDomain.EXPORT_DASHBOARD: EmergencyThreadRoute(
        EmergencyProblemDomain.EXPORT_DASHBOARD,
        ThreadKind.GENERAL_REVIEW,
        ThreadPriority.NORMAL,
        SectorId.ENGINEERING,
        (SectorId.IT_BI_DATA,),
        ("export_id", "filter_hash", "lote_id"),
        (CommunicationDelayCause.TOOL_RUNTIME_FAILURE, CommunicationDelayCause.MISSING_CONTEXT),
    ),
    EmergencyProblemDomain.BI_ACCESS: EmergencyThreadRoute(
        EmergencyProblemDomain.BI_ACCESS,
        ThreadKind.ACCESS_RLS_ISSUE,
        ThreadPriority.HIGH,
        SectorId.IT_BI_DATA,
        (SectorId.MANAGEMENT,),
        ("dataset_version", "report_page", "filter_hash"),
        (CommunicationDelayCause.DATASET_OR_REFRESH_ISSUE, CommunicationDelayCause.NO_ESCALATION_PATH),
    ),
    EmergencyProblemDomain.OPERATIONAL_EVENT: EmergencyThreadRoute(
        EmergencyProblemDomain.OPERATIONAL_EVENT,
        ThreadKind.SWITCHING_EVENT,
        ThreadPriority.CRITICAL,
        SectorId.OPERATION,
        (SectorId.ENGINEERING, SectorId.PROTECTION_AUTOMATION),
        ("se", "bay_or_feeder", "period_start", "period_end"),
        (CommunicationDelayCause.MISSING_CONTEXT, CommunicationDelayCause.NO_DECISION_RECORD),
    ),
    EmergencyProblemDomain.TOOL_RUNTIME: EmergencyThreadRoute(
        EmergencyProblemDomain.TOOL_RUNTIME,
        ThreadKind.BI_DATASET_ISSUE,
        ThreadPriority.HIGH,
        SectorId.IT_BI_DATA,
        (SectorId.ENGINEERING,),
        ("dataset_version", "lote_id", "filter_hash"),
        (CommunicationDelayCause.TOOL_RUNTIME_FAILURE, CommunicationDelayCause.DATASET_OR_REFRESH_ISSUE),
    ),
}


def route_for_emergency_domain(domain: EmergencyProblemDomain | str) -> EmergencyThreadRoute:
    return EMERGENCY_ROUTES[EmergencyProblemDomain(domain)]


def sla_for_severity(severity: EmergencySeverity | str) -> EmergencySla:
    return EMERGENCY_SLA[EmergencySeverity(severity)]


def estimate_emergency_readiness(completed_ids: Iterable[str] | None = None) -> EmergencyReadinessReport:
    completed = set(completed_ids or DEFAULT_COMPLETED_ITEMS)
    items = default_emergency_readiness_items()
    score = sum(item.weight for item in items if item.item_id in completed)
    max_score = sum(item.weight for item in items)
    percent = round((score / max_score) * 100, 1) if max_score else 0.0
    status = "MVP_FOUNDATION_READY" if percent >= 45 else "FOUNDATION_INCOMPLETE"
    if percent >= 75:
        status = "DESKTOP_PILOT_READY"
    if percent >= 90:
        status = "ENGINEERING_EMERGENCY_READY"
    return EmergencyReadinessReport(score, max_score, percent, status, tuple(items))


def default_emergency_readiness_items() -> list[EmergencyReadinessItem]:
    return [
        EmergencyReadinessItem("domain_core", "Domain core and technical references", "done", 10, "andy_threads models/references", "keep stable"),
        EmergencyReadinessItem("sector_matrix", "Initial sector routing matrix", "done", 8, "sector_lens/responsibility", "collect human acceptance"),
        EmergencyReadinessItem("deny_policy", "Deny-by-default local policy", "done", 8, "policy tests", "connect to real identity later"),
        EmergencyReadinessItem("local_store", "Local SQLite MVP store", "done", 8, "store tests", "define retention and backup before corporate use"),
        EmergencyReadinessItem("audit_redaction", "Audit and redaction", "done", 8, "audit tests", "extend with export/read events in UI"),
        EmergencyReadinessItem("emergency_taxonomy", "Emergency engineering taxonomy", "done", 8, "emergency module", "validate terms with engineering"),
        EmergencyReadinessItem("desktop_entrypoint", "Desktop button: comment this recorte", "pending", 12, "not implemented", "build PySide6 entrypoint"),
        EmergencyReadinessItem("thread_panel", "Thread panel for recorte history", "pending", 10, "not implemented", "show list, status and decision"),
        EmergencyReadinessItem("notification_bridge", "Teams/Outlook alert bridge", "blocked", 8, "future boundary disabled", "requires corporate provider review"),
        EmergencyReadinessItem("multiuser_store", "Corporate multiuser store", "blocked", 10, "future boundary disabled", "requires architecture/security review"),
        EmergencyReadinessItem("sector_acceptance", "Human sector acceptance", "pending", 6, "acceptance gate pending", "collect signed-off private matrix"),
        EmergencyReadinessItem("operational_runbook", "Emergency operations runbook", "pending", 4, "draft docs only", "run tabletop drill"),
    ]


DEFAULT_COMPLETED_ITEMS = (
    "domain_core",
    "sector_matrix",
    "deny_policy",
    "local_store",
    "audit_redaction",
    "emergency_taxonomy",
)
