from __future__ import annotations

from andy_bi.refresh_plan import default_refresh_plan, validate_refresh_plan


def test_refresh_plan_does_not_enable_real_gateway_or_auto_publish() -> None:
    plan = default_refresh_plan()

    assert validate_refresh_plan(plan) == []
    assert plan["real_gateway_configured"] is False
    assert plan["publish_automatically"] is False
