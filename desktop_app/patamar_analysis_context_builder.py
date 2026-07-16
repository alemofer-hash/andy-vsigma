"""
Builder service for PatamarAnalysisContext.

Constructs canonical analysis context from LoadProfileResult, including
glossary, pre-computed sheets, and visual hints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import datetime as dt

import pandas as pd

from desktop_app.load_profile_service import LoadProfileResult
from desktop_app.models import QueryFilters
from desktop_app.patamar_analysis_context import PatamarAnalysisContext, TermDefinition
from desktop_app.patamar_xlsx_generator import generate_patamar_dashboard_sheets


class PatamarAnalysisContextBuilder:
    """
    Builds canonical PatamarAnalysisContext from LoadProfileResult.

    Centralizes:
    - glossary creation
    - sheet generation
    - metadata assembly
    - visual hints computation
    - warning collection
    """

    @staticmethod
    def build(
        load_profile_result: LoadProfileResult,
        query_filters: QueryFilters,
        temporal_bounds: Tuple[str, str],
    ) -> PatamarAnalysisContext:
        glossary = PatamarAnalysisContextBuilder._build_glossary()
        sheets_preview = generate_patamar_dashboard_sheets(load_profile_result)
        sheets_preview = PatamarAnalysisContextBuilder._enrich_sheets_with_scope(
            sheets_preview=sheets_preview,
            query_filters=query_filters,
            temporal_bounds=temporal_bounds,
        )
        metadata = PatamarAnalysisContextBuilder._build_metadata(temporal_bounds, query_filters)
        visual_hints = PatamarAnalysisContextBuilder._compute_visual_hierarchy(load_profile_result)
        warnings = list(load_profile_result.warnings or [])

        return PatamarAnalysisContext(
            load_profile_result=load_profile_result,
            query_filters=query_filters,
            temporal_bounds=temporal_bounds,
            term_glossary=glossary,
            sheets_preview=sheets_preview,
            export_metadata=metadata,
            visual_hierarchy=visual_hints,
            warnings=warnings,
        )

    @staticmethod
    def _build_glossary() -> Dict[str, TermDefinition]:
        return {
            "Esforco": TermDefinition(
                short_label="Esforco",
                description="Magnitude de corrente em amperes observada no turno.",
                computational_basis="I_res = |IA*e^(jphi) + IB*e^(j(phi-120)) + IC*e^(j(phi+120))|",
                icon="grafico",
                tooltip=(
                    "O eixo Y dos graficos de patamar representa a corrente observada.\n"
                    "  - Min Esforco: menor corrente do turno\n"
                    "  - Max Esforco: maior corrente do turno\n"
                    "  - Percentis (P25, P50, P75): distribuicao ao longo do turno"
                ),
                example="Se P50 = 60 A, metade do turno operou com corrente <= 60 A.",
            ),
            "Dentro da faixa otima": TermDefinition(
                short_label="Dentro",
                description="Tensao dentro do intervalo recomendado de 205 V a 230 V.",
                computational_basis="205 V <= V_nominal <= 230 V",
                icon="ok",
                tooltip="Indicativo de operacao conforme a faixa otima de tensao.",
                example="Se V_nominal = 215 V, a amostra esta dentro da faixa otima.",
            ),
            "Fora da faixa otima": TermDefinition(
                short_label="Fora",
                description="Tensao fora do intervalo recomendado de 205 V a 230 V.",
                computational_basis="V_nominal < 205 V ou V_nominal > 230 V",
                icon="alerta",
                tooltip="Pode indicar subtensao ou sobretensao e merece verificacao operacional.",
                example="Se V_nominal = 195 V, a amostra esta fora da faixa otima.",
            ),
            "Indeterminado": TermDefinition(
                short_label="Indeterminado",
                description="Medicao de tensao nao disponivel ou invalida para este timestamp.",
                computational_basis="voltage_compliance == None",
                icon="?",
                tooltip="Nao foi possivel determinar a conformidade por falta de leitura valida.",
                example="Sem leitura de tensao valida, a amostra fica como indeterminada.",
            ),
            "Conformidade de Tensao": TermDefinition(
                short_label="Conformidade",
                description="Percentual de amostras dentro da faixa otima de 205-230 V durante o turno.",
                computational_basis="count(Dentro) / (count(Dentro) + count(Fora)) * 100%",
                icon="percentual",
                tooltip=(
                    "Proporcao de operacao conforme a faixa otima.\n"
                    "  - >95%: excelente\n"
                    "  - 80-95%: aceitavel\n"
                    "  - <80%: critica"
                ),
                example="Se 92 de 100 amostras estao dentro, a conformidade e 92%.",
            ),
            "Mediana (P50)": TermDefinition(
                short_label="P50 / Mediana",
                description="Valor de corrente onde 50% das amostras ficam abaixo e 50% acima.",
                computational_basis="Percentil 50 do array ordenado de corrente",
                icon="p50",
                tooltip=(
                    "Referencia central da distribuicao.\n"
                    "Ajuda a comparar perfis entre turnos com menor sensibilidade a outliers."
                ),
                example="P50 = 60 A significa que metade do turno operou com I <= 60 A.",
            ),
            "Amplitude": TermDefinition(
                short_label="Amplitude",
                description="Diferenca entre o maior e o menor valor de corrente no turno.",
                computational_basis="Amplitude = Max - Min",
                icon="variacao",
                tooltip=(
                    "Medida de variabilidade ao longo do turno.\n"
                    "Amplitude alta sugere oscilacao relevante; baixa indica regime mais estavel."
                ),
                example="Se Min = 50 A e Max = 70 A, a amplitude e 20 A.",
            ),
        }

    @staticmethod
    def _build_metadata(
        temporal_bounds: Tuple[str, str],
        query_filters: QueryFilters,
    ) -> Dict[str, Any]:
        t0, t1 = temporal_bounds
        scope_summary = PatamarAnalysisContextBuilder._build_scope_summary(query_filters, temporal_bounds)
        return {
            "title": "Analise de Patamar de Carga",
            "subtitle": "Distribuicao de corrente e conformidade de tensao por turno operacional",
            "period": f"{t0} -> {t1}",
            "period_label": f"Periodo: {t0[:10]} a {t1[:10]}",
            "scope_summary": scope_summary,
            "generated_at": dt.datetime.now().isoformat(),
            "glossary_available": True,
            "author": "ANDY vSigma Desktop",
        }

    @staticmethod
    def _compute_visual_hierarchy(result: LoadProfileResult) -> Dict[str, Any]:
        _ = result
        return {
            "emphasize_compliance": True,
            "show_extremes_inline": True,
            "compact_diagnostics": True,
            "highlight_critical_thresholds": True,
            "glossary_icon_visible": True,
        }

    @staticmethod
    def _compact_values(values: list[str], *, label: str, limit: int = 3) -> Optional[str]:
        cleaned = [str(value).strip() for value in values if str(value).strip()]
        if not cleaned:
            return None
        if len(cleaned) <= limit:
            return f"{label}: {', '.join(cleaned)}"
        visible = ", ".join(cleaned[:limit])
        remaining = len(cleaned) - limit
        return f"{label}: {visible} (+{remaining})"

    @staticmethod
    def _build_scope_summary(
        query_filters: QueryFilters,
        temporal_bounds: Tuple[str, str],
    ) -> str:
        t0, t1 = temporal_bounds
        parts = [f"Periodo analisado: {t0[:16]} -> {t1[:16]}"]

        for label, values in (
            ("Anos", [str(value) for value in query_filters.anos_sel]),
            ("Meses", [str(value) for value in query_filters.meses_sel]),
            ("SE", list(query_filters.se_sel)),
            ("Bay", list(query_filters.bay_sel)),
            ("Objeto", list(query_filters.equipamento_sel)),
            ("Terminal", list(query_filters.terminal_sel)),
            ("Variaveis", list(query_filters.vars_sel)),
        ):
            fragment = PatamarAnalysisContextBuilder._compact_values(values, label=label)
            if fragment:
                parts.append(fragment)

        if query_filters.ponto_id_like:
            parts.append(f"Ponto filtro: {query_filters.ponto_id_like}")

        return " | ".join(parts)

    @staticmethod
    def _build_scope_focus(query_filters: QueryFilters) -> str:
        focus_parts: list[str] = []
        for label, values in (
            ("SE", list(query_filters.se_sel)),
            ("Bay", list(query_filters.bay_sel)),
            ("Objeto", list(query_filters.equipamento_sel)),
            ("Terminal", list(query_filters.terminal_sel)),
        ):
            fragment = PatamarAnalysisContextBuilder._compact_values(values, label=label, limit=2)
            if fragment:
                focus_parts.append(fragment)
        return " | ".join(focus_parts) if focus_parts else "escopo geral do recorte"

    @staticmethod
    def _enrich_sheets_with_scope(
        *,
        sheets_preview: Dict[str, pd.DataFrame],
        query_filters: QueryFilters,
        temporal_bounds: Tuple[str, str],
    ) -> Dict[str, pd.DataFrame]:
        if not sheets_preview:
            return sheets_preview

        scope_summary = PatamarAnalysisContextBuilder._build_scope_summary(query_filters, temporal_bounds)
        scope_focus = PatamarAnalysisContextBuilder._build_scope_focus(query_filters)
        enriched: Dict[str, pd.DataFrame] = {}

        for sheet_name, df in sheets_preview.items():
            if df.empty:
                enriched[sheet_name] = df
                continue

            scoped_df = df.copy()
            if "Escopo do Recorte" not in scoped_df.columns:
                scoped_df.insert(0, "Escopo do Recorte", scope_summary)

            if "Contexto e Interpretacao" in scoped_df.columns:
                scoped_df["Contexto e Interpretacao"] = scoped_df["Contexto e Interpretacao"].map(
                    lambda text: f"{text} Recorte analisado: {scope_summary}."
                )
            if "Pontos de Verificacao Sugerida" in scoped_df.columns:
                scoped_df["Pontos de Verificacao Sugerida"] = scoped_df["Pontos de Verificacao Sugerida"].map(
                    lambda text: f"{text} Priorizar a verificacao em: {scope_focus}."
                )

            enriched[sheet_name] = scoped_df

        return enriched
