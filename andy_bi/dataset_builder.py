from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .data_contract import default_data_contract, table_contract_map, write_default_contract
from .dataset_schema import DatasetSchemaFinding, validate_dataset_frames, validation_status
from .publish_manifest import build_publish_manifest, write_manifest
from .schema_version import ANDY_BI_DATASET_VERSION, ANDY_BI_SCHEMA_VERSION
from .semantic_dataset import dataset_file_name, normalize_dataset_format, write_frame


@dataclass(frozen=True)
class DatasetBuildResult:
    out_dir: Path
    schema_path: Path
    manifest_path: Path
    validation_report_path: Path
    files: dict[str, str]
    row_counts: dict[str, int]
    validation_status: str
    findings: list[DatasetSchemaFinding]
    synthetic: bool


def build_andy_bi_dataset(
    *,
    out_dir: str | Path,
    fmt: str = "parquet",
    source_db: str | Path | None = None,
    lote_id: str = "andy_bi_demo_lote",
    synthetic: bool | None = None,
    allow_local_data: bool = False,
) -> DatasetBuildResult:
    """Build a governed BI dataset package without publishing it.

    Real/local DuckDB extraction is intentionally opt-in. The default path emits
    a small synthetic dataset that exercises the contract without carrying
    operational measurements into versionable artifacts.
    """

    fmt = normalize_dataset_format(fmt)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    use_synthetic = synthetic if synthetic is not None else not source_db
    if source_db and not allow_local_data:
        raise ValueError("source_db_requires_allow_local_data")
    if source_db and allow_local_data:
        frames = _frames_from_duckdb_placeholder(Path(source_db), lote_id)
        use_synthetic = False
    else:
        frames = synthetic_dataset_frames(lote_id=lote_id)
        use_synthetic = True

    findings = validate_dataset_frames(frames)
    status = validation_status(findings)
    schema_path = write_default_contract(out / "schema.json")

    file_paths: dict[str, Path] = {}
    for table_name, frame in frames.items():
        if fmt in {"parquet", "both"}:
            file_paths[f"{table_name}:parquet"] = write_frame(frame, out / dataset_file_name(table_name, "parquet"))
        if fmt in {"csv", "both"}:
            file_paths[f"{table_name}:csv"] = write_frame(frame, out / dataset_file_name(table_name, "csv"))

    row_counts = {table: int(len(frame)) for table, frame in frames.items()}
    manifest = build_publish_manifest(
        lote_id=lote_id,
        files=file_paths,
        row_counts=row_counts,
        source_fingerprint="synthetic-demo" if use_synthetic else f"local-duckdb:{Path(source_db).name if source_db else 'unknown'}",
        source_period_start=_period_start(frames),
        source_period_end=_period_end(frames),
        validation_status=status,
        source_cadence_summary=_cadence_summary(frames),
        quality_flags=_quality_flags(frames),
        audit_summary={
            "published": False,
            "real_identity_provider_called": False,
            "real_source_written": False,
            "synthetic": use_synthetic,
        },
    )
    manifest_path = write_manifest(out / "manifest.json", manifest)
    validation_report_path = write_validation_report(out / "validation_report.md", findings, row_counts, use_synthetic)
    return DatasetBuildResult(
        out_dir=out,
        schema_path=schema_path,
        manifest_path=manifest_path,
        validation_report_path=validation_report_path,
        files={name: str(path) for name, path in file_paths.items()},
        row_counts=row_counts,
        validation_status=status,
        findings=findings,
        synthetic=use_synthetic,
    )


