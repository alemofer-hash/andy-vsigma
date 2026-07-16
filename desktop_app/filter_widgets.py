from __future__ import annotations

from typing import Iterable, List, Optional

from PySide6.QtCore import QSize, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from db.query_builder import EMPTY_FILTER_TOKEN
from desktop_app.layout_tokens import (
    CHECKABLE_LIST_HEIGHT,
    POPUP_MINIMUM_SIZE,
    SEARCH_FIELD_HEIGHT,
    apply_layout_frame,
)
from desktop_app.theme import polish_widget


def display_filter_value(value: object) -> str:
    return "(vazio)" if str(value) == EMPTY_FILTER_TOKEN else str(value)


class CheckableListPopup(QDialog):
    selection_changed = Signal(object)

    def __init__(self, parent: QWidget, *, placeholder: str, empty_text: str) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setModal(False)
        self.setMinimumSize(*POPUP_MINIMUM_SIZE)
        self._updating = False
        self._empty_text = empty_text

        layout = QVBoxLayout(self)
        apply_layout_frame(layout, "popup_root")

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(f"Buscar em {placeholder.lower()}...")
        self.search_edit.setMinimumHeight(SEARCH_FIELD_HEIGHT)
        layout.addWidget(self.search_edit)

        header_row = QHBoxLayout()
        apply_layout_frame(header_row, "popup_row")
        self.status_label = QLabel("0 disponiveis")
        header_row.addWidget(self.status_label)
        header_row.addStretch(1)
        self.select_all_button = QPushButton("Selecionar todos")
        self.select_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_all_button.setToolTip("Seleciona todas as opcoes disponiveis no contexto atual.")
        header_row.addWidget(self.select_all_button)
        self.clear_button = QPushButton("Limpar")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        header_row.addWidget(self.clear_button)
        layout.addLayout(header_row)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setUniformItemSizes(False)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        layout.addWidget(self.list_widget, stretch=1)

        self.empty_label = QLabel(self._empty_text)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)
        self.empty_label.hide()

        self.search_edit.textChanged.connect(self._apply_search)
        self.select_all_button.clicked.connect(self.select_all_checks)
        self.clear_button.clicked.connect(self.clear_checks)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        self.apply_theme()

    def apply_theme(self, theme_name: str | None = None) -> None:
        _ = theme_name
        polish_widget(self, role="multiSelectPopup")
        polish_widget(self.search_edit, role="popupSearch")
        polish_widget(self.status_label, role="popupStatus")
        polish_widget(self.select_all_button, role="popupActionButton")
        polish_widget(self.clear_button, role="popupActionButton")
        polish_widget(self.list_widget, role="popupList")
        polish_widget(self.empty_label, role="popupEmpty")

    def set_items(self, values: Iterable[object], *, checked_values: Optional[Iterable[object]] = None) -> None:
        selected = {str(v) for v in (checked_values or [])}
        self._updating = True
        try:
            self.list_widget.blockSignals(True)
            self.list_widget.clear()
            for raw in values:
                raw_text = str(raw)
                item = QListWidgetItem(display_filter_value(raw_text))
                item.setData(Qt.ItemDataRole.UserRole, raw_text)
                item.setToolTip(display_filter_value(raw_text))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if raw_text in selected else Qt.CheckState.Unchecked)
                self.list_widget.addItem(item)
            self._apply_search(self.search_edit.text())
            self._refresh_status()
        finally:
            self.list_widget.blockSignals(False)
            self._updating = False

    def checked_values(self) -> List[str]:
        values: List[str] = []
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            if item.checkState() == Qt.CheckState.Checked:
                values.append(str(item.data(Qt.ItemDataRole.UserRole)))
        return values

    def clear_checks(self) -> None:
        self._updating = True
        try:
            self.list_widget.blockSignals(True)
            for idx in range(self.list_widget.count()):
                self.list_widget.item(idx).setCheckState(Qt.CheckState.Unchecked)
            self._refresh_status()
        finally:
            self.list_widget.blockSignals(False)
            self._updating = False
        self.selection_changed.emit(None)

    def select_all_checks(self) -> None:
        if self.list_widget.count() == 0:
            return
        changed = False
        self._updating = True
        try:
            self.list_widget.blockSignals(True)
            for idx in range(self.list_widget.count()):
                item = self.list_widget.item(idx)
                if item.checkState() != Qt.CheckState.Checked:
                    item.setCheckState(Qt.CheckState.Checked)
                    changed = True
            self._refresh_status()
        finally:
            self.list_widget.blockSignals(False)
            self._updating = False
        if changed:
            self.selection_changed.emit(None)

    def is_updating(self) -> bool:
        return self._updating

    def _apply_search(self, text: str) -> None:
        needle = str(text or "").strip().lower()
        visible = 0
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            hay = item.text().lower()
            hidden = bool(needle) and needle not in hay
            item.setHidden(hidden)
            if not hidden:
                visible += 1
        self.empty_label.setVisible(visible == 0)
        self.empty_label.setText("Nenhum resultado para a busca." if needle and visible == 0 else self._empty_text)
        self._refresh_status()

    def _refresh_status(self) -> None:
        total = self.list_widget.count()
        selected = len(self.checked_values())
        visible = sum(1 for idx in range(total) if not self.list_widget.item(idx).isHidden())
        if total and selected == total:
            self.status_label.setText(f"Todos selecionados ({total}) | {visible}/{total} visiveis")
        else:
            self.status_label.setText(f"{selected} selecionado(s) | {visible}/{total} visiveis")
        self.select_all_button.setEnabled(total > 0 and selected < total)
        self.clear_button.setEnabled(selected > 0)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        if self._updating:
            return
        self._refresh_status()
        self.selection_changed.emit(item)


