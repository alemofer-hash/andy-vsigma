from __future__ import annotations

ANDY_BI_DATASET_VERSION = "0.1.0"
ANDY_BI_SCHEMA_VERSION = "andy.bi.dataset.v1"
ANDY_BI_SEMANTIC_MODEL_VERSION = "andy.bi.semantic.v1"
ANDY_BI_RLS_POLICY_VERSION = "andy.bi.rls.v1"
ANDY_BI_REFRESH_PLAN_VERSION = "andy.bi.refresh.v1"

ENGINE_SOURCE_OF_TRUTH = "python"
CRITICAL_MEASURE_SOURCE = "andy_python_engine"


def version_payload() -> dict[str, str]:
    return {
        "dataset_version": ANDY_BI_DATASET_VERSION,
        "schema_version": ANDY_BI_SCHEMA_VERSION,
        "semantic_model_version": ANDY_BI_SEMANTIC_MODEL_VERSION,
        "rls_policy_version": ANDY_BI_RLS_POLICY_VERSION,
        "refresh_plan_version": ANDY_BI_REFRESH_PLAN_VERSION,
        "engine_source_of_truth": ENGINE_SOURCE_OF_TRUTH,
    }