def synthetic_dataset_frames(*, lote_id: str = "andy_bi_demo_lote") -> dict[str, pd.DataFrame]:
    timestamps = pd.to_datetime(["2026-01-01 00:00", "2026-01-01 00:15", "2026-01-01 00:30", "2026-01-01 00:45"])
    fact_medicoes = pd.DataFrame(
        {
            "timestamp": timestamps,
            "date_id": ["20260101"] * 4,
            "time_id": ["0000", "0015", "0030", "0045"],
            "source_id": ["source_demo"] * 4,
            "se_id": ["SE_DEMO"] * 4,
            "bay_alimentador_id": ["AL_DEMO"] * 4,
            "equipamento_id": ["EQ_DEMO"] * 4,
            "terminal_id": ["T1"] * 4,
            "variavel_id": ["P", "Q", "P", "Q"],
            "ponto_id": ["PONTO_DEMO"] * 4,
            "valor": [12.0, 3.0, -8.0, 2.0],
            "source_cadence": ["15min"] * 4,
            "lote_id": [lote_id] * 4,
            "quality_flag": ["OK"] * 4,
        }
    )
    fact_power_flow = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-01 00:00", "2026-01-01 00:30"]),
            "source_id": ["source_demo", "source_demo"],
            "se_id": ["SE_DEMO", "SE_DEMO"],
            "bay_alimentador_id": ["AL_DEMO", "AL_DEMO"],
            "equipamento_id": ["EQ_DEMO", "EQ_DEMO"],
            "terminal_id": ["T1", "T1"],
            "ponto_id": ["PONTO_DEMO", "PONTO_DEMO"],
            "mw": [12.0, -8.0],
            "mvar": [3.0, 2.0],
            "mva": [12.3693168769, 8.2462112512],
            "fp_assinado": [0.9701425001, -0.9701425001],
            "quadrante": ["Q1", "Q2"],
            "sentido_fluxo": ["DIRETO", "INVERSO"],
            "inversao_flag": [False, True],
            "patamar_id": ["leve", "leve"],
            "lote_id": [lote_id, lote_id],
            "quality_flag": ["OK", "OK"],
        }
    )
    fact_load_profile = pd.DataFrame(
        {
            "periodo_id": ["2026-01-01"],
            "patamar_id": ["leve"],
            "source_id": ["source_demo"],
            "ponto_id": ["PONTO_DEMO"],
            "corrente_media": [11.5],
            "corrente_max": [13.2],
            "tensao_media": [13.8],
            "mw_media": [2.0],
            "mva_media": [10.3],
            "fp_medio": [0.95],
            "sample_count": [4],
            "lote_id": [lote_id],
            "quality_flag": ["OK"],
        }
    )
    fact_catalog_quality = pd.DataFrame(
        {
            "source_id": ["source_demo"],
            "quantidade_arquivos": [2],
            "quantidade_pontos": [1],
            "cobertura_temporal_inicio": pd.to_datetime(["2026-01-01 00:00"]),
            "cobertura_temporal_fim": pd.to_datetime(["2026-01-01 00:45"]),
            "cadencia_detectada": ["15min"],
            "lacunas_detectadas": [0],
            "quality_flag": ["OK"],
            "lote_id": [lote_id],
        }
    )
    fact_access_audit = pd.DataFrame(
        {
            "event_id": ["event_demo_001"],
            "event_type": ["dataset_build"],
            "actor_scope": ["mock_engineer"],
            "operation_scope": ["demo_dataset"],
            "risk": ["LOW"],
            "timestamp": pd.to_datetime([_now_utc()]),
            "lote_id": [lote_id],
        }
    )
    frames: dict[str, pd.DataFrame] = {
        "fact_medicoes_long": fact_medicoes,
        "fact_power_flow": fact_power_flow,
        "fact_load_profile": fact_load_profile,
        "fact_catalog_quality": fact_catalog_quality,
        "fact_access_audit": fact_access_audit,
    }
    frames.update(_dimension_frames(frames, lote_id))
    return frames


