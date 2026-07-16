"""
Load profile dashboard widget for visualization of hourly tier curves.

Displays temporal series, per-tier empirical quantile curves, P/Q association,
voltage compliance indicators, and operational extremes with interactive controls.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QSignalBlocker, QTimer, Qt, Signal
from PySide6.QtGui import QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from desktop_app.load_profile_service import (
    ExtremityPoint,
    LEGACY_LABEL,
    LEGACY_MODE,
    LoadProfileResult,
    MetricStats,
    PatamarCurve,
    VECTOR_LABEL,
    VECTOR_MODE,
)


TIER_ORDER = ("Madrugada", "Manha", "Tarde", "Noite")
TIER_COLORS = {
    "Madrugada": "#1f77b4",
    "Manha": "#2ca02c",
    "Tarde": "#ff7f0e",
    "Noite": "#d62728",
}

PRIMARY_MODE_COLORS = {
    VECTOR_MODE: "#1295d8",
    LEGACY_MODE: "#6b7280",
}

TEMPORAL_CANVAS_MIN_HEIGHT = 360
TIER_CANVAS_MIN_HEIGHT = 700
PQ_CANVAS_MIN_HEIGHT = 700
VOLTAGE_CANVAS_MIN_HEIGHT = 580
EXTREME_CARD_MIN_HEIGHT = 230
EXTREME_CARD_BREAKPOINT = 1120
MAX_SCATTER_POINTS = 1400


class TierExtremeCardWidget(QFrame):
    """Card displaying tier summary and min/max extremes."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumHeight(EXTREME_CARD_MIN_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.title_label = QLabel("Tier")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(self.title_label)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.summary_label)

        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(12)
        self.grid_layout.setVerticalSpacing(8)
        layout.addLayout(self.grid_layout)
        layout.addStretch(1)

    def set_curve(self, curve: PatamarCurve) -> None:
        """Update card with tier summary and extremes."""

        ratio_text = "tensao sem amostras validas"
        if curve.voltage_compliance_ratio is not None:
            ratio_text = f"tensao dentro: {curve.voltage_compliance_ratio * 100.0:.1f}%"

        metric_summary = f"{curve.metric_label} | media={self._fmt(curve.mean_value)} | desvio={self._fmt(curve.std_value)}"
        compliance_summary = (
            f"{ratio_text} | dentro={curve.voltage_within_count} | fora={curve.voltage_outside_count} | sem tensao={curve.voltage_unknown_count}"
        )
        self.title_label.setText(f"{curve.tier_name} | leitura operacional")
        self.summary_label.setText(f"{metric_summary}\n{compliance_summary}")

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        row = 0
        row = self._add_extreme_block("Minimo operacional", curve.min_extremity, row)
        self._add_extreme_block("Maximo operacional", curve.max_extremity, row)

    def _add_extreme_block(self, label: str, point: Optional[ExtremityPoint], row: int) -> int:
        title = QLabel(label)
        title.setStyleSheet("font-weight: 600; font-size: 11px;")
        self.grid_layout.addWidget(title, row, 0, 1, 2)
        row += 1

        value = QLabel(self._format_extremity(point))
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.grid_layout.addWidget(value, row, 0, 1, 2)
        return row + 1

    @staticmethod
    def _fmt(value: Optional[float], *, digits: int = 3) -> str:
        if value is None:
            return "-"
        return f"{value:.{digits}f}"

    @classmethod
    def _format_extremity(cls, point: Optional[ExtremityPoint]) -> str:
        """Format extremity point for display."""

        if point is None:
            return "Sem dado operacional associado a este extremo."

        lines: list[str] = []
        if point.timestamp is not None:
            ts_text = str(point.timestamp)
            if point.voltage_status:
                ts_text += f" | {point.voltage_status}"
            lines.append(ts_text)

        current_summary: list[str] = []
        if point.current_vector_pu is not None:
            current_summary.append(f"|I_res|={point.current_vector_pu:.3f} pu")
        if point.current_legacy_pu is not None:
            current_summary.append(f"Imax={point.current_legacy_pu:.3f} pu")
        if point.fp is not None:
            current_summary.append(f"FP={point.fp:.3f}")
        if point.stress_index is not None:
            current_summary.append(f"stress={point.stress_index:.3f}")
        if current_summary:
            lines.append(" | ".join(current_summary))

        phase_currents: list[str] = []
        if point.ia is not None:
            phase_currents.append(f"IA={point.ia:.2f} A")
        if point.ib is not None:
            phase_currents.append(f"IB={point.ib:.2f} A")
        if point.ic is not None:
            phase_currents.append(f"IC={point.ic:.2f} A")
        if phase_currents:
            lines.append(" | ".join(phase_currents))

        power_values: list[str] = []
        if point.p_pu is not None:
            power_values.append(f"P_pu={point.p_pu:.3f}")
        if point.q_pu is not None:
            power_values.append(f"Q_pu={point.q_pu:.3f}")
        if point.s_pu is not None:
            power_values.append(f"S_pu={point.s_pu:.3f}")
        if point.phi_deg is not None:
            power_values.append(f"phi={point.phi_deg:.1f} deg")
        if point.resultant_angle_deg is not None:
            power_values.append(f"ang(I_res)={point.resultant_angle_deg:.1f} deg")
        if power_values:
            lines.append(" | ".join(power_values))

        voltage_values: list[str] = []
        if point.v_min_pu is not None:
            voltage_values.append(f"Vmin={point.v_min_pu:.3f} pu")
        if point.v_max_pu is not None:
            voltage_values.append(f"Vmax={point.v_max_pu:.3f} pu")
        if point.v_min_v is not None:
            voltage_values.append(f"Vmin={point.v_min_v:.1f} V")
        if point.v_max_v is not None:
            voltage_values.append(f"Vmax={point.v_max_v:.1f} V")
        if voltage_values:
            lines.append(" | ".join(voltage_values))

        return "\n".join(lines) if lines else "Sem dado operacional associado a este extremo."


