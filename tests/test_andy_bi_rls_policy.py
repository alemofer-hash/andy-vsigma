from __future__ import annotations

from andy_bi.access_model import AccessScope
from andy_bi.rls_policy import default_rls_policy, evaluate_rls, validate_rls_policy


def test_rls_policy_is_deny_by_default() -> None:
    policy = default_rls_policy()

    assert validate_rls_policy(policy) == []
    denied = evaluate_rls(None, AccessScope(distributor="DEMO", state="RS", source_id="source_demo"), policy=policy)

    assert denied.allowed is False
    assert denied.reason == "identity_required"


def test_rls_policy_allows_only_matching_claim_scope() -> None:
    policy = default_rls_policy()
    scope = AccessScope(distributor="DEMO", state="RS", source_id="source_demo")

    allowed = evaluate_rls(
        {
            "subject": "unit-engineer",
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
            "subject": "unit-viewer",
            "roles": ["viewer"],
            "distributor_scope": ["OTHER"],
            "state_scope": ["MA"],
            "source_scope": [],
        },
        scope,
        action="view",
        policy=policy,
    )

    assert allowed.allowed is True
    assert denied.allowed is False
