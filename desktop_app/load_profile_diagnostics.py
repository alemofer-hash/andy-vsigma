"""
Load profile semantic diagnostics.

Analyzes per-tier load profiles and generates operational interpretations
based on real current magnitudes, voltage compliance, and relative variation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from desktop_app.load_profile_service import PatamarCurve


@dataclass(frozen=True)
class TierInterpretation:
    """Professional semantic interpretation of a tier's load profile."""

    tier_name: str
    summary_line: str
    operational_context: str
    attention_points: str
    confidence_indicator: str


def _relative_indicator(reference: float, variation: float) -> float:
    base = abs(reference) if abs(reference) > 1e-6 else 1.0
    return abs(variation) / base


def diagnose_tier_profile(curve: Optional[PatamarCurve]) -> Optional[TierInterpretation]:
    """
    Generate professional interpretation of a tier's load curve.

    Returns None when the curve has too few points to sustain a reading.
    """
    if curve is None or curve.count < 10:
        return None

    tier_name = str(curve.tier_name or "desconhecido")
    mean_current = float(curve.mean_value or curve.p50)
    current_range = float(curve.max_value - curve.min_value)
    stability = float(curve.std_value or 0.0)
    median = float(curve.p50)
    voltage_ok_ratio = float(curve.voltage_compliance_ratio or 0.0)
    relative_stability = _relative_indicator(mean_current, stability)
    relative_range = _relative_indicator(median, current_range)

    if tier_name.lower() == "madrugada":
        summary, context, attention = _diagnose_madrugada(
            mean_current, stability, median, voltage_ok_ratio, relative_stability, relative_range
        )
    elif tier_name.lower() == "manha":
        summary, context, attention = _diagnose_manha(
            mean_current, stability, median, voltage_ok_ratio, relative_stability, relative_range
        )
    elif tier_name.lower() == "tarde":
        summary, context, attention = _diagnose_tarde(
            mean_current, stability, median, voltage_ok_ratio, relative_stability, relative_range
        )
    elif tier_name.lower() == "noite":
        summary, context, attention = _diagnose_noite(
            mean_current, stability, median, voltage_ok_ratio, relative_stability, relative_range
        )
    else:
        summary = f"Turno {tier_name}: perfil operacional observado."
        context = (
            f"Corrente media {mean_current:.1f} A com variacao +/-{stability:.1f} A. "
            f"Leitura sugere conferir o contexto especifico deste recorte."
        )
        attention = "Verificar o contexto operacional e a conformidade de tensao deste turno."

    return TierInterpretation(
        tier_name=tier_name,
        summary_line=summary,
        operational_context=context,
        attention_points=attention,
        confidence_indicator="observado",
    )


def _diagnose_madrugada(
    mean_current: float,
    stability: float,
    median: float,
    voltage_ok_ratio: float,
    relative_stability: float,
    relative_range: float,
) -> tuple[str, str, str]:
    summary = "Madrugada: operacao de menor carga, regime geralmente mais controlado."

    if relative_stability < 0.08 and relative_range < 0.25:
        context = (
            f"Perfil de minima carga com excelente estabilidade (media {mean_current:.1f} A, "
            f"+/-{stability:.1f} A). Indica regime bem definido e previsivel no periodo."
        )
        attention = "Verificar se a tensao minima permanece dentro da faixa otima de 205-230 V."
    elif relative_stability < 0.18 and relative_range < 0.45:
        context = (
            f"Operacao tranquila em baixa demanda (media {mean_current:.1f} A) com boa estabilidade "
            f"(+/-{stability:.1f} A). Leitura compativel com o comportamento esperado da madrugada."
        )
        attention = "Perfil estavel. Verificar a conformidade de tensao para confirmar a operacao adequada."
    else:
        context = (
            f"Madrugada com dispersao relevante (+/-{stability:.1f} A em torno de {median:.1f} A). "
            f"Sugere cargas variaveis ou mudancas de regime durante o periodo."
        )
        attention = "Investigar a origem da variacao e verificar se houve manobra, reconfiguracao ou carga intermitente."

    if voltage_ok_ratio < 0.85:
        attention = "Conformidade de tensao reduzida (<85%). Merece verificar regulacao, tap ou sobretensao em vazio."

    return summary, context, attention


