from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .schema_version import ANDY_BI_DATASET_VERSION, ANDY_BI_SCHEMA_VERSION


@dataclass(frozen=True)
class ColumnContract:
    name: str
    dtype: str
    nullable: bool = True
    description: str = ""


@dataclass(frozen=True)
class TableContract:
    name: str
    kind: str
    primary_key: tuple[str, ...]
    columns: tuple[ColumnContract, ...]
    description: str = ""

    @property
    def required_columns(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns if not column.nullable)

    @property
    def all_columns(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


def _col(name: str, dtype: str, *, nullable: bool = True, description: str = "") -> ColumnContract:
    return ColumnContract(name=name, dtype=dtype, nullable=nullable, description=description)


def default_table_contracts() -> tuple[TableContract, ...]:
    return (
        TableContract(
            name="fact_medicoes_long",
            kind="fact",
            primary_key=("lote_id", "timestamp", "ponto_id", "variavel_id"),
            description="Medicoes normalizadas em formato LONG para consumo BI.",
            columns=(
                _col("timestamp", "datetime64[ns]", nullable=False),
                _col("date_id", "string", nullable=False),
                _col("time_id", "string", nullable=False),
                _col("source_id", "string", nullable=False),
                _col("se_id", "string"),
                _col("bay_alimentador_id", "string"),
                _col("equipamento_id", "string"),
                _col("terminal_id", "string"),
                _col("variavel_id", "string", nullable=False),
                _col("ponto_id", "string", nullable=False),
                _col("valor", "float64"),
                _col("source_cadence", "string"),
                _col("lote_id", "string", nullable=False),
                _col("quality_flag", "string", nullable=False),
            ),
        ),
        TableContract(
            name="fact_power_flow",
            kind="fact",
            primary_key=("lote_id", "timestamp", "ponto_id"),
            description="Resultados de fluxo P/Q e grandezas criticas calculadas pela engine Python.",
            columns=(
                _col("timestamp", "datetime64[ns]", nullable=False),
                _col("source_id", "string", nullable=False),
                _col("se_id", "string"),
                _col("bay_alimentador_id", "string"),
                _col("equipamento_id", "string"),
                _col("terminal_id", "string"),
                _col("ponto_id", "string", nullable=False),
                _col("mw", "float64"),
                _col("mvar", "float64"),
                _col("mva", "float64"),
                _col("fp_assinado", "float64"),
                _col("quadrante", "string"),
                _col("sentido_fluxo", "string"),
                _col("inversao_flag", "bool"),
                _col("patamar_id", "string"),
                _col("lote_id", "string", nullable=False),
                _col("quality_flag", "string", nullable=False),
            ),
        ),
        TableContract(
            name="fact_load_profile",
            kind="fact",
            primary_key=("lote_id", "patamar_id", "ponto_id"),
            description="Agregacoes de patamar/carga produzidas pela engine Python.",
            columns=(
                _col("periodo_id", "string", nullable=False),
                _col("patamar_id", "string", nullable=False),
                _col("source_id", "string", nullable=False),
                _col("ponto_id", "string", nullable=False),
                _col("corrente_media", "float64"),
                _col("corrente_max", "float64"),
                _col("tensao_media", "float64"),
                _col("mw_media", "float64"),
                _col("mva_media", "float64"),
                _col("fp_medio", "float64"),
                _col("sample_count", "int64", nullable=False),
                _col("lote_id", "string", nullable=False),
                _col("quality_flag", "string", nullable=False),
            ),
        ),
        TableContract(
            name="fact_catalog_quality",
            kind="fact",
            primary_key=("lote_id", "source_id"),
            description="Qualidade de catalogo, cobertura temporal e cadencia detectada.",
            columns=(
                _col("source_id", "string", nullable=False),
                _col("quantidade_arquivos", "int64", nullable=False),
                _col("quantidade_pontos", "int64", nullable=False),
                _col("cobertura_temporal_inicio", "datetime64[ns]"),
                _col("cobertura_temporal_fim", "datetime64[ns]"),
                _col("cadencia_detectada", "string"),
                _col("lacunas_detectadas", "int64", nullable=False),
                _col("quality_flag", "string", nullable=False),
                _col("lote_id", "string", nullable=False),
            ),
        ),
        TableContract(
            name="fact_access_audit",
            kind="fact",
            primary_key=("lote_id", "event_id"),
            description="Eventos redigidos/mock para acesso, exportacao e auditoria BI.",
            columns=(
                _col("event_id", "string", nullable=False),
                _col("event_type", "string", nullable=False),
                _col("actor_scope", "string", nullable=False),
                _col("operation_scope", "string"),
                _col("risk", "string"),
                _col("timestamp", "datetime64[ns]", nullable=False),
                _col("lote_id", "string", nullable=False),
            ),
        ),
        *_dimension_contracts(),
    )


def _dimension_contracts() -> tuple[TableContract, ...]:
    dimensions: list[TableContract] = []
    for name, key, label in (
        ("dim_date", "date_id", "Data"),
        ("dim_time", "time_id", "Hora"),
        ("dim_source", "source_id", "Fonte"),
        ("dim_subestacao", "se_id", "Subestacao"),
        ("dim_bay_alimentador", "bay_alimentador_id", "BAY/Alimentador"),
        ("dim_equipamento", "equipamento_id", "Equipamento"),
        ("dim_terminal", "terminal_id", "Terminal"),
        ("dim_variavel", "variavel_id", "Variavel"),
        ("dim_cadencia", "source_cadence", "Cadencia"),
        ("dim_patamar", "patamar_id", "Patamar"),
        ("dim_lote", "lote_id", "Lote"),
        ("dim_quality_flag", "quality_flag", "Quality flag"),
        ("dim_access_scope", "access_scope_id", "Escopo de acesso"),
    ):
        dimensions.append(
            TableContract(
                name=name,
                kind="dimension",
                primary_key=(key,),
                description=f"Dimensao BI: {label}.",
                columns=(
                    _col(key, "string", nullable=False),
                    _col("label", "string", nullable=False),
                    _col("description", "string"),
                    _col("lote_id", "string"),
                ),
            )
        )
    return tuple(dimensions)


def default_data_contract() -> dict[str, Any]:
    tables = default_table_contracts()
    return {
        "schema": ANDY_BI_SCHEMA_VERSION,
        "dataset_version": ANDY_BI_DATASET_VERSION,
        "engine_source_of_truth": "python",
        "critical_math_policy": {
            "bi_can_present": True,
            "bi_can_reimplement_critical_math": False,
            "critical_measure_source": "andy_python_engine",
        },
        "required_lote_fields": [
            "dataset_version",
            "schema_version",
            "build_timestamp",
            "source_fingerprint",
            "source_period_start",
            "source_period_end",
            "lote_id",
            "hash_lote",
            "created_by_runtime",
            "andy_engine_version",
            "validation_status",
            "source_cadence_summary",
            "row_counts",
            "quality_flags",
            "audit_summary",
        ],
        "tables": [asdict(table) for table in tables],
    }


def table_contract_map() -> dict[str, TableContract]:
    return {table.name: table for table in default_table_contracts()}


def required_table_names() -> tuple[str, ...]:
    return tuple(table.name for table in default_table_contracts())


def write_default_contract(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(default_data_contract(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_contract(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("andy_bi_contract_root_must_be_object")
    return payload


def validate_contract_payload(payload: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if payload.get("schema") != ANDY_BI_SCHEMA_VERSION:
        failures.append("schema_version_mismatch")
    tables = payload.get("tables")
    if not isinstance(tables, list):
        failures.append("tables_must_be_list")
        return failures
    names = {str(item.get("name")) for item in tables if isinstance(item, dict)}
    missing = set(required_table_names()) - names
    for table in sorted(missing):
        failures.append(f"missing_table:{table}")
    return failures
