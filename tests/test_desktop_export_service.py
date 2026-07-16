"""Service-layer contract propagation tests."""
from __future__ import annotations

from unittest.mock import patch
import pytest

from desktop_app.models import ExportFormat, ExportOptions
from desktop_app.export_service import DesktopExportService, ExportAmbiguityError, _is_ambiguity_error

BASE_OPTS_KWARGS = dict(
    equips=["TR-001"],
    t0="2025-01-01 00:00:00",
    t1="2025-01-01 23:59:59",
    vars_=["IA"],
    agg="max",
    time_floor=None,
    equip_slots=1,
    var_slots=3,
    max_timestamps=1_000,
    out_dir="/tmp/andy_exports",
    out_name="test_out.xlsx",
    format=ExportFormat.XLSX_DASH,
)


def _opts(**overrides) -> ExportOptions:
    return ExportOptions(**{**BASE_OPTS_KWARGS, **overrides})


@pytest.fixture
def svc():
    return DesktopExportService(work_root="/work", db_path="/work/andy.duckdb")


@patch("desktop_app.export_service.run_report", return_value="/tmp/out.xlsx")
def test_runner_contract_propagates_template_and_patamar(mock_run, svc):
    svc.export_xlsx_dashboard(_opts(
        template_path="/tpl/base.xlsx",
        include_patamar=True,
        patamar_p_vars=["P"],
        patamar_q_vars=["Q"],
        patamar_principal_p_key="key-p",
        patamar_principal_q_key="key-q",
    ))
    _, kw = mock_run.call_args
    assert kw["template_path"] == "/tpl/base.xlsx"
    assert kw["include_patamar"] is True
    assert kw["patamar_p_vars"] == ["P"]
    assert kw["patamar_q_vars"] == ["Q"]
    assert kw["patamar_principal_p_key"] == "key-p"
    assert kw["patamar_principal_q_key"] == "key-q"


@patch("desktop_app.export_service.run_report", return_value="/tmp/out.xlsx")
def test_empty_patamar_lists_become_none(mock_run, svc):
    svc.export_xlsx_dashboard(_opts(include_patamar=False, patamar_p_vars=[], patamar_q_vars=[]))
    _, kw = mock_run.call_args
    assert kw["patamar_p_vars"] is None
    assert kw["patamar_q_vars"] is None


@patch("desktop_app.export_service.run_report", side_effect=ValueError("Ambiguidade: 2 series candidatas para vars=['P']"))
def test_ambiguity_error_is_wrapped(mock_run, svc):
    with pytest.raises(ExportAmbiguityError):
        svc.export_xlsx_dashboard(_opts(include_patamar=True, patamar_p_vars=["P"], patamar_q_vars=["Q"]))


def test_is_ambiguity_error_keywords():
    assert _is_ambiguity_error("Ambiguidade: 2 series candidatas para vars=['P']")
    assert not _is_ambiguity_error("timestamp inválido")