def _diagnose_manha(
    mean_current: float,
    stability: float,
    median: float,
    voltage_ok_ratio: float,
    relative_stability: float,
    relative_range: float,
) -> tuple[str, str, str]:
    summary = "Manha: transicao matinal com crescimento gradual de corrente."

    if relative_stability < 0.10 and relative_range < 0.30:
        context = (
            f"Comportamento estavel durante o ramp-up matinal (media {mean_current:.1f} A, "
            f"+/-{stability:.1f} A). Indica transicao suave do regime noturno para o diurno."
        )
        attention = "Perfil esperado. Verificar a continuidade do crescimento ao longo da janela operacional."
    elif relative_stability < 0.20 and relative_range < 0.50:
        context = (
            f"Variacao moderada durante a manha (+/-{stability:.1f} A em torno de {median:.1f} A). "
            f"Leitura compativel com aumento gradual de demanda."
        )
        attention = "Padrao tipico. Verificar correlacao com a entrada de carga ou mudanca de habito operacional."
    else:
        context = (
            f"Variacao significativa durante a transicao matinal (+/-{stability:.1f} A). "
            f"Sugere multiplos regimes ou alteracoes rapidas de carga."
        )
        attention = "Investigar a causa: manobra, entrada de geracao, compensacao ou carga intermitente."

    if voltage_ok_ratio < 0.80:
        attention = "Conformidade de tensao reduzida (<80%). Possivel sinal de sobrecarga ou regulacao inadequada no ramp-up."

    return summary, context, attention


def _diagnose_tarde(
    mean_current: float,
    stability: float,
    median: float,
    voltage_ok_ratio: float,
    relative_stability: float,
    relative_range: float,
) -> tuple[str, str, str]:
    summary = "Tarde: janela de maior solicitacao operacional."

    if relative_stability < 0.10 and relative_range < 0.30:
        context = (
            f"Regime de pico estavel (media {mean_current:.1f} A, +/-{stability:.1f} A). "
            f"Indica concentracao consistente de carga no periodo."
        )
        attention = "Perfil concentrado. Verificar margem termica e conformidade de tensao em regime sustentado."
    elif relative_stability < 0.22 and relative_range < 0.55:
        context = (
            f"Operacao de pico com variacao moderada (+/-{stability:.1f} A em torno de {median:.1f} A). "
            f"Leitura compativel com transicoes internas do periodo vespertino."
        )
        attention = "Possivel efeito de geracao variavel, compensacao ou mudanca operacional. Verificar a origem dominante."
    else:
        context = (
            f"Variacao significativa durante a tarde (+/-{stability:.1f} A em torno de {median:.1f} A). "
            f"Sugere multiplos regimes operacionais ao longo do periodo."
        )
        attention = "Investigar mudancas de configuracao, variacao de carga e eventos que expliquem a dispersao observada."

    if voltage_ok_ratio < 0.75:
        attention = "Conformidade de tensao critica (<75%). Merece verificar queda de tensao, regulacao e compensacao reativa."

    return summary, context, attention


def _diagnose_noite(
    mean_current: float,
    stability: float,
    median: float,
    voltage_ok_ratio: float,
    relative_stability: float,
    relative_range: float,
) -> tuple[str, str, str]:
    summary = "Noite: regime sustentado com desaceleracao progressiva."

    if relative_stability < 0.10 and relative_range < 0.30:
        context = (
            f"Regime noturno bem consolidado (media {mean_current:.1f} A, +/-{stability:.1f} A). "
            f"Indica operacao sustentada e previsivel no fechamento do dia."
        )
        attention = "Perfil concentrado. Verificar a transicao esperada para a madrugada e a tensao em regime sustentado."
    elif relative_stability < 0.22 and relative_range < 0.55:
        context = (
            f"Operacao noturna com variacao moderada (+/-{stability:.1f} A em torno de {median:.1f} A). "
            f"Leitura compativel com desaceleracao gradual da demanda."
        )
        attention = "Padrao esperado. Verificar se a transicao para a madrugada ocorre no ritmo previsto."
    else:
        context = (
            f"Variacao significativa durante a noite (+/-{stability:.1f} A em torno de {median:.1f} A). "
            f"Sugere multiplas fases operacionais ou mudancas de regime."
        )
        attention = "Investigar a sequencia operacional do fechamento e verificar eventos que expliquem a dispersao."

    if voltage_ok_ratio < 0.80:
        attention = "Conformidade de tensao reduzida (<80%). Possivel necessidade de ajuste operacional ou de regulacao."

    return summary, context, attention
