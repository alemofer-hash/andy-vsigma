from __future__ import annotations

from pathlib import Path

from scripts.run_andy_threads_demo_scenarios import build_scenarios_package


def test_demo_scenarios_generate_five_sector_packages(tmp_path: Path) -> None:
    package = build_scenarios_package(tmp_path)

    assert package["status"] == "GO"
    assert package["data_class"] == "synthetic"
    assert package["real_provider_enabled"] is False
    assert package["scenario_count"] == 5
    assert package["ready_for_human_review"] is True
    assert Path(package["index_markdown_path"]).exists()
    assert Path(package["index_json_path"]).exists()
    assert {item["scenario_id"] for item in package["scenarios"]} == {
        "scenario_01_power_inversion_pq",
        "scenario_02_scada_switching",
        "scenario_03_measurement_gap_cadence",
        "scenario_04_cadastre_terminal_mismatch",
        "scenario_05_export_bi_dataset",
    }


def test_demo_scenarios_keep_operational_confirmation_scada_only(tmp_path: Path) -> None:
    package = build_scenarios_package(tmp_path)
    by_id = {item["scenario_id"]: item for item in package["scenarios"]}

    assert by_id["scenario_01_power_inversion_pq"]["candidate"]["status"] == "HUMAN_CONFIRMED"
    assert by_id["scenario_01_power_inversion_pq"]["operationally_confirmed"] is False
    assert by_id["scenario_02_scada_switching"]["candidate"]["status"] == "SCADA_CONFIRMED"
    assert by_id["scenario_02_scada_switching"]["operationally_confirmed"] is True
    assert by_id["scenario_04_cadastre_terminal_mismatch"]["candidate"]["status"] == "HUMAN_REVIEWED"
    assert by_id["scenario_04_cadastre_terminal_mismatch"]["operationally_confirmed"] is False


def test_demo_scenarios_generate_diagnostics_for_non_event_cases(tmp_path: Path) -> None:
    package = build_scenarios_package(tmp_path)
    by_id = {item["scenario_id"]: item for item in package["scenarios"]}

    gap = by_id["scenario_03_measurement_gap_cadence"]
    export = by_id["scenario_05_export_bi_dataset"]

    assert gap["candidate"] is None
    assert gap["diagnostic"]["diagnostic_type"] == "MEASUREMENT_AVAILABILITY"
    assert gap["feedback"]["training_label"] == "partial_incomplete"
    assert export["candidate"] is None
    assert export["diagnostic"]["diagnostic_type"] == "EXPORT_DASHBOARD"
    assert export["feedback"]["training_label"] == "partial_incomplete"


def test_demo_scenarios_markdown_is_review_ready_and_redacted(tmp_path: Path) -> None:
    package = build_scenarios_package(tmp_path)
    index_md = Path(package["index_markdown_path"]).read_text(encoding="utf-8")

    assert "ANDY Threads Demo Scenarios 001" in index_md
    assert "Provider real: `disabled`" in index_md
    for scenario in package["scenarios"]:
        markdown = Path(scenario["markdown_path"]).read_text(encoding="utf-8")
        assert "## Perguntas para revisao humana" in markdown
        assert "GO / PARTIAL / NO-GO" in markdown
        assert "C:\\Users" not in markdown
        assert "synthetic" in markdown
