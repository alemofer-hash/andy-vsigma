from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# --- NEW: installed-app runtime snapshot consumed by the desktop UI ---
@dataclass(frozen=True)
class DesktopRuntimeState:
    layout: Dict[str, Path]
    settings: Dict[str, Any]
    source_root: str
    source_reason: str
    source_mode: str
    source_exists: bool
    source_is_unc: bool
    source_file_count: int
    db_path: str
    db_exists: bool
    setup_required: bool
    settings_path: str
    last_index: Dict[str, Any]


# --- NEW: canonical desktop query filters, independent from Streamlit state ---
@dataclass
class QueryFilters:
    ano: Optional[int] = None
    anos_sel: List[int] = field(default_factory=list)
    meses_sel: List[int] = field(default_factory=list)
    dias_sel: List[int] = field(default_factory=list)
    se_sel: List[str] = field(default_factory=list)
    bay_sel: List[str] = field(default_factory=list)
    equipamento_sel: List[str] = field(default_factory=list)
    terminal_sel: List[str] = field(default_factory=list)
    vars_sel: List[str] = field(default_factory=list)
    ponto_id_like: str = ""
    advanced_equals: Dict[str, List[str]] = field(default_factory=dict)
    advanced_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)


# --- NEW: page result abstraction for the desktop table view ---
@dataclass(frozen=True)
class PageResult:
    total: int
    frame: pd.DataFrame


class ExportFormat(str, Enum):
    CSV_LONG = "csv_long"
    CSV_WIDE = "csv_wide"
    XLSX_DASH = "xlsx_dashboard"


# --- NEW: export options shared by audit/export operations in the desktop app ---
@dataclass
class ExportOptions:
    fmt: str | ExportFormat | None = None
    format: ExportFormat | str | None = None
    equips: List[str] = field(default_factory=list)
    t0: str = ""
    t1: str = ""
    vars_: List[str] = field(default_factory=list)
    limit_cap: Optional[int] = None
    agg: str = "max"
    time_floor: Optional[str] = None
    max_timestamps: int = 100_000
    equip_slots: int = 8
    var_slots: int = 6
    out_dir: str = ""
    out_name: str = ""
    template_path: Optional[str] = None
    destination_excel: bool = True
    split_timestamp_columns: bool = False
    split_timestamp_columns_xlsx: bool = False
    include_patamar: bool = False
    patamar_p_vars: Optional[List[str]] = None
    patamar_q_vars: Optional[List[str]] = None
    patamar_principal_p_key: Optional[str] = None
    patamar_principal_q_key: Optional[str] = None
    include_patamar_tabs: bool = False
    include_maneuver_tabs: bool = True

    def __post_init__(self) -> None:
        active_format = self.format or self.fmt or ExportFormat.XLSX_DASH
        if isinstance(active_format, ExportFormat):
            active_format = active_format.value
        self.fmt = str(active_format)
        if self.format is None:
            try:
                self.format = ExportFormat(self.fmt)
            except ValueError:
                self.format = self.fmt


# --- NEW: desktop export audit result for UI confirmation flows ---
@dataclass(frozen=True)
class ExportAuditResult:
    status: str
    metrics: Dict[str, Any]
    findings: List[Any]
