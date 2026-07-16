from __future__ import annotations

import logging
import math
import os
import sys
import traceback
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional

import pandas as pd
from PySide6.QtCore import QThread, Qt, Signal, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTableView,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from andy_version import APP_NAME
from desktop_app.export_service import DesktopExportService
from desktop_app.models import DesktopRuntimeState, ExportFormat, ExportOptions, PageResult, QueryFilters
from desktop_app.qt_models import DataFrameTableModel
from desktop_app.query_service import DesktopQueryService, ORDER_OPTIONS
from desktop_app.runtime import DesktopRuntimeService


def _display_filter_value(value: object) -> str:
    text = str(value or "").strip()
    return text if text else "(vazio)"


# --- NEW: background execution wrapper for indexing/export tasks in the desktop UI ---
class FunctionWorker(QThread):
    success = Signal(object)
    failure = Signal(str)

    def __init__(self, fn: Callable[[], object], *, logger: Optional[logging.Logger] = None) -> None:
        super().__init__()
        self._fn = fn
        self._logger = logger or logging.getLogger("andy.desktop")

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # pragma: no cover - exercised through signal behavior
            self._logger.exception("Desktop background task failed.")
            details = "".join(traceback.format_exception(exc))
            self.failure.emit(details)
            return
        self.success.emit(result)


# --- NEW: reusable checkable list widget for multi-select desktop filters ---
class CheckableListWidget(QListWidget):
    def __init__(self, *, min_height: int = 110) -> None:
        super().__init__()
        self.setMinimumHeight(min_height)
        self.setAlternatingRowColors(True)
        self._updating = False

    def set_items(self, values: Iterable[object], *, checked_values: Optional[Iterable[object]] = None) -> None:
        selected = {str(v) for v in (checked_values or [])}
        self._updating = True
        try:
            self.blockSignals(True)
            self.clear()
            for raw in values:
                text = str(raw)
                item = QListWidgetItem(_display_filter_value(text))
                item.setData(Qt.ItemDataRole.UserRole, text)
                item.setToolTip(_display_filter_value(text))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if text in selected else Qt.CheckState.Unchecked)
                self.addItem(item)
        finally:
            self.blockSignals(False)
            self._updating = False

    def checked_values(self) -> List[str]:
        values: List[str] = []
        for idx in range(self.count()):
            item = self.item(idx)
            if item.checkState() == Qt.CheckState.Checked:
                values.append(str(item.data(Qt.ItemDataRole.UserRole) or item.text()))
        return values

    def clear_checks(self) -> None:
        self._updating = True
        try:
            self.blockSignals(True)
            for idx in range(self.count()):
                self.item(idx).setCheckState(Qt.CheckState.Unchecked)
        finally:
            self.blockSignals(False)
            self._updating = False

    def is_updating(self) -> bool:
        return self._updating


class ExportPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QFormLayout(self)
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItem("XLSX dashboard", ExportFormat.XLSX_DASH)
        self._fmt_combo.addItem("CSV LONG", ExportFormat.CSV_LONG)
        self._fmt_combo.addItem("CSV WIDE", ExportFormat.CSV_WIDE)
        self._tmpl_path_edit = QLineEdit()
        self._patamar_chk = QCheckBox("Incluir patamar")
        self._patamar_p_vars_edit = QLineEdit()
        self._patamar_q_vars_edit = QLineEdit()
        self._patamar_p_key_edit = QLineEdit()
        self._patamar_q_key_edit = QLineEdit()

        layout.addRow("Formato", self._fmt_combo)
        layout.addRow("Template XLSX", self._tmpl_path_edit)
        layout.addRow("", self._patamar_chk)
        layout.addRow("Variaveis P", self._patamar_p_vars_edit)
        layout.addRow("Variaveis Q", self._patamar_q_vars_edit)
        layout.addRow("Chave principal P", self._patamar_p_key_edit)
        layout.addRow("Chave principal Q", self._patamar_q_key_edit)

        self._patamar_chk.toggled.connect(self._set_patamar_controls_enabled)
        self._set_patamar_controls_enabled(False)

    def _set_patamar_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self._patamar_p_vars_edit,
            self._patamar_q_vars_edit,
            self._patamar_p_key_edit,
            self._patamar_q_key_edit,
        ):
            widget.setEnabled(bool(enabled))

    def validate_readiness(self) -> Optional[str]:
        template = self._tmpl_path_edit.text().strip()
        if template and not Path(template).exists():
            return "Template XLSX nao encontrado."
        if self._patamar_chk.isChecked():
            if not self._patamar_p_vars_edit.text().strip():
                return "Informe ao menos uma variavel P para patamar."
            if not self._patamar_q_vars_edit.text().strip():
                return "Informe ao menos uma variavel Q para patamar."
        return None

    def collect_options(self, base: ExportOptions) -> ExportOptions:
        active_format = self._fmt_combo.currentData()
        return replace(
            base,
            format=active_format,
            fmt=active_format.value if isinstance(active_format, ExportFormat) else str(active_format),
            template_path=self._tmpl_path_edit.text().strip() or None,
            include_patamar=self._patamar_chk.isChecked(),
            patamar_p_vars=_split_csv(self._patamar_p_vars_edit.text()),
            patamar_q_vars=_split_csv(self._patamar_q_vars_edit.text()),
            patamar_principal_p_key=self._patamar_p_key_edit.text().strip() or None,
            patamar_principal_q_key=self._patamar_q_key_edit.text().strip() or None,
        )


