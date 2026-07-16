from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_threads.emergency import (
    EMERGENCY_ROUTES,
    EMERGENCY_SLA,
    estimate_emergency_readiness,
)

DEFAULT_CONFIG = ROOT / "config" / "andy_threads_emergency_readiness.example.json"


def load_completed_items(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if payload.get("schema") != "andy_threads_emergency_readiness.v1":
        raise ValueError("schema_version_mismatch")
    completed = payload.get("completed_items", [])
    if not isinstance(completed, list):
        raise ValueError("completed_items_must_be_list")
    return [str(item) for item in completed]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate ANDY Threads emergency engineering readiness.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--min-percent", type=float, default=45.0)
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)

    completed = load_completed_items(Path(args.config))
    report = estimate_emergency_readiness(completed)
    payload: dict[str, Any] = {
        "status": report.status,
        "score": report.score,
        "max_score": report.max_score,
        "readiness_percent": report.readiness_percent,
        "route_count": len(EMERGENCY_ROUTES),
        "sla_count": len(EMERGENCY_SLA),
        "pending": [item.item_id for item in report.items if item.item_id not in set(completed)],
    }
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("ANDY Threads emergency readiness: " + ("passed" if report.readiness_percent >= args.min_percent else "failed"))
    print(f"status={report.status}")
    print(f"readiness_percent={report.readiness_percent}")
    print(f"score={report.score}/{report.max_score}")
    print(f"routes={len(EMERGENCY_ROUTES)}")
    print(f"slas={len(EMERGENCY_SLA)}")
    if report.readiness_percent < args.min_percent:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