class LoadProfileDashboardWidget(QWidget):
    """Interactive visualization of load profile analysis."""

    state_changed = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.logger = logging.getLogger("andy.ui.load_profile")
        self.load_profile_result: Optional[LoadProfileResult] = None
        self._cut_min_pct = 0.0
        self._cut_max_pct = 100.0
        self._show_cuts = True
        self._show_points = False
        self._show_power_overlay = True
        self._show_alt_mode = True
        self._refresh_pending = False
        self._refresh_scheduled = False
        self.extremes_cards: Dict[str, TierExtremeCardWidget] = {}
        self._extreme_card_order: list[str] = []

        self._init_ui()

    def _init_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title = QLabel("Dashboard Vetorial de Patamar")
        title.setStyleSheet("font-weight: bold; font-size: 15px; padding: 2px 0px;")
        header_layout.addWidget(title)

        description = QLabel(
            "Leitura vetorial trifasica do recorte atual em pu, com curva de permanencia por turno, associacao P/Q, conformidade de tensao e extremos operacionais."
        )
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px;")
        header_layout.addWidget(description)

        self.base_summary_label = QLabel("Bases e referencias operacionais indisponiveis ate o primeiro recorte valido.")
        self.base_summary_label.setWordWrap(True)
        self.base_summary_label.setStyleSheet("font-size: 11px;")
        header_layout.addWidget(self.base_summary_label)
        layout.addWidget(header)

        self.temporal_group, temporal_layout = self._build_section_group(
            "Serie Temporal Principal",
            "O eixo principal usa a grandeza em pu do modo ativo e pode sobrepor o modo alternativo e P/Q normalizados.",
        )
        self.figure_temporal = Figure(figsize=(10, 4), dpi=100)
        self.canvas_temporal = FigureCanvas(self.figure_temporal)
        self.canvas_temporal.setMinimumHeight(TEMPORAL_CANVAS_MIN_HEIGHT)
        self.canvas_temporal.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        temporal_layout.addWidget(self.canvas_temporal)
        layout.addWidget(self.temporal_group)

        self.controls_box = self._build_controls()
        layout.addWidget(self.controls_box)

        self.tier_curve_group, tier_curve_layout = self._build_section_group(
            "Curvas por Patamar",
            "Cada turno mostra a curva empirica de permanencia em pu, com cortes percentuais e comparacao opcional com o modo alternativo.",
        )
        self.figure_tiers = Figure(figsize=(12, 8), dpi=100)
        self.canvas_tiers = FigureCanvas(self.figure_tiers)
        self.canvas_tiers.setMinimumHeight(TIER_CANVAS_MIN_HEIGHT)
        self.canvas_tiers.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        tier_curve_layout.addWidget(self.canvas_tiers)
        layout.addWidget(self.tier_curve_group)

        self.pq_group, pq_layout = self._build_section_group(
            "Associacao P e Q por Patamar",
            "Cada scatter mostra P_pu vs Q_pu, com cor dada por |I_res| para preservar a leitura do regime energetico junto do desequilibrio vetorial.",
        )
        self.figure_pq = Figure(figsize=(12, 8), dpi=100)
        self.canvas_pq = FigureCanvas(self.figure_pq)
        self.canvas_pq.setMinimumHeight(PQ_CANVAS_MIN_HEIGHT)
        self.canvas_pq.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        pq_layout.addWidget(self.canvas_pq)
        layout.addWidget(self.pq_group)

        self.voltage_group, voltage_layout = self._build_section_group(
            "Indicador de Tensao por Patamar",
            "Resumo por turno da conformidade frente a faixa otima 205-230 V e do intervalo em pu observado no recorte.",
        )
        self.figure_voltage = Figure(figsize=(12, 6), dpi=100)
        self.canvas_voltage = FigureCanvas(self.figure_voltage)
        self.canvas_voltage.setMinimumHeight(VOLTAGE_CANVAS_MIN_HEIGHT)
        self.canvas_voltage.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        voltage_layout.addWidget(self.canvas_voltage)
        layout.addWidget(self.voltage_group)

        self.extremes_group, extremes_layout = self._build_section_group(
            "Cards Operacionais por Patamar",
            "Cada card combina estatistica do turno com os registros reais dos extremos relevantes, sem obrigar o analista a voltar a tabela.",
        )
        self.extremes_container = QWidget()
        self.extremes_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.extremes_grid = QGridLayout(self.extremes_container)
        self.extremes_grid.setContentsMargins(0, 0, 0, 0)
        self.extremes_grid.setHorizontalSpacing(12)
        self.extremes_grid.setVerticalSpacing(12)
        extremes_layout.addWidget(self.extremes_container)
        layout.addWidget(self.extremes_group)

    def _build_section_group(self, title: str, body: str) -> tuple[QGroupBox, QVBoxLayout]:
        group = QGroupBox(title)
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 18, 16, 14)
        layout.setSpacing(10)

        description = QLabel(body)
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px;")
        layout.addWidget(description)
        return group, layout

    def _build_controls(self) -> QGroupBox:
        group = QGroupBox("Controles da Analise")
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QGridLayout(group)
        layout.setContentsMargins(16, 18, 16, 14)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        metric_mode_label = QLabel("Modo principal:")
        self.metric_mode_combo = QComboBox()
        self.metric_mode_combo.addItem("Vetorial trifasico", VECTOR_MODE)
        self.metric_mode_combo.addItem("Legado max fase", LEGACY_MODE)
        self.metric_mode_combo.currentIndexChanged.connect(self._on_metric_mode_changed)

        cut_min_label = QLabel("Corte minimo (%):")
        self.cut_min_spin = QSpinBox()
        self.cut_min_spin.setRange(0, 100)
        self.cut_min_spin.setValue(0)
        self.cut_min_spin.valueChanged.connect(self._on_cut_min_changed)

        cut_max_label = QLabel("Corte maximo (%):")
        self.cut_max_spin = QSpinBox()
        self.cut_max_spin.setRange(0, 100)
        self.cut_max_spin.setValue(100)
        self.cut_max_spin.valueChanged.connect(self._on_cut_max_changed)

        self.toggle_alt_mode_checkbox = QCheckBox("Comparar com modo alternativo")
        self.toggle_alt_mode_checkbox.setChecked(True)
        self.toggle_alt_mode_checkbox.stateChanged.connect(self._on_toggle_alt_mode)

        self.toggle_power_overlay_checkbox = QCheckBox("Overlay P_pu e Q_pu")
        self.toggle_power_overlay_checkbox.setChecked(True)
        self.toggle_power_overlay_checkbox.stateChanged.connect(self._on_toggle_power_overlay)

        self.toggle_cuts_checkbox = QCheckBox("Mostrar linhas de corte")
        self.toggle_cuts_checkbox.setChecked(True)
        self.toggle_cuts_checkbox.stateChanged.connect(self._on_toggle_cuts)

        self.toggle_points_checkbox = QCheckBox("Mostrar pontos")
        self.toggle_points_checkbox.setChecked(False)
        self.toggle_points_checkbox.stateChanged.connect(self._on_toggle_points)

        self.zoom_out_button = QPushButton("Zoom -")
        self.zoom_out_button.clicked.connect(self._on_zoom_out)

        self.zoom_in_button = QPushButton("Zoom +")
        self.zoom_in_button.clicked.connect(self._on_zoom_in)

        self.reset_zoom_button = QPushButton("Restaurar zoom")
        self.reset_zoom_button.clicked.connect(self._on_reset_zoom)

        layout.addWidget(metric_mode_label, 0, 0)
        layout.addWidget(self.metric_mode_combo, 0, 1, 1, 2)
        layout.addWidget(cut_min_label, 0, 3)
        layout.addWidget(self.cut_min_spin, 0, 4)
        layout.addWidget(cut_max_label, 0, 5)
        layout.addWidget(self.cut_max_spin, 0, 6)
        layout.addWidget(self.toggle_alt_mode_checkbox, 1, 0, 1, 2)
        layout.addWidget(self.toggle_power_overlay_checkbox, 1, 2, 1, 2)
        layout.addWidget(self.toggle_cuts_checkbox, 1, 4)
        layout.addWidget(self.toggle_points_checkbox, 1, 5, 1, 2)
        layout.addWidget(self.zoom_out_button, 2, 0)
        layout.addWidget(self.zoom_in_button, 2, 1)
        layout.addWidget(self.reset_zoom_button, 2, 2, 1, 2)
        layout.setColumnStretch(7, 1)
        return group
