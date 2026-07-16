from __future__ import annotations

from andy_threads.references import AndyThreadReference, ThreadEntityType
from andy_threads.responsibility import route_thread
from andy_threads.models import ThreadKind
from andy_threads.sector_lens import SectorId


def test_routing_returns_owner_consulted_and_resolvers() -> None:
    ref = AndyThreadReference(ThreadEntityType.POWER_FLOW_EVENT, se="SE1", bay_or_feeder="AL1")
    decision = route_thread(ThreadKind.POWER_INVERSION, ref)
    assert decision.owner_sector == SectorId.ENGINEERING
    assert SectorId.OPERATION in decision.consulted_sectors
    assert SectorId.ENGINEERING in decision.can_resolve_sectors


def test_missing_context_is_reported() -> None:
    ref = AndyThreadReference(ThreadEntityType.POWER_FLOW_EVENT, se="SE1")
    decision = route_thread(ThreadKind.POWER_INVERSION, ref)
    assert "bay_or_feeder" in decision.missing_context
    assert "period_start" in decision.missing_context
