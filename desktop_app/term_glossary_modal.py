"""
Glossary modal widget for displaying patamar term definitions.
"""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from desktop_app.patamar_analysis_context import TermDefinition
from desktop_app.theme import polish_widget


class TermGlossaryModal(QDialog):
    """Dialog displaying the canonical glossary used by the patamar analysis."""

    def __init__(
        self,
        glossary: Dict[str, TermDefinition],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.glossary = glossary
        self.setWindowTitle("Glossario: termos da analise de patamares")
        self.resize(800, 700)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel("Glossario de termos da analise de carga por patamar")
        polish_widget(header, role="dashboardTitle")
        layout.addWidget(header)

        subtitle = QLabel(
            "As definicoes abaixo refletem a logica computacional real usada no desktop. "
            "Cada termo inclui descricao operacional, base de calculo e exemplo quando disponivel."
        )
        subtitle.setWordWrap(True)
        polish_widget(subtitle, role="dashboardBody")
        layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(4, 4, 4, 4)

        for term_name, term_def in sorted(glossary.items()):
            content_layout.addWidget(self._create_term_block(term_name, term_def))

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

        footer_text = QLabel(
            "Use estas definicoes para interpretar os graficos, cards e planilhas exportadas."
        )
        footer_text.setWordWrap(True)
        polish_widget(footer_text, role="dashboardHint")
        layout.addWidget(footer_text)

        close_btn = QPushButton("Fechar")
        close_btn.setMaximumWidth(120)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _create_term_block(self, term_name: str, definition: TermDefinition) -> QFrame:
        frame = QFrame()
        polish_widget(frame, role="termCard")

        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel(f"{definition.icon} {term_name}")
        polish_widget(title_label, role="dashboardSubtleTitle")
        layout.addWidget(title_label)

        desc_label = QLabel(definition.description)
        desc_label.setWordWrap(True)
        polish_widget(desc_label, role="dashboardBody")
        layout.addWidget(desc_label)

        if definition.computational_basis:
            basis_label = QLabel(f"Calculo: {definition.computational_basis}")
            basis_label.setWordWrap(True)
            polish_widget(basis_label, role="termCode")
            layout.addWidget(basis_label)

        if definition.tooltip:
            tooltip_label = QLabel(definition.tooltip)
            tooltip_label.setWordWrap(True)
            polish_widget(tooltip_label, role="dashboardHint")
            layout.addWidget(tooltip_label)

        if definition.example:
            example_label = QLabel(f"Exemplo: {definition.example}")
            example_label.setWordWrap(True)
            polish_widget(example_label, role="termExample")
            layout.addWidget(example_label)

        return frame
