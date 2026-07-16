from __future__ import annotations

from pathlib import Path

from scripts.run_andy_threads_occurrences_demo import build_demo_payload


def test_occurrences_demo_builds_synthetic_end_to_end_flow(tmp_path: Path) -> None:
    payload = build_demo_payload(tmp_path)

    assert payload["status"] == "GO"
    assert payload["data_class"] == "synthetic"
    assert payload["real_provider_enabled"] is False
    assert payload["occurrence"]["occurrence_id"] == "occ-demo-threads-001"
    assert payload["occurrence"]["feedback_status"] == "RECEIVED"
    assert payload["notification_intents"][0]["status"] == "READY_FOR_HUMAN_SEND"
    assert payload["notification_intents"][0]["real_provider_enabled"] is False
    assert payload["candidate"]["status"] == "HUMAN_CONFIRMED"
    assert payload["candidate"]["validation_level"] == "HUMAN_CONFIRMED"
    assert payload["candidate"]["operationally_confirmed"] is False
    assert payload["feedback"]["training_label"] == "positive_human_confirmed"
    assert payload["ready_criteria"]["creates_occurrence"] is True
    assert payload["ready_criteria"]["generates_notification_intent"] is True
    assert payload["ready_criteria"]["registers_feedback_captcha"] is True
    assert payload["ready_criteria"]["exports_redacted_summary"] is True
    assert payload["ready_criteria"]["provider_real_disabled"] is True
    assert payload["ready_criteria"]["operational_decision_applied"] is False
    assert Path(payload["json_path"]).exists()
    assert Path(payload["markdown_path"]).exists()


def test_occurrences_demo_markdown_is_redacted_and_human_readable(tmp_path: Path) -> None:
    payload = build_demo_payload(tmp_path)
    markdown = Path(payload["markdown_path"]).read_text(encoding="utf-8")

    assert "ANDY Threads Occurrences Demo" in markdown
    assert "Provider real: `disabled`" in markdown
    assert "Nao houve envio real" in markdown
    assert "C:\\Users" not in markdown
