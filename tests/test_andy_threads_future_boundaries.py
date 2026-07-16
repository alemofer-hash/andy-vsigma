from __future__ import annotations

from scripts.check_andy_threads_future_boundaries import validate_future_boundaries


def _payload() -> dict:
    return {
        "schema": "andy_threads_future_boundaries.v1",
        "mvp_mode": True,
        "real_identity_provider_enabled": False,
        "corporate_multiuser_store": {"enabled": False},
        "pyside_desktop_ui": {"enabled": False},
        "local_api": {"enabled": False},
        "notifications": {"enabled": False, "must_not_be_source_of_truth": True},
        "attachments": {"enabled": False},
    }


def test_future_boundaries_pass_for_disabled_mvp_features() -> None:
    assert validate_future_boundaries(_payload()) == []


def test_future_boundaries_fail_if_corporate_store_is_enabled() -> None:
    payload = _payload()
    payload["corporate_multiuser_store"]["enabled"] = True
    assert "future_feature_enabled_in_example:corporate_multiuser_store" in validate_future_boundaries(payload)


def test_future_boundaries_fail_if_notifications_become_source_of_truth() -> None:
    payload = _payload()
    payload["notifications"]["must_not_be_source_of_truth"] = False
    assert "notifications_must_not_be_source_of_truth" in validate_future_boundaries(payload)
