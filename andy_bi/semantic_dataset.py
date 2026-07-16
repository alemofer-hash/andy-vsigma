from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


DATASET_FORMATS = {"parquet", "csv", "both"}


def normalize_dataset_format(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in DATASET_FORMATS:
        raise ValueError(f"unsupported_dataset_format:{value}")
    return normalized


def dataset_file_name(table_name: str, fmt: str) -> str:
    if fmt not in {"parquet", "csv"}:
        raise ValueError(f"unsupported_table_format:{fmt}")
    return f"{table_name}.{fmt}"


def write_frame(frame: pd.DataFrame, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower()
    if suffix == ".parquet":
        frame.to_parquet(target, index=False)
    elif suffix == ".csv":
        frame.to_csv(target, index=False, encoding="utf-8-sig")
    else:
        raise ValueError(f"unsupported_dataset_file_suffix:{suffix}")
    return target


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("json_root_must_be_object")
    return payload


def load_dataset_frames(dataset_dir: str | Path) -> dict[str, pd.DataFrame]:
    root = Path(dataset_dir)
    frames: dict[str, pd.DataFrame] = {}
    for path in sorted(root.glob("*.parquet")):
        frames[path.stem] = pd.read_parquet(path)
    for path in sorted(root.glob("*.csv")):
        frames.setdefault(path.stem, pd.read_csv(path, encoding="utf-8-sig"))
    return frames