def write_validation_report(path: str | Path, findings: list[DatasetSchemaFinding], row_counts: Mapping[str, int], synthetic: bool) -> Path:
    lines = [
        "# ANDY BI Dataset Validation Report",
        "",
        f"- Validation status: {validation_status(findings)}",
        f"- Synthetic dataset: {synthetic}",
        "- Published to corporate BI: false",
        "- Python engine source of truth: true",
        "",
        "## Row Counts",
        "",
    ]
    for table, count in sorted(row_counts.items()):
        lines.append(f"- {table}: {count}")
    lines.extend(["", "## Findings", ""])
    if findings:
        for item in findings:
            lines.append(f"- {item.severity} {item.table} {item.code}: {item.message}")
    else:
        lines.append("- none")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _dimension_frames(frames: Mapping[str, pd.DataFrame], lote_id: str) -> dict[str, pd.DataFrame]:
    values: dict[str, set[str]] = {
        "date_id": set(),
        "time_id": set(),
        "source_id": set(),
        "se_id": set(),
        "bay_alimentador_id": set(),
        "equipamento_id": set(),
        "terminal_id": set(),
        "variavel_id": set(),
        "source_cadence": set(),
        "patamar_id": set(),
        "quality_flag": set(),
    }
    for frame in frames.values():
        for column in values:
            if column in frame.columns:
                values[column].update(str(item) for item in frame[column].dropna().unique())
    specs = {
        "dim_date": "date_id",
        "dim_time": "time_id",
        "dim_source": "source_id",
        "dim_subestacao": "se_id",
        "dim_bay_alimentador": "bay_alimentador_id",
        "dim_equipamento": "equipamento_id",
        "dim_terminal": "terminal_id",
        "dim_variavel": "variavel_id",
        "dim_cadencia": "source_cadence",
        "dim_patamar": "patamar_id",
        "dim_quality_flag": "quality_flag",
    }
    dimensions = {
        table: _dimension_frame(key, sorted(values[key]), lote_id)
        for table, key in specs.items()
    }
    dimensions["dim_lote"] = _dimension_frame("lote_id", [lote_id], lote_id)
    dimensions["dim_access_scope"] = _dimension_frame("access_scope_id", ["mock_engineer"], lote_id)
    return dimensions


def _dimension_frame(key: str, items: list[str], lote_id: str) -> pd.DataFrame:
    safe_items = items or ["UNSPECIFIED"]
    return pd.DataFrame(
        {
            key: safe_items,
            "label": safe_items,
            "description": [f"ANDY BI demo dimension value for {key}"] * len(safe_items),
            "lote_id": [lote_id] * len(safe_items),
        }
    )


def _frames_from_duckdb_placeholder(source_db: Path, lote_id: str) -> dict[str, pd.DataFrame]:
    if not source_db.exists():
        raise FileNotFoundError(str(source_db))
    raise NotImplementedError("local_duckdb_extraction_requires_repo_specific_mapping_review")


def _period_start(frames: Mapping[str, pd.DataFrame]) -> str:
    timestamps = _all_timestamps(frames)
    return timestamps.min().isoformat() if not timestamps.empty else ""


def _period_end(frames: Mapping[str, pd.DataFrame]) -> str:
    timestamps = _all_timestamps(frames)
    return timestamps.max().isoformat() if not timestamps.empty else ""


def _all_timestamps(frames: Mapping[str, pd.DataFrame]) -> pd.Series:
    series = [
        pd.to_datetime(frame["timestamp"], errors="coerce", utc=True).dt.tz_convert(None)
        for frame in frames.values()
        if "timestamp" in frame.columns
    ]
    if not series:
        return pd.Series(dtype="datetime64[ns]")
    return pd.concat(series).dropna()


def _cadence_summary(frames: Mapping[str, pd.DataFrame]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for frame in frames.values():
        for column in ("source_cadence", "cadencia_detectada"):
            if column in frame.columns:
                for value, count in frame[column].dropna().astype(str).value_counts().items():
                    counts[value] = counts.get(value, 0) + int(count)
    return counts


def _quality_flags(frames: Mapping[str, pd.DataFrame]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for frame in frames.values():
        if "quality_flag" in frame.columns:
            for value, count in frame["quality_flag"].dropna().astype(str).value_counts().items():
                counts[value] = counts.get(value, 0) + int(count)
    return counts


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def contract_payload() -> dict[str, Any]:
    return default_data_contract()


def known_tables() -> tuple[str, ...]:
    return tuple(table_contract_map())
