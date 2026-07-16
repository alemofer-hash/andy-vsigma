from __future__ import annotations

from andy_bi.semantic_model import default_semantic_model, validate_semantic_model


def test_semantic_model_preserves_python_critical_math_boundary() -> None:
    model = default_semantic_model()

    assert validate_semantic_model(model) == []
    assert model["critical_math_policy"]["python_engine_is_source_of_truth"] is True
    assert model["critical_math_policy"]["bi_may_reimplement_mva_fp_mw_flow_patamar"] is False
    assert any(measure["source"] == "andy_python_engine" for measure in model["measures"])
