from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import pandas as pd


DEFAULT_FEEDER_VLL_KV = 23.1
ALS_REFERENCE_ENV_VAR = "ANDYS_ALS_REFERENCE_PATH"
ALS_REFERENCE_FILENAMES = ("ALs 2026.xlsx", "ALs_2026.xlsx", "ALs2026.xlsx")

_FEEDER_COLUMN_ALIASES = {
    "AL",
    "ALIMENTADOR",
    "BAY",
    "CIRCUITO",
    "CIRCUIT",
    "FEEDER",
    "FEEDERKEY",
}
_VOLTAGE_COLUMN_ALIASES = {
    "V",
    "KV",
    "VKV",
    "VKVBASE",
    "TENSAO",
    "TENSAONOMINAL",
    "TENSAOBASE",
    "TENSAOKV",
    "VLLKV",
    "VNOMINALKV",
}
_INVISIBLE_CHARS_RE = re.compile(r"[\u200b-\u200d\ufeff]")
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")
_NUMBER_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


@dataclass(frozen=True)
class FeederVoltageLookup:
    normalized_key: str
    feeder_value: str
    voltage_kv: float
    source: str


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_feeder_key(value: object) -> str:
    text = _strip_accents(str(value or ""))
    text = _INVISIBLE_CHARS_RE.sub("", text).strip().upper()
    if not text:
        return ""
    text = text.replace("\\", " ").replace("/", " ").replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_column_token(value: object) -> str:
    text = normalize_feeder_key(value)
    return _NON_ALNUM_RE.sub("", text)


def _iter_candidate_values(
    feeder_key: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> list[str]:
    candidates: list[str] = []
    if feeder_key:
        candidates.append(str(feeder_key))

    if metadata:
        for key_name in (
            "alimentador",
            "AL",
            "al",
            "BAY",
            "bay",
            "circuito",
            "circuit",
            "feeder",
            "feeder_key",
        ):
            value = metadata.get(key_name)
            if value:
                candidates.append(str(value))

        ponto_id = metadata.get("ponto_id") or metadata.get("key") or metadata.get("series_key")
        if ponto_id:
            parts = str(ponto_id).split("|")
            if len(parts) >= 2 and parts[1].strip():
                candidates.append(parts[1].strip())

    unique_values: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        normalized = normalize_feeder_key(value)
        if not normalized or normalized in seen:
            continue
        unique_values.append(value)
        seen.add(normalized)
    return unique_values


def iter_feeder_key_candidates(
    feeder_key: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> list[str]:
    return [normalize_feeder_key(value) for value in _iter_candidate_values(feeder_key=feeder_key, metadata=metadata)]


def _coerce_voltage_kv(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        numeric = float(value)
    else:
        matches = _NUMBER_RE.findall(str(value))
        if not matches:
            return None
        try:
            numeric = float(matches[0].replace(",", "."))
        except ValueError:
            return None

    if numeric <= 0:
        return None
    if numeric > 1000.0:
        numeric = numeric / 1000.0
    return float(numeric)


def _select_column(columns: Iterable[object], aliases: set[str]) -> Optional[str]:
    best_match: Optional[str] = None
    for raw_name in columns:
        token = _normalize_column_token(raw_name)
        if not token:
            continue
        if token in aliases:
            return str(raw_name)
        if best_match is None:
            if aliases is _FEEDER_COLUMN_ALIASES and ("ALIMENTADOR" in token or token.startswith("FEEDER")):
                best_match = str(raw_name)
            elif aliases is _VOLTAGE_COLUMN_ALIASES and ("TENSAO" in token or token.endswith("KV") or "VLL" in token):
                best_match = str(raw_name)
    return best_match


def load_feeder_voltage_entries(als_reference_path: Path) -> dict[str, FeederVoltageLookup]:
    reference_path = Path(als_reference_path).expanduser().resolve()
    if not reference_path.exists():
        raise FileNotFoundError(f"Referencia ALs nao encontrada: {reference_path}")

    entries: dict[str, FeederVoltageLookup] = {}
    workbook = pd.ExcelFile(reference_path)
    for sheet_name in workbook.sheet_names:
        frame = workbook.parse(sheet_name=sheet_name, dtype=object)
        if frame.empty:
            continue
        feeder_column = _select_column(frame.columns, _FEEDER_COLUMN_ALIASES)
        voltage_column = _select_column(frame.columns, _VOLTAGE_COLUMN_ALIASES)
        if not feeder_column or not voltage_column:
            continue

        for feeder_value, voltage_value in frame[[feeder_column, voltage_column]].itertuples(index=False, name=None):
            normalized_key = normalize_feeder_key(feeder_value)
            voltage_kv = _coerce_voltage_kv(voltage_value)
            if not normalized_key or voltage_kv is None:
                continue
            if normalized_key in entries:
                continue
            entries[normalized_key] = FeederVoltageLookup(
                normalized_key=normalized_key,
                feeder_value=str(feeder_value).strip(),
                voltage_kv=voltage_kv,
                source=f"{reference_path.name}:{sheet_name}",
            )
    return entries


def load_feeder_voltage_map(als_reference_path: Path) -> dict[str, float]:
    return {
        normalized_key: entry.voltage_kv
        for normalized_key, entry in load_feeder_voltage_entries(als_reference_path).items()
    }


def resolve_feeder_voltage_kv(
    feeder_key: str,
    als_reference_path: Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> float | None:
    if als_reference_path is None:
        return None
    entries = load_feeder_voltage_entries(als_reference_path)
    for normalized_candidate in iter_feeder_key_candidates(feeder_key=feeder_key, metadata=metadata):
        entry = entries.get(normalized_candidate)
        if entry is not None:
            return entry.voltage_kv
    return None


def find_als_reference_path(
    *,
    explicit_path: Path | str | None = None,
    runtime_settings: Mapping[str, Any] | None = None,
    extra_search_roots: Iterable[Path | str] = (),
) -> Path | None:
    configured_candidates: list[Path] = []
    for raw_value in (
        explicit_path,
        os.environ.get(ALS_REFERENCE_ENV_VAR),
        None if runtime_settings is None else runtime_settings.get("als_reference_path"),
    ):
        if not raw_value:
            continue
        candidate = Path(str(raw_value)).expanduser()
        configured_candidates.append(candidate)
        if candidate.exists():
            return candidate.resolve()

    for raw_root in extra_search_roots:
        if not raw_root:
            continue
        root = Path(str(raw_root)).expanduser()
        if not root.exists() or not root.is_dir():
            continue
        for filename in ALS_REFERENCE_FILENAMES:
            candidate = root / filename
            if candidate.exists():
                return candidate.resolve()
    return None
