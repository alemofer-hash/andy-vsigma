from __future__ import annotations

from andy_bi.data_contract import default_data_contract, required_table_names, validate_contract_payload
from andy_bi.dataset_builder import synthetic_dataset_frames
from andy_bi.dataset_schema import validate_dataset_frames, validation_status


def test_data_contract_contains_required_tables_and_python_source_of_truth() -> None:
    contract = default_data_contract()

    assert contract["engine_source_of_truth"] == "python"
    assert contract["critical_math_policy"]["bi_can_reimplement_critical_math"] is False
    assert "fact_power_flow" in required_table_names()
    assert validate_contract_payload(contract) == []


def test_synthetic_frames_match_dataset_schema() -> None:
    frames = synthetic_dataset_frames(lote_id="test_lote")

    findings = validate_dataset_frames(frames)

    assert validation_status(findings) == "valid"