class CheckableListWidget(QWidget):
    itemChanged = Signal(object)

    def __init__(
        self,
        *,
        min_height: int = CHECKABLE_LIST_HEIGHT,
        placeholder: str = "Selecione...",
        empty_text: str = "Sem opcoes disponiveis.",
    ) -> None:
        super().__init__()
        self._updating = False
        self._collapsed_height = max(36, int(min_height))
        self._placeholder = placeholder
        self._empty_text = empty_text
        self._values: List[str] = []
        self._summary_override_text = ""
        self._summary_override_tooltip = ""
        self._change_notification_pending = False
        self._queued_change_payload: tuple[str, ...] = ()
        self._popup = CheckableListPopup(self, placeholder=placeholder, empty_text=empty_text)
        self._popup.selection_changed.connect(self._on_popup_changed)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(self._collapsed_height)
        self.setMaximumHeight(self._collapsed_height)

        layout = QVBoxLayout(self)
        apply_layout_frame(layout, "popup_row")

        top_row = QHBoxLayout()
        apply_layout_frame(top_row, "popup_row")
        self.summary_button = QPushButton(self._placeholder)
        self.summary_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.summary_button.setMinimumHeight(self._collapsed_height)
        self.summary_button.setMaximumHeight(self._collapsed_height)
        self.summary_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.clear_button = QToolButton()
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.setMinimumHeight(self._collapsed_height)
        self.clear_button.setMaximumHeight(self._collapsed_height)
        self.clear_button.setMinimumWidth(self._collapsed_height)
        self.clear_button.setMaximumWidth(self._collapsed_height)
        self.clear_button.setText("X")
        self.clear_button.setToolTip("Limpar selecao")
        top_row.addWidget(self.summary_button, stretch=1)
        top_row.addWidget(self.clear_button)
        layout.addLayout(top_row)

        self.summary_button.clicked.connect(self._open_popup)
        self.clear_button.clicked.connect(self.clear_checks)
        self.apply_theme()
        self._refresh_summary()

    def set_items(self, values: Iterable[object], *, checked_values: Optional[Iterable[object]] = None) -> None:
        self._values = [str(v) for v in values]
        self._updating = True
        try:
            self._popup.set_items(self._values, checked_values=checked_values)
            self._refresh_summary()
        finally:
            self._updating = False

    def checked_values(self) -> List[str]:
        return self._popup.checked_values()

    def clear_checks(self) -> None:
        self._popup.clear_checks()
        self._refresh_summary()

    def select_all_checks(self) -> None:
        self._popup.select_all_checks()
        self._refresh_summary()

    def set_summary_override(self, text: Optional[str], *, tooltip: Optional[str] = None) -> None:
        self._summary_override_text = str(text or "").strip()
        if tooltip is None:
            self._summary_override_tooltip = self._summary_override_text
        else:
            self._summary_override_tooltip = str(tooltip or "").strip()
        self._refresh_summary()

    def is_updating(self) -> bool:
        return self._updating or self._popup.is_updating()

    def setEnabled(self, enabled: bool) -> None:  # type: ignore[override]
        super().setEnabled(enabled)
        self.summary_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled and bool(self.checked_values()))
        self._refresh_summary()

    def sizeHint(self) -> QSize:  # type: ignore[override]
        clear_width = self._collapsed_height if self.clear_button.isVisible() else 0
        spacing = 6 if clear_width else 0
        width = max(280, self.summary_button.sizeHint().width() + clear_width + spacing)
        return QSize(width, self._collapsed_height)

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(220, self._collapsed_height)

    def apply_theme(self, theme_name: str | None = None) -> None:
        _ = theme_name
        polish_widget(self.summary_button, role="filterSummaryButton")
        polish_widget(self.clear_button, role="filterClearButton")
        self._popup.apply_theme()

    def _open_popup(self) -> None:
        if not self.isEnabled():
            return
        anchor = self.summary_button
        global_pos = anchor.mapToGlobal(anchor.rect().bottomLeft())
        popup_width = max(anchor.width() + self.clear_button.width() + 18, POPUP_MINIMUM_SIZE[0])
        self._popup.resize(popup_width, max(self._popup.height(), POPUP_MINIMUM_SIZE[1]))
        self._popup.move(global_pos)
        self._popup.show()
        self._popup.raise_()
        self._popup.activateWindow()

    def _refresh_summary(self) -> None:
        selected = self.checked_values()
        option_count = len(self._values)
        if not option_count:
            if self.isEnabled():
                self.summary_button.setText("Sem opcoes disponiveis")
                self.summary_button.setToolTip(self._empty_text)
            else:
                self.summary_button.setText(self._placeholder)
                self.summary_button.setToolTip(self._placeholder)
        elif not selected:
            if self._summary_override_text:
                self.summary_button.setText(self._summary_override_text)
                self.summary_button.setToolTip(self._summary_override_tooltip or self._summary_override_text)
            else:
                self.summary_button.setText(self._placeholder)
                self.summary_button.setToolTip(self._placeholder)
        elif len(selected) == 1:
            label = display_filter_value(selected[0])
            self.summary_button.setText(label)
            self.summary_button.setToolTip(label)
        elif len(selected) == option_count and option_count > 1:
            self.summary_button.setText(f"Todos ({option_count})")
            self.summary_button.setToolTip("\n".join(display_filter_value(v) for v in selected))
        else:
            preview = ", ".join(display_filter_value(v) for v in selected[:3])
            suffix = "..." if len(selected) > 3 else ""
            self.summary_button.setText(f"{len(selected)} selecionados")
            self.summary_button.setToolTip(f"{preview}{suffix}")
        if selected:
            self.summary_button.setToolTip("\n".join(display_filter_value(v) for v in selected))
        can_clear = self.isEnabled() and bool(selected)
        self.clear_button.setVisible(can_clear)
        self.clear_button.setEnabled(can_clear)

    def _queue_item_changed_notification(self) -> None:
        self._queued_change_payload = tuple(self.checked_values())
        if self._change_notification_pending:
            return
        self._change_notification_pending = True

        def _emit() -> None:
            self._change_notification_pending = False
            payload = {"selected_values": list(self._queued_change_payload)}
            if not self._updating:
                self.itemChanged.emit(payload)

        QTimer.singleShot(0, _emit)

    def _on_popup_changed(self, item: object) -> None:
        _ = item
        self._refresh_summary()
        if not self._updating:
            self._queue_item_changed_notification()
