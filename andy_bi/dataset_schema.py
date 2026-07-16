from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from .data_contract import table_contract_map


@dataclass(frozen=True)
class DatasetSchemaFinding:
    table: str
    code: str
    severity: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "table": self.table,
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }


def empty_frame_for_table(table_name: str) -> pd.DataFrame:
    contract = table_contract_map()[table_name]
    return pd.DataFrame({column.name: pd.Series(dtype="object") for column in contract.columns})


def validate_dataset_frames(frames: Mapping[str, pd.DataFrame]) -> list[DatasetSchemaFinding]:
    findings: list[DatasetSchemaFinding] = []
    contracts = table_contract_map()
    for table_name, contract in contracts.items():
        frame = frames.get(table_name)
        if frame is None:
            findings.append(_finding(table_name, "missing_table", "ERROR", "Tabela obrigatoria ausente."))
            continue
        columns = set(map(str, frame.columns))
        for column in contract.all_columns:
            if column not in columns:
                findings.append(_finding(table_name, f"missing_column:{column}", "ERROR", f"Coluna obrigatoria ausente: {column}."))
        for column in contract.required_columns:
            if column in frame.columns and frame[column].isna().any():
                findings.append(_finding(table_name, f"null_required_column:{column}", "ERROR", f"Coluna obrigatoria contem nulos: {column}."))
    return findings


def validation_status(findings: list[DatasetSchemaFinding]) -> str:
    return "blocked" if any(item.severity == "ERROR" for item in findings) else "valid"


def _finding(table: str, code: str, severity: str, message: str) -> DatasetSchemaFinding:
    return DatasetSchemaFinding(table=table, code=code, severity=severity, message=message)
