"""
desktop_app/load_profile_service.py
Serviço de perfil de carga — consulta o lake e organiza os dados por turno.

SPRINT 1 — endurecimento HBits:
- preserva a boa decisão de usar a semântica do runner como fonte única de verdade;
- remove dependência rígida de um único nome de módulo;
- mantém fallback local estritamente equivalente apenas para testes/ausência de runner.
"""
from __future__ import annotations

import importlib
from typing import Dict, List, Optional, Sequence

import pandas as pd


def _try_import_module(module_names: Sequence[str]):
    for module_name in module_names:
        try:
            return importlib.import_module(module_name)
        except Exception:
            continue
    return None


_RUNNER_MODULES = (
    "andys_report_runner",
    "xlsx_report_runner",
    "report_runner",
    "desktop_app.andys_report_runner",
    "desktop_app.xlsx_report_runner",
)

_runner = _try_import_module(_RUNNER_MODULES)

if _runner is not None and all(hasattr(_runner, name) for name in ("SHIFT_DEFS", "SHIFT_ORDER", "MIDNIGHT_HOUR", "classify_shift")):
    SHIFT_DEFS = getattr(_runner, "SHIFT_DEFS")
    SHIFT_ORDER = getattr(_runner, "SHIFT_ORDER")
    MIDNIGHT_HOUR = getattr(_runner, "MIDNIGHT_HOUR")
    classify_shift = getattr(_runner, "classify_shift")
else:
    SHIFT_DEFS = [
        ("madrugada", 1, 5),
        ("manha", 6, 11),
        ("tarde", 12, 16),
        ("noite", 17, 23),
    ]
    SHIFT_ORDER = [s[0] for s in SHIFT_DEFS]
    MIDNIGHT_HOUR = 0

    def classify_shift(ts: pd.Timestamp) -> Optional[str]:
        h = int(ts.hour)
        if h == MIDNIGHT_HOUR:
            return None
        for name, start, end in SHIFT_DEFS:
            if start <= h <= end:
                return name
        return None


class LoadProfileEntry:
    __slots__ = ("equip", "shift", "ts_list", "values")

    def __init__(self, equip: str, shift: str) -> None:
        self.equip = equip
        self.shift = shift
        self.ts_list: List[pd.Timestamp] = []
        self.values: List[float] = []

    def add(self, ts: pd.Timestamp, value: float) -> None:
        self.ts_list.append(ts)
        self.values.append(value)

    @property
    def count(self) -> int:
        return len(self.values)


class LoadProfileService:
    def build_profile(
        self,
        df_agg: pd.DataFrame,
        *,
        equips: Optional[List[str]] = None,
        var: Optional[str] = None,
    ) -> Dict[str, Dict[str, LoadProfileEntry]]:
        if df_agg.empty:
            return {}

        df = df_agg.copy()
        df["_SHIFT"] = pd.to_datetime(df["_TS"]).map(classify_shift)
        df = df.dropna(subset=["_SHIFT"])

        if equips:
            df = df[df["_EQUIP"].isin(equips)]
        if var:
            df = df[df["_VAR"] == var]

        result: Dict[str, Dict[str, LoadProfileEntry]] = {}
        for _, row in df.iterrows():
            equip = str(row["_EQUIP"])
            shift = str(row["_SHIFT"])
            ts = pd.Timestamp(row["_TS"])
            val = row["_VAL"]
            if pd.isna(val):
                continue

            bucket = result.setdefault(equip, {})
            entry = bucket.setdefault(shift, LoadProfileEntry(equip=equip, shift=shift))
            entry.add(ts, float(val))

        return result

    def shift_summary(self, profile: Dict[str, Dict[str, LoadProfileEntry]]) -> pd.DataFrame:
        rows = []
        for equip, shifts in profile.items():
            for shift in SHIFT_ORDER:
                entry = shifts.get(shift)
                if entry is None or entry.count == 0:
                    continue
                vals = pd.Series(entry.values, dtype="float64")
                rows.append(
                    {
                        "equip": equip,
                        "shift": shift,
                        "count": entry.count,
                        "mean": round(float(vals.mean()), 1),
                        "min": round(float(vals.min()), 1),
                        "max": round(float(vals.max()), 1),
                    }
                )
        if not rows:
            return pd.DataFrame(columns=["equip", "shift", "count", "mean", "min", "max"])
        return pd.DataFrame(rows)
