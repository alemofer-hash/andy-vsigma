from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOUNDARY = ROOT / "config" / "andy_threads_future_boundaries.example.json"

DISABLED_BLOCKS = (
    "corporate_multiuser_store",
    "pyside_desktop_ui",
    "local_api",
    "notifications",
    "attachments",
)


def validate_future_boundaries(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if payload.get("schema") != "andy_threads_future_boundaries.v1":
        failures.append("schema_version_mismatch")
    if payload.get("mvp_mode") is not True:
        failures.append("mvp_mode_must_remain_true_for_example")
    if payload.get("real_identity_provider_enabled") is not False:
        failures.append("real_identity_provider_must_be_disabled")
    for block_name in DISABLED_BLOCKS:
        block = payload.get(block_name)
        if not isinstance(block, dict):
            failures.append(f"missing_boundary_block:{block_name}")
            continue
        if block.get("enabled") is not False:
            failures.append(f"future_feature_enabled_in_example:{block_name}")
    notifications = payload.get("notifications", {})
    if isinstance(notifications, dict) and notifications.get("must_not_be_source_of_truth") is not True:
        failures.append("notifications_must_not_be_source_of_truth")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ANDY Threads future feature boundaries.")
    parser.add_argument("--file", default=str(DEFAULT_BOUNDARY))
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.file).read_text(encoding="utf-8-sig"))
    failures = validate_future_boundaries(payload)
    if failures:
        print("ANDY Threads future boundaries: failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("ANDY Threads future boundaries: passed")
    print("corporate_multiuser_store=false")
    print("pyside_desktop_ui=false")
    print("local_api=false")
    print("notifications=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
