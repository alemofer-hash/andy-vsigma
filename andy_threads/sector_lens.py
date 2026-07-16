from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import ThreadKind


class SectorId(str, Enum):
    ENGINEERING = "ENGINEERING"
    OPERATION = "OPERATION"
    MEASUREMENT_DATA = "MEASUREMENT_DATA"
    CADASTRE_ASSETS = "CADASTRE_ASSETS"
    PROTECTION_AUTOMATION = "PROTECTION_AUTOMATION"
    WORKS_MAINTENANCE = "WORKS_MAINTENANCE"
    IT_BI_DATA = "IT_BI_DATA"
    MANAGEMENT = "MANAGEMENT"


@dataclass(frozen=True)
class SectorLens:
    sector_id: SectorId
    label: str
    sees_measurement_as: str
    owns_problem_kinds: tuple[ThreadKind, ...]
    consulted_on: tuple[ThreadKind, ...]
    can_resolve: tuple[ThreadKind, ...]
    required_context_fields: tuple[str, ...]
    default_tags: tuple[str, ...]


DEFAULT_SECTOR_LENSES: dict[SectorId, SectorLens] = {
    SectorId.ENGINEERING: SectorLens(
        SectorId.ENGINEERING,
        "Engenharia",
        "evidencia de comportamento eletrico e planejamento",
        (
            ThreadKind.LOAD_FLOW_ANOMALY,
            ThreadKind.POWER_INVERSION,
            ThreadKind.AT_BT_TRANSITION,
            ThreadKind.PARITY_DESKTOP_BI,
        ),
        (ThreadKind.SWITCHING_EVENT, ThreadKind.WORK_MAINTENANCE_IMPACT, ThreadKind.TERMINAL_MAPPING),
        (ThreadKind.LOAD_FLOW_ANOMALY, ThreadKind.POWER_INVERSION, ThreadKind.PARITY_DESKTOP_BI),
        ("se", "bay_or_feeder", "equipamento", "terminal", "period_start", "period_end"),
        ("engenharia", "analise_eletrica"),
    ),
    SectorId.OPERATION: SectorLens(
        SectorId.OPERATION,
        "Operacao",
        "evidencia de evento operacional, manobra ou estado da rede",
        (ThreadKind.SWITCHING_EVENT,),
        (ThreadKind.POWER_INVERSION, ThreadKind.LOAD_FLOW_ANOMALY),
        (ThreadKind.SWITCHING_EVENT,),
        ("se", "bay_or_feeder", "period_start", "period_end"),
        ("operacao", "evento"),
    ),
    SectorId.MEASUREMENT_DATA: SectorLens(
        SectorId.MEASUREMENT_DATA,
        "Medicao / Dados",
        "evidencia de disponibilidade, cadencia e confiabilidade",
        (
            ThreadKind.MEASUREMENT_GAP,
            ThreadKind.CADENCE_ISSUE,
            ThreadKind.DATA_QUALITY,
            ThreadKind.VARIABLE_MAPPING,
        ),
        (ThreadKind.TERMINAL_MAPPING, ThreadKind.BI_DATASET_ISSUE),
        (ThreadKind.MEASUREMENT_GAP, ThreadKind.CADENCE_ISSUE, ThreadKind.DATA_QUALITY),
        ("source_cadence", "variavel", "period_start", "period_end"),
        ("medicao", "qualidade_dados"),
    ),
    SectorId.CADASTRE_ASSETS: SectorLens(
        SectorId.CADASTRE_ASSETS,
        "Cadastro / Ativos / GIS",
        "evidencia de vinculo entre ativo, terminal e cadastro",
        (ThreadKind.TERMINAL_MAPPING, ThreadKind.VARIABLE_MAPPING),
        (ThreadKind.AT_BT_TRANSITION, ThreadKind.POWER_INVERSION),
        (ThreadKind.TERMINAL_MAPPING, ThreadKind.VARIABLE_MAPPING),
        ("se", "bay_or_feeder", "equipamento", "terminal"),
        ("cadastro", "ativos"),
    ),
    SectorId.PROTECTION_AUTOMATION: SectorLens(
        SectorId.PROTECTION_AUTOMATION,
        "Protecao / Automacao / SCADA",
        "evidencia de sinal, supervisao, rele e automacao",
        (ThreadKind.PROTECTION_AUTOMATION_SIGNAL,),
        (ThreadKind.SWITCHING_EVENT, ThreadKind.LOAD_FLOW_ANOMALY),
        (ThreadKind.PROTECTION_AUTOMATION_SIGNAL,),
        ("se", "equipamento", "terminal", "period_start", "period_end"),
        ("scada", "automacao"),
    ),
    SectorId.WORKS_MAINTENANCE: SectorLens(
        SectorId.WORKS_MAINTENANCE,
        "Obras / Manutencao",
        "evidencia de impacto operacional apos intervencao",
        (ThreadKind.WORK_MAINTENANCE_IMPACT,),
        (ThreadKind.SWITCHING_EVENT, ThreadKind.LOAD_FLOW_ANOMALY),
        (ThreadKind.WORK_MAINTENANCE_IMPACT,),
        ("se", "bay_or_feeder", "period_start", "period_end"),
        ("obra", "manutencao"),
    ),
    SectorId.IT_BI_DATA: SectorLens(
        SectorId.IT_BI_DATA,
        "TI / Dados / BI",
        "evidencia de dataset, acesso, refresh e publicacao",
        (ThreadKind.BI_DATASET_ISSUE, ThreadKind.ACCESS_RLS_ISSUE, ThreadKind.PARITY_DESKTOP_BI),
        (ThreadKind.DATA_QUALITY,),
        (ThreadKind.BI_DATASET_ISSUE, ThreadKind.ACCESS_RLS_ISSUE),
        ("dataset_version", "lote_id", "filter_hash"),
        ("bi", "governanca"),
    ),
    SectorId.MANAGEMENT: SectorLens(
        SectorId.MANAGEMENT,
        "Gestao",
        "evidencia consolidada para decisao e acompanhamento",
        (),
        (ThreadKind.LOAD_FLOW_ANOMALY, ThreadKind.DATA_QUALITY, ThreadKind.BI_DATASET_ISSUE),
        (),
        ("lote_id", "period_start", "period_end"),
        ("gestao", "acompanhamento"),
    ),
}


def get_sector_lens(sector_id: SectorId | str) -> SectorLens:
    return DEFAULT_SECTOR_LENSES[SectorId(sector_id)]


def sectors_for_thread_kind(kind: ThreadKind | str) -> tuple[SectorId, ...]:
    active_kind = ThreadKind(kind)
    sectors = [
        lens.sector_id
        for lens in DEFAULT_SECTOR_LENSES.values()
        if active_kind in lens.owns_problem_kinds or active_kind in lens.consulted_on
    ]
    return tuple(sectors)


def owner_sector_for_thread_kind(kind: ThreadKind | str) -> SectorId:
    active_kind = ThreadKind(kind)
    for lens in DEFAULT_SECTOR_LENSES.values():
        if active_kind in lens.owns_problem_kinds:
            return lens.sector_id
    return SectorId.ENGINEERING


def consulted_sectors_for_thread_kind(kind: ThreadKind | str) -> tuple[SectorId, ...]:
    active_kind = ThreadKind(kind)
    return tuple(lens.sector_id for lens in DEFAULT_SECTOR_LENSES.values() if active_kind in lens.consulted_on)


def can_sector_resolve(sector: SectorId | str, kind: ThreadKind | str) -> bool:
    lens = get_sector_lens(sector)
    return ThreadKind(kind) in lens.can_resolve
