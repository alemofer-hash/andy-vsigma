from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from andy_bi.access_model import AccessScope  # noqa: E402
from andy_bi.rls_policy import default_rls_policy, evaluate_rls, validate_rls_policy, write_default_rls_policy  # noqa: E402


REPORT_JSON = ROOT / "reports" / "ANDY_BI_RLS_POLICY.json"
REPORT_MD = ROOT / "reports" / "ANDY_BI_RLS_POLICY.md"


def main() -> int:
    policy = default_rls_policy()
    failures = validate_rls_policy(policy)
    generated = ROOT / "artifacts" / "andy_bi_rls_policy_check" / "rls_policy.json"
    write_default_rls_policy(generated)
    scope = AccessScope(distributor="DEMO", state="RS", source_id="source_demo")
    allowed = evaluate_rls(
        {
            "subject": "mock-engineer",
            "roles": ["engineer"],
            "distributor_scope": ["DEMO"],
            "state_scope": ["RS"],
            "source_scope": ["source_demo"],
        },
        scope,
        action="export",
        policy=policy,
    )
    denied = evaluate_rls(
        {
            "subject": "mock-out-of-scope",
            "roles": ["viewer"],
            "distributor_scope": ["OTHER"],
            "state_scope": ["MA"],
            "source_scope": [],
        },
        scope,
        action="view",
        policy=policy,
    )
    if not allowed.allowed:
        failures.append("mock_engineer_should_be_allowed")
    if denied.allowed:
        failures.append("out_of_scope_user_should_be_denied")
    report = {
        "status": "passed" if not failures else "blocked",
        "failures": failures,
        "generated_policy": str(generated),
        "allowed_decision": allowed.as_dict(),
        "denied_decision": denied.as_dict(),
        "default_decision": policy["default_decision"],
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"report={REPORT_MD}")
    return 0 if not failures else 1


def _markdown(report: dict) -> str:
    return (
        "# ANDY BI RLS/ABAC Gate\n\n"
        f"- Status: {report['status']}\n"
        f"- Default decision: {report['default_decision']}\n"
        f"- Mock allowed decision: {report['allowed_decision']['allowed']}\n"
        f"- Mock denied decision: {report['denied_decision']['allowed']}\n"
        f"- Failures: {', '.join(report['failures']) if report['failures'] else 'none'}\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
