"""
Export actions widget for patamar analysis.

Provides a focused secondary action area for patamar-only export and glossary
access without competing with the main XLSX export flow.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from desktop_app.patamar_analysis_context import PatamarAnalysisContext
from desktop_app.theme import polish_widget


class PatamarExportActionsWidget(QFrame):
    """Direct export and glossary actions for the patamar dashboard."""

    export_requested = Signal()
    glossary_requested = Signal()

    def __init__(self, parent: Optional[QFrame] = None) -> None:
        super().__init__(parent)
        self.context: Optional[PatamarAnalysisContext] = None

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLineWidth(0)
        polish_widget(self, role="dashboardActionPanel")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Acoes rapidas do patamar")
        polish_widget(title, role="dashboardSubtleTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Use esta area para exportar somente a analise de patamar. "
            "O XLSX principal continua sendo o fluxo recomendado para consolidar tudo."
        )
        hint.setWordWrap(True)
        polish_widget(hint, role="dashboardHint")
        layout.addWidget(hint)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        self.export_button = QPushButton("Exportar somente patamar")
        self.export_button.setMinimumHeight(36)
        self.export_button.setMaximumWidth(240)
        polish_widget(self.export_button, role="primary")
        self.export_button.clicked.connect(self.export_requested.emit)

        self.glossary_button = QPushButton("Glossario de termos")
        self.glossary_button.setMinimumHeight(36)
        self.glossary_button.setMaximumWidth(190)
        polish_widget(self.glossary_button, role="secondary")
        self.glossary_button.clicked.connect(self.glossary_requested.emit)

        buttons_layout.addWidget(self.export_button)
        buttons_layout.addWidget(self.glossary_button)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.set_context(None)

    def set_context(self, context: Optional[PatamarAnalysisContext]) -> None:
        """Enable actions only when patamar data is available."""

        self.context = context
        has_data = bool(context and context.has_data())
        self.export_button.setEnabled(has_data)
        self.glossary_button.setEnabled(has_data)

        if has_data:
            self.set_status(
                "Analise pronta. Exporte so o patamar aqui ou use o XLSX principal para levar tudo junto.",
                tone="success",
            )
            return

        self.set_status(
            "Sem analise de patamar disponivel. Execute uma consulta valida primeiro.",
            tone="warning",
        )

    def set_status(self, message: str, tone: str = "info") -> None:
        """Update status message with theme-driven contrast."""

        self.status_label.setText(message)
        polish_widget(self.status_label, role="dashboardHint", tone=tone)
        self.status_label.setStyleSheet("font-size: 10px; font-style: italic;")

    def set_loading(self, is_loading: bool) -> None:
        """Disable actions while background work is running."""

        has_data = bool(self.context and self.context.has_data())
        self.export_button.setEnabled(has_data and not is_loading)
        self.glossary_button.setEnabled(has_data and not is_loading)

        if is_loading:
            self.set_status("Processando patamar...", tone="info")
            return
        if has_data:
            self.set_status("Analise pronta para exportacao.", tone="success")
            return
        self.set_status("Sem analise de patamar disponivel.", tone="warning")
