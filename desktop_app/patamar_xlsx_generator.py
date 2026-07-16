"""
Load profile patamar dashboard XLSX generator.

Generates professional Excel workbooks with load profile analysis using
real current and voltage magnitudes instead of per-unit values.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

from desktop_app.load_profile_diagnostics import diagnose_tier_profile
from desktop_app.load_profile_service import HOURLY_TIERS, LoadProfileResult


def generate_patamar_dashboard_sheets(result: LoadProfileResult) -> Dict[str, pd.DataFrame]:
    """
    Generate multiple sheets for patamar dashboard in Excel.

    Returns dictionary of sheet_name -> DataFrame for populating a workbook.
    """
    sheets: Dict[str, pd.DataFrame] = {}

    summary_df = _build_summary_table(result)
    if not summary_df.empty:
        sheets["Resumo por Turno"] = summary_df

    details_df = _build_detailed_metrics_table(result)
    if not details_df.empty:
        sheets["Metricas Detalhadas"] = details_df

    diagnostics_df = _build_diagnostics_table(result)
    if not diagnostics_df.empty:
        sheets["Interpretacao Operacional"] = diagnostics_df

    voltage_df = _build_voltage_compliance_table(result)
    if not voltage_df.empty:
        sheets["Conformidade de Tensao"] = voltage_df

    return sheets


def _period_label(tier_name: str) -> str:
    start, end = HOURLY_TIERS.get(tier_name, (0, 0))
    return f"{start:02d}:00-{end:02d}:59"


def _fmt_optional(value: float | None, *, digits: int = 4) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def _build_summary_table(result: LoadProfileResult) -> pd.DataFrame:
    """Build executive summary table: one row per tier with key operational metrics."""
    if not result.curves:
        return pd.DataFrame()

    rows = []
    for tier_name in ("Madrugada", "Manha", "Tarde", "Noite"):
        curve = result.curves.get(tier_name)
        if curve is None:
            continue

        rows.append(
            {
                "Turno": tier_name.capitalize(),
                "Periodo": _period_label(tier_name),
                "Carga Media (A)": _fmt_optional(curve.mean_value),
                "Variacao Std (A)": _fmt_optional(curve.std_value),
                "Mediana P50 (A)": _fmt_optional(curve.p50),
                "P25-P75 (A)": f"{curve.p25:.4f}-{curve.p75:.4f}",
                "Min/Max (A)": f"{curve.min_value:.4f}/{curve.max_value:.4f}",
                "Conformidade Tensao (%)": (
                    f"{curve.voltage_compliance_ratio * 100:.1f}%"
                    if curve.voltage_compliance_ratio is not None
                    else "-"
                ),
                "Amostras": int(curve.count),
            }
        )

    return pd.DataFrame(rows)


def _build_detailed_metrics_table(result: LoadProfileResult) -> pd.DataFrame:
    """Build detailed metrics table: percentiles, extremes, and distribution analysis."""
    if not result.curves:
        return pd.DataFrame()

    rows = []
    for tier_name in ("Madrugada", "Manha", "Tarde", "Noite"):
        curve = result.curves.get(tier_name)
        if curve is None:
            continue

        rows.append(
            {
                "Turno": tier_name.capitalize(),
                "Periodo Horario": _period_label(tier_name),
                "P10 (A)": _fmt_optional(curve.p10),
                "P25 (A)": _fmt_optional(curve.p25),
                "P50 Mediana (A)": _fmt_optional(curve.p50),
                "P75 (A)": _fmt_optional(curve.p75),
                "P90 (A)": _fmt_optional(curve.p90),
                "Amplitude = Max-Min (A)": f"{curve.max_value - curve.min_value:.4f}",
                "Min Corrente (A)": f"{curve.min_value:.4f}",
                "Max Corrente (A)": f"{curve.max_value:.4f}",
                "Fator Potencia Medio": _fmt_optional(curve.mean_fp, digits=3),
                "Modo Metrica Principal": str(curve.metric_mode),
                "Total Amostras no Turno": int(curve.count),
            }
        )

    return pd.DataFrame(rows)


def _build_diagnostics_table(result: LoadProfileResult) -> pd.DataFrame:
    """Build operational diagnostics table: semantic interpretation per shift."""
    if not result.curves:
        return pd.DataFrame()

    rows = []
    for tier_name in ("Madrugada", "Manha", "Tarde", "Noite"):
        curve = result.curves.get(tier_name)
        if curve is None:
            continue

        diagnosis = diagnose_tier_profile(curve)
        if diagnosis is None:
            continue

        rows.append(
            {
                "Turno": tier_name.capitalize(),
                "Periodo": _period_label(tier_name),
                "Resumo Operacional": diagnosis.summary_line,
                "Contexto e Interpretacao": diagnosis.operational_context,
                "Pontos de Verificacao Sugerida": diagnosis.attention_points,
                "Indicador de Confianca": diagnosis.confidence_indicator,
            }
        )

    return pd.DataFrame(rows)


def _build_voltage_compliance_table(result: LoadProfileResult) -> pd.DataFrame:
    """Build voltage compliance analysis for the 205-230 V optimal range."""
    if not result.curves:
        return pd.DataFrame()

    rows = []
    for tier_name in ("Madrugada", "Manha", "Tarde", "Noite"):
        curve = result.curves.get(tier_name)
        if curve is None:
            continue

        total = curve.voltage_within_count + curve.voltage_outside_count + curve.voltage_unknown_count
        if total == 0:
            total = 1

        rows.append(
            {
                "Turno": tier_name.capitalize(),
                "Periodo": _period_label(tier_name),
                "Dentro Faixa Otima (205-230V)": int(curve.voltage_within_count),
                "Fora da Faixa Otima": int(curve.voltage_outside_count),
                "Indeterminado/Sem Dado": int(curve.voltage_unknown_count),
                "Total Amostras": total,
                "% Conformidade": (
                    f"{curve.voltage_compliance_ratio * 100:.1f}%"
                    if curve.voltage_compliance_ratio is not None
                    else "-"
                ),
            }
        )

    return pd.DataFrame(rows)


def format_patamar_excel_workbook(workbook, sheets_dict: Dict[str, pd.DataFrame]) -> None:
    """
    Placeholder for future workbook styling integration.
    """
    _ = workbook, sheets_dict
