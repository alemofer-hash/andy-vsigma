from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACCEPTANCE = ROOT / "config" / "andy_threads_sector_acceptance.example.json"

REQUIRED_SECTORS = {
    "ENGINEERING",
    "OPERATION",
    "MEASUREMENT_DATA",
    "CADASTRE_ASSETS",
    "PROTECTION_AUTOMATION",
    "WORKS_MAINTENANCE",
    "IT_BI_DATA",
    "MANAGEMENT",
}


def validate_acceptance(payload: dict[str, Any], *, allow_pending: bool = False) -> list[str]:
    failures: list[str] = []
    if payload.get("schema") != "andy_threads_sector_acceptance.v1":
        failures.append("schema_version_mismatch")
    sectors = payload.get("sectors")
    if not isinstance(sectors, list):
        return failures + ["sectors_must_be_list"]
    by_id = {str(item.get("sector_id", "")): item for item in sectors if isinstance(item, dict)}
    missing = sorted(REQUIRED_SECTORS - set(by_id))
    if missing:
        failures.append("missing_required_sectors:" + ",".join(missing))
    for sector_id in sorted(REQUIRED_SECTORS & set(by_id)):
        sector = by_id[sector_id]
        if allow_pending:
            continue
        if sector.get("accepted") is not True:
            failures.append(f"sector_not_accepted:{sector_id}")
        if str(sector.get("review_status", "")).lower() != "accepted":
            failures.append(f"sector_review_not_accepted:{sector_id}")
    if not allow_pending and payload.get("accepted_for_operational_use") is not True:
        failures.append("accepted_for_operational_use_required")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ANDY Threads sector human acceptance gate.")
    parser.add_argument("--file", default=str(DEFAULT_ACCEPTANCE))
    parser.add_argument("--allow-pending", action="store_true", help="Allow public/example pending template for local readiness.")
    args = parser.parse_args(argv)

    path = Path(args.file)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    failures = validate_acceptance(payload, allow_pending=args.allow_pending)
    if failures:
        print("ANDY Threads sector acceptance: failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    status = "pending_allowed" if args.allow_pending and payload.get("accepted_for_operational_use") is not True else "accepted"
    print("ANDY Threads sector acceptance: passed")
    print(f"status={status}")
    print(f"sectors={len(payload.get('sectors', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
