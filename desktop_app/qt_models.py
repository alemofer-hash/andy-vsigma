from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


# --- NEW: lightweight pandas-backed table model for the desktop results grid ---
class DataFrameTableModel(QAbstractTableModel):
    def __init__(self, frame: pd.DataFrame | None = None) -> None:
        super().__init__()
        self._frame = frame.copy() if frame is not None else pd.DataFrame()

    # --- NEW: replace the full table payload after a desktop query refresh ---
    def set_frame(self, frame: pd.DataFrame) -> None:
        self.beginResetModel()
        self._frame = frame.copy()
        self.endResetModel()

    # --- NEW: expose current DataFrame for diagnostics/export follow-up if needed ---
    def frame(self) -> pd.DataFrame:
        return self._frame.copy()

    # --- NEW: row count for Qt view contract ---
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        if parent.isValid():
            return 0
        return int(len(self._frame))

    # --- NEW: column count for Qt view contract ---
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        if parent.isValid():
            return 0
        return int(len(self._frame.columns))

    # --- NEW: cell/header rendering for the desktop table ---
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> str | None:
        if not index.isValid() or role not in {Qt.DisplayRole, Qt.ToolTipRole}:
            return None
        value = self._frame.iat[index.row(), index.column()]
        if pd.isna(value):
            return ""
        return str(value)

    # --- NEW: horizontal/vertical header labels from DataFrame metadata ---
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> str | None:
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            try:
                return str(self._frame.columns[section])
            except Exception:
                return ""
        return str(section + 1)
