"""
XLSX preview widget for patamar analysis.

The widget renders the same sheet payload stored in
``PatamarAnalysisContext.sheets_preview`` so the desktop preview stays aligned
with the exported workbook.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from desktop_app.patamar_analysis_context import PatamarAnalysisContext
from desktop_app.qt_models import DataFrameTableModel
from desktop_app.theme import polish_widget


class PatamarXlsxPreviewWidget(QWidget):
    """Preview of the patamar workbook inside the desktop dashboard."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.context: Optional[PatamarAnalysisContext] = None

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Preview do XLSX a ser exportado")
        polish_widget(header, role="dashboardSubtleTitle")
        header.setStyleSheet("padding: 8px 4px 2px 4px;")
        layout.addWidget(header)

        header_hint = QLabel(
            "As abas abaixo espelham o mesmo conteudo que sera gravado no arquivo final."
        )
        header_hint.setWordWrap(True)
        polish_widget(header_hint, role="dashboardHint")
        layout.addWidget(header_hint)

        self.tab_widget = QTabWidget()

        self.table_resumo = self._create_table_view()
        self.table_metricas = self._create_table_view()
        self.table_diagnosticos = self._create_table_view()
        self.table_compliance = self._create_table_view()

        self.tab_widget.addTab(self.table_resumo, "Resumo por Turno")
        self.tab_widget.addTab(self.table_metricas, "Metricas Detalhadas")
        self.tab_widget.addTab(self.table_diagnosticos, "Interpretacao Operacional")
        self.tab_widget.addTab(self.table_compliance, "Conformidade de Tensao")
        layout.addWidget(self.tab_widget, 1)

    def _create_table_view(self) -> QTableView:
        table = QTableView()
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setVisible(False)
        return table

    def set_context(self, context: Optional[PatamarAnalysisContext]) -> None:
        """Load preview tables from the canonical context."""

        self.context = context
        if context is None or not context.sheets_preview:
            self.show_empty_state("Sem analise de patamar disponivel. Execute uma consulta primeiro.")
            return

        sheet_map = {
            "Resumo por Turno": self.table_resumo,
            "Métricas Detalhadas": self.table_metricas,
            "Metricas Detalhadas": self.table_metricas,
            "Interpretação Operacional": self.table_diagnosticos,
            "Interpretacao Operacional": self.table_diagnosticos,
            "Conformidade de Tensão": self.table_compliance,
            "Conformidade de Tensao": self.table_compliance,
        }

        for canonical_name, table_widget in sheet_map.items():
            df = context.sheets_preview.get(canonical_name)
            if df is not None:
                self._populate_table(table_widget, df)

        for table_widget in (
            self.table_resumo,
            self.table_metricas,
            self.table_diagnosticos,
            self.table_compliance,
        ):
            if table_widget.model() is None:
                self._populate_table(
                    table_widget,
                    pd.DataFrame({"Mensagem": ["Sem dados para esta aba no recorte atual."]}),
                )

    def _populate_table(self, table: QTableView, df: pd.DataFrame) -> None:
        model = DataFrameTableModel(df if not df.empty else pd.DataFrame({"Mensagem": ["Sem dados"]}))
        table.setModel(model)
        table.resizeColumnsToContents()

    def _set_message_on_all_tabs(self, column_name: str, message: str) -> None:
        model = DataFrameTableModel(pd.DataFrame({column_name: [message]}))
        for table in (
            self.table_resumo,
            self.table_metricas,
            self.table_diagnosticos,
            self.table_compliance,
        ):
            table.setModel(model)

    def show_empty_state(self, message: str) -> None:
        self._set_message_on_all_tabs("Status", message)

    def show_error_state(self, message: str) -> None:
        self._set_message_on_all_tabs("Erro", message)

    def clear(self) -> None:
        self.context = None
        self._set_message_on_all_tabs("Status", "-")
