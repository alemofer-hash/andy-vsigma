from __future__ import annotations

from andy_bi.access_model import AccessPrincipal


def test_access_principal_from_claims_normalizes_scope_lists() -> None:
    principal = AccessPrincipal.from_claims(
        {
            "subject": "unit",
            "roles": ["engineer"],
            "groups": "group-one",
            "distributor_scope": ["DEMO"],
            "state_scope": ["RS"],
            "source_scope": ["source_demo"],
        }
    )

    assert principal.subject == "unit"
    assert principal.roles == ("engineer",)
    assert principal.groups == ("group-one",)
    assert principal.distributors == ("DEMO",)
