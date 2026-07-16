from __future__ import annotations

from andy_threads.emergency import (
    CommunicationDelayCause,
    EmergencyProblemDomain,
    EmergencySeverity,
    SectorId,
    estimate_emergency_readiness,
    route_for_emergency_domain,
    sla_for_severity,
)
from andy_threads.models import ThreadKind


def test_electrical_parameter_route_goes_to_engineering() -> None:
    route = route_for_emergency_domain(EmergencyProblemDomain.ELECTRICAL_PARAMETER)
    assert route.owner_sector == SectorId.ENGINEERING
    assert route.thread_kind == ThreadKind.LOAD_FLOW_ANOMALY
    assert CommunicationDelayCause.UNVERIFIED_PARAMETER in route.typical_delay_causes


def test_measurement_availability_route_goes_to_measurement_data() -> None:
    route = route_for_emergency_domain(EmergencyProblemDomain.MEASUREMENT_AVAILABILITY)
    assert route.owner_sector == SectorId.MEASUREMENT_DATA
    assert route.thread_kind == ThreadKind.MEASUREMENT_GAP


def test_critical_sla_requires_fast_decision_record() -> None:
    sla = sla_for_severity(EmergencySeverity.S4_CRITICAL_DECISION_RISK)
    assert sla.triage_minutes == 15
    assert sla.requires_decision_record is True


def test_emergency_readiness_estimates_current_gap() -> None:
    report = estimate_emergency_readiness()
    assert report.status == "MVP_FOUNDATION_READY"
    assert report.readiness_percent >= 45
    assert report.readiness_percent < 75