def _split_csv(text: str) -> List[str]:
    return [item.strip() for item in str(text or "").split(",") if item.strip()]


# --- NEW: native desktop main window for setup, status, querying and exports ---
class AndyDesktopWindow(QMainWindow):
    def __init__(self, runtime_service: Optional[DesktopRuntimeService] = None) -> None:
        super().__init__()
        self.runtime_service = runtime_service or DesktopRuntimeService()
        self.logger = self.runtime_service.logger
        self.runtime_state: Optional[DesktopRuntimeState] = None
        self.query_service: Optional[DesktopQueryService] = None
        self.export_service: Optional[DesktopExportService] = None
        self._catalog_by_month = pd.DataFrame()
        self._catalog_years: List[int] = []
        self._current_page = 1
        self._page_size = 200
        self._month_user_touched = False
        self._month_list_updating = False
        self._loading_catalog = False
        self._worker: Optional[FunctionWorker] = None

        self.setWindowTitle(APP_NAME)
        self.resize(1600, 940)
        self.setMinimumSize(1280, 760)

        self._build_ui()
        self._build_toolbar()
        self._connect_signals()
        self.reload_runtime_state()

    # --- NEW: construct the full native window layout ---
    def _build_ui(self) -> None:
        self.central_container = QWidget()
        central_layout = QGridLayout(self.central_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        central_layout.addWidget(self.stack, 0, 0)

        self.loading_overlay = QFrame(self.central_container)
        self.loading_overlay.setObjectName("loadingOverlay")
        self.loading_overlay.setStyleSheet(
            "#loadingOverlay { background-color: rgba(0, 0, 0, 145); border: 0; } "
            "#loadingOverlay QLabel { color: white; font-size: 16px; font-weight: 600; }"
        )
        overlay_layout = QVBoxLayout(self.loading_overlay)
        overlay_layout.addStretch(1)
        self.loading_label = QLabel("Processando...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_progress = QProgressBar()
        self.loading_progress.setRange(0, 0)
        self.loading_progress.setTextVisible(False)
        self.loading_progress.setFixedWidth(260)
        progress_row = QHBoxLayout()
        progress_row.addStretch(1)
        progress_row.addWidget(self.loading_progress)
        progress_row.addStretch(1)
        overlay_layout.addWidget(self.loading_label)
        overlay_layout.addLayout(progress_row)
        overlay_layout.addStretch(1)
        central_layout.addWidget(self.loading_overlay, 0, 0)
        self.loading_overlay.hide()

        self.setCentralWidget(self.central_container)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.setup_page = self._build_setup_page()
        self.main_page = self._build_main_page()
        self.stack.addWidget(self.setup_page)
        self.stack.addWidget(self.main_page)

    # --- NEW: top-level desktop toolbar for maintenance actions ---
    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Acoes")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.action_refresh = QAction("Atualizar", self)
        self.action_reindex = QAction("Reindexar", self)
        self.action_change_source = QAction("Alterar fonte", self)
        self.action_open_exports = QAction("Abrir exports", self)
        self.action_open_logs = QAction("Abrir logs", self)

        for action in (
            self.action_refresh,
            self.action_reindex,
            self.action_change_source,
            self.action_open_exports,
            self.action_open_logs,
        ):
            toolbar.addAction(action)

    # --- NEW: first-run/setup page with explicit source configuration flow ---
    def _build_setup_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title = QLabel("Configuracao inicial")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(title)

        intro = QLabel(
            f"O {APP_NAME} precisa da pasta real onde as planilhas ficam armazenadas. "
            "Informe a pasta, salve e inicie a indexacao local."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form_box = QGroupBox("Fonte de dados")
        form = QGridLayout(form_box)
        form.addWidget(QLabel("Pasta real das planilhas"), 0, 0)
        self.setup_source_edit = QLineEdit()
        self.setup_source_edit.setPlaceholderText(r"\\servidor\compartilhamento\ELIPSE")
        form.addWidget(self.setup_source_edit, 0, 1)
        self.setup_browse_button = QPushButton("Procurar...")
        form.addWidget(self.setup_browse_button, 0, 2)
        layout.addWidget(form_box)

        info_box = QGroupBox("Runtime local")
        info_form = QFormLayout(info_box)
        self.setup_settings_path = self._make_value_label()
        self.setup_workspace_path = self._make_value_label()
        self.setup_db_path = self._make_value_label()
        self.setup_inbox_path = self._make_value_label()
        info_form.addRow("Settings", self.setup_settings_path)
        info_form.addRow("Workspace", self.setup_workspace_path)
        info_form.addRow("DuckDB local", self.setup_db_path)
        info_form.addRow("Pasta local opcional", self.setup_inbox_path)
        layout.addWidget(info_box)

        button_row = QHBoxLayout()
        self.setup_save_button = QPushButton("Salvar fonte e indexar")
        self.setup_save_button.setDefault(True)
        self.setup_inbox_button = QPushButton("Usar pasta local de entrada")
        self.setup_reload_button = QPushButton("Recarregar status")
        button_row.addWidget(self.setup_save_button)
        button_row.addWidget(self.setup_inbox_button)
        button_row.addWidget(self.setup_reload_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.setup_message = QTextEdit()
        self.setup_message.setReadOnly(True)
        self.setup_message.setMaximumHeight(160)
        self.setup_message.setPlaceholderText("Mensagens de setup e indexacao aparecem aqui.")
        layout.addWidget(self.setup_message)
        layout.addStretch(1)
        return page

    # --- NEW: operational page with status, filters, table and exports ---
    def _build_main_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        status_box = QGroupBox("Status do aplicativo")
        status_grid = QGridLayout(status_box)
        self.status_source = self._make_value_label()
        self.status_source_reason = self._make_value_label()
        self.status_source_meta = self._make_value_label()
        self.status_db = self._make_value_label()
        self.status_settings = self._make_value_label()
        self.status_last_index = self._make_value_label()
        self.status_catalog = self._make_value_label()
        status_grid.addWidget(QLabel("Fonte ativa"), 0, 0)
        status_grid.addWidget(self.status_source, 0, 1)
        status_grid.addWidget(QLabel("Origem da fonte"), 1, 0)
        status_grid.addWidget(self.status_source_reason, 1, 1)
        status_grid.addWidget(QLabel("Diagnostico da fonte"), 2, 0)
        status_grid.addWidget(self.status_source_meta, 2, 1)
        status_grid.addWidget(QLabel("DuckDB local"), 0, 2)
        status_grid.addWidget(self.status_db, 0, 3)
        status_grid.addWidget(QLabel("Settings"), 1, 2)
        status_grid.addWidget(self.status_settings, 1, 3)
        status_grid.addWidget(QLabel("Ultima indexacao"), 2, 2)
        status_grid.addWidget(self.status_last_index, 2, 3)
        status_grid.addWidget(QLabel("Catalogo"), 3, 0)
        status_grid.addWidget(self.status_catalog, 3, 1, 1, 3)
        layout.addWidget(status_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        filter_panel = QWidget()
        filter_layout = QVBoxLayout(filter_panel)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(10)

        filter_box = QGroupBox("Filtros")
        filter_form = QFormLayout(filter_box)
        self.year_combo = QComboBox()
        self.month_list = CheckableListWidget()
        self.se_list = CheckableListWidget()
        self.bay_list = CheckableListWidget()
        self.equip_list = CheckableListWidget()
        self.terminal_list = CheckableListWidget()
        self.var_list = CheckableListWidget(min_height=140)
        self.point_like_edit = QLineEdit()
        self.point_like_edit.setPlaceholderText("Filtro parcial em ponto_id")
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["100", "200", "500", "1000"])
        self.page_size_combo.setCurrentText("200")
        self.order_combo = QComboBox()
        for label in ORDER_OPTIONS:
            self.order_combo.addItem(label)

        filter_form.addRow("Ano", self.year_combo)
        filter_form.addRow("Mes(es)", self.month_list)
        filter_form.addRow("SE", self.se_list)
        filter_form.addRow("BAY", self.bay_list)
        filter_form.addRow("Equipamento", self.equip_list)
        filter_form.addRow("Terminal", self.terminal_list)
        filter_form.addRow("Variaveis", self.var_list)
        self.point_like_label = QLabel("ponto_id LIKE")
        self.page_size_label = QLabel("Page size")
        self.order_label = QLabel("Ordenacao")
        filter_form.addRow(self.point_like_label, self.point_like_edit)
        filter_form.addRow(self.page_size_label, self.page_size_combo)
        filter_form.addRow(self.order_label, self.order_combo)
        for widget in (
            self.point_like_label,
            self.point_like_edit,
            self.page_size_label,
            self.page_size_combo,
            self.order_label,
            self.order_combo,
        ):
            widget.hide()
        filter_layout.addWidget(filter_box)

        filter_buttons = QHBoxLayout()
        self.refresh_options_button = QPushButton("Atualizar opcoes")
        self.apply_filters_button = QPushButton("Consultar")
        self.clear_filters_button = QPushButton("Resetar")
        filter_buttons.addWidget(self.refresh_options_button)
        filter_buttons.addWidget(self.apply_filters_button)
        filter_buttons.addWidget(self.clear_filters_button)
        filter_layout.addLayout(filter_buttons)
        for widget in (self.refresh_options_button, self.apply_filters_button, self.clear_filters_button):
            widget.hide()

        maintenance_box = QGroupBox("Manutencao")
        self.maintenance_box = maintenance_box
        maintenance_layout = QVBoxLayout(maintenance_box)
        self.reindex_button = QPushButton("Reindex local DB")
        self.change_source_button = QPushButton("Alterar fonte")
        self.open_exports_button = QPushButton("Abrir pasta de exports")
        self.open_logs_button = QPushButton("Abrir pasta de logs")
        maintenance_layout.addWidget(self.reindex_button)
        maintenance_layout.addWidget(self.change_source_button)
        maintenance_layout.addWidget(self.open_exports_button)
        maintenance_layout.addWidget(self.open_logs_button)
        filter_layout.addWidget(maintenance_box)
        maintenance_box.hide()
        filter_layout.addStretch(1)

        results_panel = QWidget()
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(10)

        overview_box = QGroupBox("Visao geral")
        overview_form = QFormLayout(overview_box)
        self.overview_label = self._make_value_label()
        self.period_label = self._make_value_label()
        self.top_vars_label = self._make_value_label()
        overview_form.addRow("Resumo", self.overview_label)
        overview_form.addRow("Periodo indexado", self.period_label)
        overview_form.addRow("Top variaveis", self.top_vars_label)
        results_layout.addWidget(overview_box)

        self.table_model = DataFrameTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.table_view, stretch=1)

        paging_row = QHBoxLayout()
        self.prev_page_button = QPushButton("Pagina anterior")
        self.next_page_button = QPushButton("Proxima pagina")
        self.page_label = QLabel("Pagina 0 de 0")
        self.page_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        paging_row.addWidget(self.prev_page_button)
        paging_row.addWidget(self.next_page_button)
        paging_row.addWidget(self.page_label)
        results_layout.addLayout(paging_row)

        export_box = QGroupBox("Exports")
        export_row = QHBoxLayout(export_box)
        self.export_csv_long_button = QPushButton("Exportar CSV LONG")
        self.export_csv_wide_button = QPushButton("Exportar CSV WIDE")
        self.export_xlsx_button = QPushButton("Gerar XLSX dashboard")
        export_row.addWidget(self.export_csv_long_button)
        export_row.addWidget(self.export_csv_wide_button)
        export_row.addWidget(self.export_xlsx_button)
        results_layout.addWidget(export_box)

        splitter.addWidget(filter_panel)
        splitter.addWidget(results_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 1180])
        layout.addWidget(splitter, stretch=1)

        self.main_message = QTextEdit()
        self.main_message.setReadOnly(True)
        self.main_message.setMaximumHeight(140)
        self.main_message.setPlaceholderText("Mensagens operacionais aparecem aqui.")
        layout.addWidget(self.main_message)
        return page

    # --- NEW: signal wiring for the desktop controls ---
    def _connect_signals(self) -> None:
        self.setup_browse_button.clicked.connect(self.choose_source_folder)
        self.setup_save_button.clicked.connect(self.save_source_and_index)
        self.setup_inbox_button.clicked.connect(self.activate_local_inbox_mode)
        self.setup_reload_button.clicked.connect(self.reload_runtime_state)

        self.action_refresh.triggered.connect(self.reload_runtime_state)
        self.action_reindex.triggered.connect(self.reindex_database)
        self.action_change_source.triggered.connect(self.show_setup_page)
        self.action_open_exports.triggered.connect(lambda: self._open_path(self._exports_path()))
        self.action_open_logs.triggered.connect(lambda: self._open_path(self._logs_path()))

        self.year_combo.currentIndexChanged.connect(self.on_year_changed)
        self.month_list.itemChanged.connect(self.on_month_item_changed)
        self.refresh_options_button.clicked.connect(self.refresh_context_options)
        self.apply_filters_button.clicked.connect(self.run_query)
        self.clear_filters_button.clicked.connect(self.reset_filters)
        self.reindex_button.clicked.connect(self.reindex_database)
        self.change_source_button.clicked.connect(self.show_setup_page)
        self.open_exports_button.clicked.connect(lambda: self._open_path(self._exports_path()))
        self.open_logs_button.clicked.connect(lambda: self._open_path(self._logs_path()))
        self.prev_page_button.clicked.connect(self.previous_page)
        self.next_page_button.clicked.connect(self.next_page)
        self.export_csv_long_button.clicked.connect(self.export_csv_long)
        self.export_csv_wide_button.clicked.connect(self.export_csv_wide)
        self.export_xlsx_button.clicked.connect(self.export_xlsx_dashboard)

    # --- NEW: common selectable label style for paths and diagnostics ---
    def _make_value_label(self) -> QLabel:
        label = QLabel("-")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    # --- NEW: simple appended log panel for setup or operational messages ---
    def _append_message(self, target: QTextEdit, message: str) -> None:
        cleaned = str(message or "").strip()
        if not cleaned:
            return
        target.append(cleaned)
        self.status_bar.showMessage(cleaned, 8000)

    # --- NEW: user-visible busy state for background tasks ---
    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.setup_page.setEnabled(not busy)
        self.main_page.setEnabled(not busy)
        self.action_refresh.setEnabled(not busy)
        self.action_reindex.setEnabled(not busy)
        self.action_change_source.setEnabled(not busy)
        if busy:
            self.loading_label.setText(message or "Processando...")
            self.loading_overlay.show()
            self.loading_overlay.raise_()
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.status_bar.showMessage(message or "Processando...")
        else:
            self.loading_overlay.hide()
            QApplication.restoreOverrideCursor()
            self.status_bar.clearMessage()

    # --- NEW: source chooser that supports local and UNC folders ---
    def choose_source_folder(self) -> None:
        current = self.setup_source_edit.text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Selecione a pasta de planilhas", current)
        if selected:
            self.setup_source_edit.setText(selected)

    # --- NEW: refresh full runtime snapshot and switch between setup/main pages ---
    def reload_runtime_state(self) -> None:
        self.logger.info("Desktop UI: reloading runtime state.")
        state = self.runtime_service.load_state(bootstrap_if_ready=True)
        self._apply_runtime_state(state)
        if state.setup_required:
            self.stack.setCurrentWidget(self.setup_page)
            self._append_message(
                self.setup_message,
                "Nenhuma fonte valida configurada. Informe a pasta real das planilhas ou selecione o modo de pasta local.",
            )
            return
        self.stack.setCurrentWidget(self.main_page)
        self.load_operational_catalog(initial=True)

    # --- NEW: project runtime state into setup/main status widgets ---
    def _apply_runtime_state(self, state: DesktopRuntimeState) -> None:
        self.runtime_state = state
        self.query_service = DesktopQueryService(state.db_path)
        self.export_service = DesktopExportService(state)

        last_index = state.last_index or {}
        last_text = "sem execucao registrada"
        if last_index:
            last_text = (
                f"status={last_index.get('status', '')} | "
                f"arquivos={last_index.get('source_file_count', '')} | "
                f"quando={last_index.get('indexed_at', '')}"
            )
            if str(last_index.get("error", "")).strip():
                last_text += f" | erro={last_index.get('error', '')}"

        source_meta = (
            f"existe={'sim' if state.source_exists else 'nao'} | "
            f"arquivos candidatos={state.source_file_count} | "
            f"UNC={'sim' if state.source_is_unc else 'nao'} | "
            f"modo={state.source_mode}"
        )
        db_meta = f"{state.db_path} | existe={'sim' if state.db_exists else 'nao'}"

        self.setup_source_edit.setText(state.source_root if state.source_mode != "local_inbox" else "")
        self.setup_settings_path.setText(state.settings_path)
        self.setup_workspace_path.setText(str(state.layout["workspace"]))
        self.setup_db_path.setText(state.db_path)
        self.setup_inbox_path.setText(str(state.layout["source"]))

        self.status_source.setText(state.source_root or str(state.layout["source"]))
        self.status_source_reason.setText(state.source_reason or "(sem resolucao)")
        self.status_source_meta.setText(source_meta)
        self.status_db.setText(db_meta)
        self.status_settings.setText(state.settings_path)
        self.status_last_index.setText(last_text)
        self.status_catalog.setText("-")

    # --- NEW: load catalog metadata and initialize filter widgets for the desktop screen ---
    def load_operational_catalog(self, *, initial: bool = False) -> None:
        if self.runtime_state is None or self.query_service is None:
            return
        if self._loading_catalog:
            return
        self._loading_catalog = True
        try:
            self.query_service.validate_ready()
            overview, by_month, vars_df, _top_equips = self.query_service.load_overview()
            cfg, manifest_df = self.query_service.load_ingestion_metadata(str(self.runtime_state.layout["lake"]))
            self._catalog_by_month = by_month
            self._catalog_years = sorted({int(v) for v in by_month["ano"].tolist()}) if not by_month.empty else []

            if overview.empty or int(overview.iloc[0].get("rows_total", 0) or 0) <= 0:
                self.overview_label.setText("Banco local inicializado, mas ainda sem medicoes indexadas.")
                self.period_label.setText("Sem periodo indexado.")
                self.top_vars_label.setText("Sem variaveis indexadas.")
                manifest_count = len(manifest_df.index) if not manifest_df.empty else 0
                self.status_catalog.setText(
                    f"rows_total=0 | manifesto={manifest_count} arquivo(s) | fonte ativa={self.runtime_state.source_root}"
                )
                self._clear_filter_widgets()
                self.table_model.set_frame(pd.DataFrame())
                self.page_label.setText("Pagina 0 de 0")
                return

            row = overview.iloc[0]
            self.overview_label.setText(
                f"rows_total={int(row.get('rows_total', 0) or 0)} | "
                f"equipamentos={int(row.get('equips_distintos', 0) or 0)} | "
                f"variaveis={int(row.get('vars_distintas', 0) or 0)}"
            )
            self.period_label.setText(f"{row.get('ts_min', '')} -> {row.get('ts_max', '')}")
            if vars_df.empty:
                self.top_vars_label.setText("Sem resumo de variaveis.")
            else:
                preview = []
                for item in vars_df.head(6).itertuples(index=False):
                    preview.append(f"{item.var} ({int(item.rows)})")
                self.top_vars_label.setText(", ".join(preview))

            manifest_count = len(manifest_df.index) if not manifest_df.empty else 0
            source_cfg = cfg.get("source_root", "") if isinstance(cfg, dict) else ""
            self.status_catalog.setText(
                f"rows_total={int(row.get('rows_total', 0) or 0)} | "
                f"manifesto={manifest_count} arquivo(s) | "
                f"source_config={source_cfg or self.runtime_state.source_root}"
            )

            self._initialize_filter_defaults(by_month=by_month, initial=initial)
            self.refresh_context_options()
            self.run_query(reset_page=True)
        except Exception as exc:
            self.table_model.set_frame(pd.DataFrame())
            self.page_label.setText("Pagina 0 de 0")
            self._append_message(self.main_message, f"Falha ao carregar catalogo local: {exc}")
        finally:
            self._loading_catalog = False

    # --- NEW: clear filter widgets when the local DB is still empty ---
    def _clear_filter_widgets(self) -> None:
        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        self.year_combo.blockSignals(False)
        self._month_list_updating = True
        try:
            self.month_list.set_items([])
        finally:
            self._month_list_updating = False
        for widget in (self.se_list, self.bay_list, self.equip_list, self.terminal_list, self.var_list):
            widget.set_items([])

    # --- NEW: year/month initialization with one-time default and explicit-clear preservation ---
    def _initialize_filter_defaults(self, *, by_month: pd.DataFrame, initial: bool) -> None:
        latest_year, latest_month = self.query_service.latest_available_year_month(by_month)
        current_year = self.current_year()
        years = sorted({int(v) for v in by_month["ano"].tolist()})

        self.year_combo.blockSignals(True)
        try:
            self.year_combo.clear()
            for year in years:
                self.year_combo.addItem(str(year), year)
            target_year = current_year if current_year in years else latest_year
            idx = self.year_combo.findData(target_year)
            if idx >= 0:
                self.year_combo.setCurrentIndex(idx)
        finally:
            self.year_combo.blockSignals(False)

        if initial:
            self._month_user_touched = False
        valid_months = self.query_service.months_for_year(by_month, self.current_year() or latest_year)
        default_month = latest_month if (self.current_year() or latest_year) == latest_year else (valid_months[-1] if valid_months else latest_month)
        self._refresh_month_options(valid_months, default_month=default_month)

    # --- NEW: month list reconciliation that respects explicit user clears ---
    def _refresh_month_options(self, valid_months: List[int], *, default_month: Optional[int] = None) -> None:
        previous = [int(v) for v in self.month_list.checked_values() if str(v).isdigit()]
        selected = [m for m in previous if m in set(valid_months)]
        if not selected and not self._month_user_touched and default_month in set(valid_months):
            selected = [int(default_month)] if default_month is not None else []

        self._month_list_updating = True
        try:
            self.month_list.set_items([str(m) for m in valid_months], checked_values=[str(m) for m in selected])
        finally:
            self._month_list_updating = False

    # --- NEW: current selected year helper used by catalog/filter refresh flows ---
    def current_year(self) -> Optional[int]:
        value = self.year_combo.currentData()
        try:
            return int(value)
        except Exception:
            return None

    # --- NEW: assemble UI selections into the service-level filter model ---
    def current_filters(self) -> QueryFilters:
        year = self.current_year()
        months = []
        for raw in self.month_list.checked_values():
            try:
                months.append(int(raw))
            except Exception:
                continue
        return QueryFilters(
            ano=year,
            meses_sel=months,
            se_sel=self.se_list.checked_values(),
            bay_sel=self.bay_list.checked_values(),
            equipamento_sel=self.equip_list.checked_values(),
            terminal_sel=self.terminal_list.checked_values(),
            vars_sel=self.var_list.checked_values(),
            ponto_id_like=self.point_like_edit.text().strip(),
        )

    # --- NEW: option-loader view of current filters that excludes the target dimension itself ---
    def _filters_for_target(self, target: str) -> QueryFilters:
        filters = self.current_filters()
        if target == "SE":
            filters.se_sel = []
        elif target == "BAY":
            filters.bay_sel = []
        elif target == "EQUIPAMENTO":
            filters.equipamento_sel = []
        elif target == "TERMINAL":
            filters.terminal_sel = []
        elif target == "var":
            filters.vars_sel = []
        return filters

    # --- NEW: repopulate dependent option lists without silently changing month selection ---
    def refresh_context_options(self) -> None:
        if self.query_service is None or self.runtime_state is None:
            return
        try:
            se_selected = self.se_list.checked_values()
            bay_selected = self.bay_list.checked_values()
            equip_selected = self.equip_list.checked_values()
            terminal_selected = self.terminal_list.checked_values()
            vars_selected = self.var_list.checked_values()

            self.se_list.set_items(
                self.query_service.load_distinct_options(target_col="SE", filters=self._filters_for_target("SE")),
                checked_values=[v for v in se_selected],
            )
            self.bay_list.set_items(
                self.query_service.load_distinct_options(target_col="BAY", filters=self._filters_for_target("BAY")),
                checked_values=[v for v in bay_selected],
            )
            self.equip_list.set_items(
                self.query_service.load_distinct_options(target_col="EQUIPAMENTO", filters=self._filters_for_target("EQUIPAMENTO")),
                checked_values=[v for v in equip_selected],
            )
            self.terminal_list.set_items(
                self.query_service.load_distinct_options(target_col="TERMINAL", filters=self._filters_for_target("TERMINAL")),
                checked_values=[v for v in terminal_selected],
            )
            self.var_list.set_items(
                self.query_service.load_vars_by_context(self._filters_for_target("var")),
                checked_values=[v for v in vars_selected],
            )
        except Exception as exc:
            self._append_message(self.main_message, f"Falha ao atualizar opcoes de filtro: {exc}")

    # --- NEW: run the paginated table query for the current desktop filter state ---
    def run_query(self, *, reset_page: bool = False) -> None:
        if self.query_service is None:
            return
        try:
            if reset_page:
                self._current_page = 1
            self._page_size = int(self.page_size_combo.currentText())
            result = self.query_service.query_page(
                filters=self.current_filters(),
                page_size=self._page_size,
                page_number=self._current_page,
                order_label=self.order_combo.currentText(),
            )
            self._apply_page_result(result)
        except Exception as exc:
            self.table_model.set_frame(pd.DataFrame())
            self.page_label.setText("Pagina 0 de 0")
            self._append_message(self.main_message, f"Falha na consulta: {exc}")

    # --- NEW: project paginated query data into the native table view ---
    def _apply_page_result(self, page: PageResult) -> None:
        self.table_model.set_frame(page.frame)
        total_pages = max(1, math.ceil(max(page.total, 1) / max(self._page_size, 1))) if page.total else 0
        self.page_label.setText(f"Pagina {self._current_page} de {total_pages} | linhas={page.total}")
        self.prev_page_button.setEnabled(self._current_page > 1)
        self.next_page_button.setEnabled(page.total > self._current_page * self._page_size)

    # --- NEW: move to previous results page ---
    def previous_page(self) -> None:
        if self._current_page <= 1:
            return
        self._current_page -= 1
        self.run_query()

    # --- NEW: move to next results page ---
    def next_page(self) -> None:
        self._current_page += 1
        self.run_query()

    # --- NEW: explicit reset action that can restore sensible defaults ---
    def reset_filters(self) -> None:
        if self._catalog_by_month.empty or self.query_service is None:
            return
        self.point_like_edit.clear()
        for widget in (self.se_list, self.bay_list, self.equip_list, self.terminal_list, self.var_list):
            widget.clear_checks()
        self._month_user_touched = False
        self._initialize_filter_defaults(by_month=self._catalog_by_month, initial=True)
        self.refresh_context_options()
        self.run_query(reset_page=True)

    # --- NEW: year change handler with careful month reconciliation ---
    def on_year_changed(self) -> None:
        if self.query_service is None or self._catalog_by_month.empty:
            return
        year = self.current_year()
        if year is None:
            return
        valid_months = self.query_service.months_for_year(self._catalog_by_month, year)
        default_month = valid_months[-1] if valid_months else None
        self._refresh_month_options(valid_months, default_month=default_month)
        self.refresh_context_options()
        self.run_query(reset_page=True)

    # --- NEW: mark explicit month edits so the UI stops re-defaulting them silently ---
    def on_month_item_changed(self, _item: QListWidgetItem) -> None:
        if self._month_list_updating or self.month_list.is_updating():
            return
        self._month_user_touched = True
        self.refresh_context_options()

    # --- NEW: switch back to the setup page for source changes ---
    def show_setup_page(self) -> None:
        if self.runtime_state is not None and self.runtime_state.source_mode != "local_inbox":
            self.setup_source_edit.setText(self.runtime_state.source_root)
        self.stack.setCurrentWidget(self.setup_page)

    # --- NEW: generic background execution harness for long-running tasks ---
    def _run_background(self, *, message: str, fn: Callable[[], object], on_success: Callable[[object], None]) -> None:
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, APP_NAME, "Ja existe uma operacao em andamento.")
            return
        self._set_busy(True, message)
        worker = FunctionWorker(fn, logger=self.logger)
        self._worker = worker

        def _success(result: object) -> None:
            self._set_busy(False)
            on_success(result)
            self._worker = None

        def _failure(details: str) -> None:
            self._set_busy(False)
            self._worker = None
            short = str(details).strip().splitlines()[-1] if str(details).strip() else "Falha desconhecida."
            self._append_message(self.setup_message if self.stack.currentWidget() is self.setup_page else self.main_message, short)
            QMessageBox.critical(self, APP_NAME, short)

        worker.success.connect(_success)
        worker.failure.connect(_failure)
        worker.start()

    # --- NEW: save configured source folder and index immediately from the desktop UI ---
    def save_source_and_index(self) -> None:
        source = self.setup_source_edit.text().strip()
        if not source:
            QMessageBox.warning(self, APP_NAME, "Informe a pasta real das planilhas.")
            return

        def _task() -> DesktopRuntimeState:
            self.runtime_service.configure_source_folder(source)
            return self.runtime_service.reindex_current_source()

        def _done(state: object) -> None:
            assert isinstance(state, DesktopRuntimeState)
            self._append_message(self.setup_message, "Fonte salva e indexacao concluida.")
            self._apply_runtime_state(state)
            self.stack.setCurrentWidget(self.main_page)
            self.load_operational_catalog(initial=True)

        self._run_background(message="Salvando fonte e indexando...", fn=_task, on_success=_done)

    # --- NEW: explicit local inbox activation instead of accidental fallback ---
    def activate_local_inbox_mode(self) -> None:
        def _task() -> DesktopRuntimeState:
            return self.runtime_service.activate_local_inbox_mode()

        def _done(state: object) -> None:
            assert isinstance(state, DesktopRuntimeState)
            self._append_message(self.setup_message, "Modo de pasta local ativado.")
            self._apply_runtime_state(state)
            self.stack.setCurrentWidget(self.main_page)
            self.load_operational_catalog(initial=True)

        self._run_background(message="Ativando pasta local...", fn=_task, on_success=_done)

    # --- NEW: in-app reindex action using the persisted configured source ---
    def reindex_database(self) -> None:
        def _done(state: object) -> None:
            assert isinstance(state, DesktopRuntimeState)
            self._append_message(self.main_message, "Reindexacao concluida.")
            self._apply_runtime_state(state)
            self.load_operational_catalog(initial=True)

        self._run_background(message="Reindexando banco local...", fn=self.runtime_service.reindex_current_source, on_success=_done)

    # --- NEW: validate month requirement only for export operations that need explicit recortes ---
    def _ensure_export_ready(self) -> QueryFilters:
        filters = self.current_filters()
        if not filters.meses_sel:
            raise ValueError("Selecione ao menos um mes antes de exportar.")
        return filters

    # --- NEW: standard export-risk confirmation shared by CSV and XLSX actions ---
    def _confirm_export(self, filters: QueryFilters, options: ExportOptions, *, selected_pontos: Optional[List[str]] = None) -> bool:
        if self.query_service is None or self.export_service is None:
            raise RuntimeError("Servicos de exportacao nao inicializados.")
        pontos = list(selected_pontos or [])
        audit_result = self.export_service.audit(self.query_service, filters, options)
        if audit_result.status == "ERROR":
            findings = "\n".join(str(getattr(item, "title", "")) for item in audit_result.findings[:6])
            raise ValueError(findings or "Exportacao bloqueada pela auditoria.")
        if audit_result.status == "WARN":
            findings = "\n".join(
                f"- {getattr(item, 'title', '')}" for item in audit_result.findings[:8]
            )
            answer = QMessageBox.question(
                self,
                "Exportacao com alertas",
                f"A auditoria encontrou alertas:\n\n{findings}\n\nDeseja continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            action = "accepted_warning" if answer == QMessageBox.StandardButton.Yes else "cancelled_warning"
            self.export_service.persist_risk_decision(
                filters=filters,
                options=options,
                audit_result=audit_result,
                selected_pontos=pontos,
                action_taken=action,
            )
            return answer == QMessageBox.StandardButton.Yes
        return True

    # --- NEW: choose destination file path for desktop exports ---
    def _choose_output_file(self, caption: str, suggested_path: str, filter_text: str) -> Optional[str]:
        directory = str(Path(suggested_path).parent)
        filename = str(Path(suggested_path).name)
        out_path, _ = QFileDialog.getSaveFileName(self, caption, str(Path(directory) / filename), filter_text)
        return out_path or None

    # --- NEW: CSV LONG export entrypoint for the native desktop app ---
    def export_csv_long(self) -> None:
        try:
            filters = self._ensure_export_ready()
            options = ExportOptions(fmt="csv_long")
            if not self._confirm_export(filters, options):
                return
            if self.export_service is None or self.query_service is None:
                raise RuntimeError("Servicos de exportacao nao inicializados.")
            target = self._choose_output_file(
                "Salvar CSV LONG",
                self.export_service.default_output_path("sentinela_export_long.csv"),
                "CSV (*.csv)",
            )
            if not target:
                return

            def _task() -> str:
                return self.export_service.export_csv_long(self.query_service, filters, output_path=target)

            def _done(result: object) -> None:
                self._append_message(self.main_message, f"CSV LONG exportado em: {result}")
                QMessageBox.information(self, APP_NAME, f"CSV LONG exportado em:\n{result}")

            self._run_background(message="Exportando CSV LONG...", fn=_task, on_success=_done)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))

    # --- NEW: CSV WIDE export entrypoint for the native desktop app ---
    def export_csv_wide(self) -> None:
        try:
            filters = self._ensure_export_ready()
            options = ExportOptions(fmt="csv_wide")
            if not self._confirm_export(filters, options):
                return
            if self.export_service is None or self.query_service is None:
                raise RuntimeError("Servicos de exportacao nao inicializados.")
            target = self._choose_output_file(
                "Salvar CSV WIDE",
                self.export_service.default_output_path("sentinela_export_wide.csv"),
                "CSV (*.csv)",
            )
            if not target:
                return

            def _task() -> str:
                return self.export_service.export_csv_wide(self.query_service, filters, output_path=target)

            def _done(result: object) -> None:
                self._append_message(self.main_message, f"CSV WIDE exportado em: {result}")
                QMessageBox.information(self, APP_NAME, f"CSV WIDE exportado em:\n{result}")

            self._run_background(message="Exportando CSV WIDE...", fn=_task, on_success=_done)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))

    # --- NEW: XLSX dashboard export entrypoint using the current selection context ---
    def export_xlsx_dashboard(self) -> None:
        try:
            filters = self._ensure_export_ready()
            if self.query_service is None or self.export_service is None:
                raise RuntimeError("Servicos de exportacao nao inicializados.")
            selected_pontos = self.query_service.resolve_points(filters)
            if not selected_pontos:
                raise ValueError("Nenhum ponto foi encontrado para o recorte atual.")
            options = ExportOptions(fmt="xlsx_dashboard", agg="max", destination_excel=True)
            if not self._confirm_export(filters, options, selected_pontos=selected_pontos):
                return
            target = self._choose_output_file(
                "Salvar XLSX dashboard",
                self.export_service.default_output_path("sentinela_dashboard_completo.xlsx"),
                "Excel (*.xlsx)",
            )
            if not target:
                return

            def _task() -> str:
                out_file, warns = self.export_service.export_xlsx_dashboard(
                    self.query_service,
                    filters,
                    selected_pontos=selected_pontos,
                    output_path=target,
                    options=options,
                )
                if warns:
                    self.logger.warning("Desktop XLSX export warnings: %s", warns)
                return out_file

            def _done(result: object) -> None:
                self._append_message(self.main_message, f"XLSX gerado em: {result}")
                QMessageBox.information(self, APP_NAME, f"XLSX gerado em:\n{result}")

            self._run_background(message="Gerando XLSX dashboard...", fn=_task, on_success=_done)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))

    # --- NEW: resolve export directory from persisted runtime settings ---
    def _exports_path(self) -> str:
        if self.runtime_state is None:
            return str(self.runtime_service.layout["exports"])
        return str(self.runtime_state.settings.get("export_dir", self.runtime_state.layout["exports"]))

    # --- NEW: resolve logs directory from persisted runtime settings ---
    def _logs_path(self) -> str:
        if self.runtime_state is None:
            return str(self.runtime_service.layout["logs"])
        return str(self.runtime_state.settings.get("logs_dir", self.runtime_state.layout["logs"]))

    # --- NEW: open runtime folders in the host OS without involving a browser shell ---
    def _open_path(self, path: str) -> None:
        target = str(path or "").strip()
        if not target:
            return
        candidate = Path(target)
        if not candidate.exists():
            QMessageBox.warning(self, APP_NAME, f"Caminho nao encontrado:\n{target}")
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(candidate))  # type: ignore[attr-defined]
            else:  # pragma: no cover - Windows is the target runtime
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(candidate)))
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Falha ao abrir caminho:\n{exc}")


# --- NEW: PySide6 desktop application bootstrap with a native window ---
def main() -> int:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    assert app is not None
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    window = AndyDesktopWindow()
    window.show()
    if not owns_app:
        return 0
    return int(app.exec())
