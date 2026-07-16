from __future__ import annotations

from andy_threads.models import ThreadKind
from andy_threads.sector_lens import SectorId, owner_sector_for_thread_kind


def test_owner_for_power_inversion_is_engineering() -> None:
    assert owner_sector_for_thread_kind(ThreadKind.POWER_INVERSION) == SectorId.ENGINEERING


def test_owner_for_switching_event_is_operation() -> None:
    assert owner_sector_for_thread_kind(ThreadKind.SWITCHING_EVENT) == SectorId.OPERATION


def test_owner_for_measurement_gap_is_measurement_data() -> None:
    assert owner_sector_for_thread_kind(ThreadKind.MEASUREMENT_GAP) == SectorId.MEASUREMENT_DATA


def test_owner_for_access_rls_issue_is_it_bi() -> None:
    assert owner_sector_for_thread_kind(ThreadKind.ACCESS_RLS_ISSUE) == SectorId.IT_BI_DATA
