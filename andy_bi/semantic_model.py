from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .schema_version import ANDY_BI_SEMANTIC_MODEL_VERSION


@dataclass(frozen=True)
class SemanticRelationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: str = "many_to_one"
    active: bool = True


@dataclass(frozen=True)
class SemanticMeasure:
    name: str
    table: str
    expression_hint: str
    category: str
    source: str
    allowed_in_bi: bool
    requires_python_parity_test: bool = False


def default_relationships() -> tuple[SemanticRelationship, ...]:
    fact_tables = ("fact_medicoes_long", "fact_power_flow", "fact_load_profile", "fact_catalog_quality", "fact_access_audit")
    relationships: list[SemanticRelationship] = []
    for fact in fact_tables:
        relationships.append(SemanticRelationship(fact, "lote_id", "dim_lote", "lote_id"))
        if fact != "fact_access_audit":
            relationships.append(SemanticRelationship(fact, "source_id", "dim_source", "source_id"))
            relationships.append(SemanticRelationship(fact, "quality_flag", "dim_quality_flag", "quality_flag"))
    for column, dim in (
        ("date_id", "dim_date"),
        ("time_id", "dim_time"),
        ("se_id", "dim_subestacao"),
        ("bay_alimentador_id", "dim_bay_alimentador"),
        ("equipamento_id", "dim_equipamento"),
        ("terminal_id", "dim_terminal"),
        ("variavel_id", "dim_variavel"),
        ("source_cadence", "dim_cadencia"),
    ):
        relationships.append(SemanticRelationship("fact_medicoes_long", column, dim, column))
    relationships.append(SemanticRelationship("fact_power_flow", "patamar_id", "dim_patamar", "patamar_id"))
    relationships.append(SemanticRelationship("fact_load_profile", "patamar_id", "dim_patamar", "patamar_id"))
    return tuple(relationships)


def default_measures() -> tuple[SemanticMeasure, ...]:
    return (
        SemanticMeasure("Medicoes", "fact_medicoes_long", "COUNTROWS(fact_medicoes_long)", "count", "bi_safe_aggregation", True),
        SemanticMeasure("Pontos", "fact_medicoes_long", "DISTINCTCOUNT(fact_medicoes_long[ponto_id])", "count", "bi_safe_aggregation", True),
        SemanticMeasure("Disponibilidade", "fact_catalog_quality", "quality/cobertura temporal precomputada", "quality", "andy_python_engine", True),
        SemanticMeasure("Media Valor Normalizado", "fact_medicoes_long", "AVERAGE(fact_medicoes_long[valor])", "simple_aggregation", "bi_safe_aggregation", True),
        SemanticMeasure("MVA", "fact_power_flow", "SUM/AVG over fact_power_flow[mva]", "critical_electrical", "andy_python_engine", True, True),
        SemanticMeasure("FP Assinado", "fact_power_flow", "AVG over fact_power_flow[fp_assinado]", "critical_electrical", "andy_python_engine", True, True),
        SemanticMeasure("MW", "fact_power_flow", "SUM/AVG over fact_power_flow[mw]", "critical_electrical", "andy_python_engine", True, True),
        SemanticMeasure("Fluxo P/Q", "fact_power_flow", "sentido_fluxo/quadrante precomputado", "critical_electrical", "andy_python_engine", True, True),
        SemanticMeasure("Inversoes", "fact_power_flow", "COUNTROWS where inversao_flag=true", "critical_electrical", "andy_python_engine", True, True),
        SemanticMeasure("Patamar", "fact_load_profile", "patamar_id precomputado", "critical_electrical", "andy_python_engine", True, True),
    )


def default_semantic_model() -> dict[str, Any]:
    return {
        "schema": ANDY_BI_SEMANTIC_MODEL_VERSION,
        "critical_math_policy": {
            "python_engine_is_source_of_truth": True,
            "bi_may_reaggregate_precomputed_values": True,
            "bi_may_reimplement_mva_fp_mw_flow_patamar": False,
        },
        "relationships": [asdict(item) for item in default_relationships()],
        "measures": [asdict(item) for item in default_measures()],
        "hidden_columns": [
            "hash_lote",
            "source_fingerprint",
            "internal_row_id",
        ],
    }


def write_default_semantic_model(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(default_semantic_model(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def validate_semantic_model(payload: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if payload.get("schema") != ANDY_BI_SEMANTIC_MODEL_VERSION:
        failures.append("schema_version_mismatch")
    policy = payload.get("critical_math_policy", {})
    if not isinstance(policy, Mapping) or policy.get("python_engine_is_source_of_truth") is not True:
        failures.append("python_engine_source_of_truth_required")
    if policy.get("bi_may_reimplement_mva_fp_mw_flow_patamar") is not False:
        failures.append("critical_math_reimplementation_must_be_false")
    measures = payload.get("measures", [])
    if not isinstance(measures, list) or not measures:
        failures.append("measures_required")
    return failures
