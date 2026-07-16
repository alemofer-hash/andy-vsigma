"""
Smoke-contract tests for ExportPanel.
SPRINT 2:
- Qt compatibility (PySide6 -> PyQt5 fallback)
- skips cleanly if main_window scaffolding is unavailable
- keeps focus on contract/state collection, not full app behavior
"""
from __future__ import annotations

import os
import pytest

try:
    from PySide6.QtWidgets import QApplication
    HAS_QT = True
except Exception:
    try:
        from PyQt5.QtWidgets import QApplication
        HAS_QT = True
    except Exception:
        HAS_QT = False

pytest.importorskip("desktop_app.main_window", reason="main_window scaffold not available")
from desktop_app.main_window import ExportPanel
from desktop_app.models import ExportFormat, ExportOptions


@pytest.fixture(scope="session")
def qapp():
    if not HAS_QT:
        pytest.skip("Nenhum binding Qt disponível")
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def panel(qapp):
    p = ExportPanel()
    yield p
    p.close()


def _base_opts(**overrides) -> ExportOptions:
    return ExportOptions(
        equips=["TR-001"],
        t0="2025-01-01 00:00:00",
        t1="2025-01-01 23:59:59",
        vars_=["IA"],
        agg="max",
        out_dir="/tmp",
        **overrides,
    )


def test_default_format_is_xlsx(panel):
    assert panel._fmt_combo.currentData() == ExportFormat.XLSX_DASH


def test_patamar_controls_disabled_by_default(panel):
    assert not panel._patamar_chk.isChecked()
    assert not panel._patamar_p_vars_edit.isEnabled()
    assert not panel._patamar_q_vars_edit.isEnabled()


def test_patamar_toggle_enables_controls(panel):
    panel._patamar_chk.setChecked(True)
    assert panel._patamar_p_vars_edit.isEnabled()
    assert panel._patamar_q_vars_edit.isEnabled()


def test_validate_readiness_requires_p_and_q_when_patamar_on(panel):
    panel._patamar_chk.setChecked(True)
    panel._patamar_p_vars_edit.setText("")
    panel._patamar_q_vars_edit.setText("Q")
    assert panel.validate_readiness() is not None
    panel._patamar_p_vars_edit.setText("P")
    panel._patamar_q_vars_edit.setText("")
    assert panel.validate_readiness() is not None


def test_validate_readiness_rejects_missing_template(panel, tmp_path):
    panel._tmpl_path_edit.setText(str(tmp_path / "missing.xlsx"))
    assert panel.validate_readiness() is not None


def test_collect_options_propagates_patamar_and_template(panel, tmp_path):
    tpl = tmp_path / "tpl.xlsx"
    tpl.write_bytes(b"x")
    panel._tmpl_path_edit.setText(str(tpl))
    panel._patamar_chk.setChecked(True)
    panel._patamar_p_vars_edit.setText("P,PA")
    panel._patamar_q_vars_edit.setText("Q")
    panel._patamar_p_key_edit.setText("key-p")
    panel._patamar_q_key_edit.setText("key-q")
    opts = panel.collect_options(_base_opts())
    assert opts.template_path == str(tpl)
    assert opts.include_patamar is True
    assert opts.patamar_p_vars == ["P", "PA"]
    assert opts.patamar_q_vars == ["Q"]
    assert opts.patamar_principal_p_key == "key-p"
    assert opts.patamar_principal_q_key == "key-q"
