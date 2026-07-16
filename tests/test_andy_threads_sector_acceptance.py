from __future__ import annotations

import json

from scripts.check_andy_threads_sector_acceptance import validate_acceptance


def _payload() -> dict:
    return {
        "schema": "andy_threads_sector_acceptance.v1",
        "accepted_for_operational_use": False,
        "sectors": [
            {"sector_id": "ENGINEERING", "accepted": False, "review_status": "pending"},
            {"sector_id": "OPERATION", "accepted": False, "review_status": "pending"},
            {"sector_id": "MEASUREMENT_DATA", "accepted": False, "review_status": "pending"},
            {"sector_id": "CADASTRE_ASSETS", "accepted": False, "review_status": "pending"},
            {"sector_id": "PROTECTION_AUTOMATION", "accepted": False, "review_status": "pending"},
            {"sector_id": "WORKS_MAINTENANCE", "accepted": False, "review_status": "pending"},
            {"sector_id": "IT_BI_DATA", "accepted": False, "review_status": "pending"},
            {"sector_id": "MANAGEMENT", "accepted": False, "review_status": "pending"},
        ],
    }


def test_sector_acceptance_allows_pending_template_when_explicit() -> None:
    assert validate_acceptance(_payload(), allow_pending=True) == []


def test_sector_acceptance_blocks_operational_use_without_human_acceptance() -> None:
    failures = validate_acceptance(_payload(), allow_pending=False)
    assert "accepted_for_operational_use_required" in failures
    assert "sector_not_accepted:ENGINEERING" in failures


def test_sector_acceptance_accepts_completed_private_shape() -> None:
    payload = _payload()
    payload["accepted_for_operational_use"] = True
    for sector in payload["sectors"]:
        sector["accepted"] = True
        sector["review_status"] = "accepted"
    assert validate_acceptance(payload) == []
