from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .models import NeighborManeuverCandidate, NeighborhoodEventEpisode, to_plain_dict

REPORT_HEADER = (
    "Este relatorio identifica candidatos de transferencia/manobra pela comparacao de correntes IB de alimentadores distintos. "
    "Nenhum evento e confirmado operacionalmente sem validacao humana ou evidencia SCADA."
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_plain_dict(payload), indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def write_table(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    if path.suffix.lower() == ".parquet":
        try:
            df.to_parquet(path, index=False)
        except Exception as exc:
            fallback = path.with_suffix(path.suffix + ".csv")
            df.to_csv(fallback, index=False)
            path.with_suffix(path.suffix + ".unavailable.txt").write_text(str(exc), encoding="utf-8")
    elif path.suffix.lower() == ".csv":
        df.to_csv(path, index=False)
    else:
        df.to_json(path, orient="records", indent=2, force_ascii=False)


def write_human_review_queue(path: Path, episodes: list[NeighborhoodEventEpisode], candidates: list[NeighborManeuverCandidate]) -> None:
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    lines = [
        "# ANDY Threads Neighbor Detection - Human Review Queue",
        "",
        REPORT_HEADER,
        "",
        "Todos os itens abaixo permanecem em `PENDING_HUMAN_REVIEW`; `training_use=false` por padrao.",
        "",
    ]
    for episode in episodes:
        lines.extend(
            [
                f"## {episode.episode_id}",
                "",
                f"- SE: {episode.SE}",
                f"- Inicio: {episode.event_start}",
                f"- Pico: {episode.event_peak}",
                f"- Fim: {episode.event_end}",
                f"- ALs que cairam: {', '.join(episode.feeders_decreasing) or 'nenhum'}",
                f"- ALs que subiram: {', '.join(episode.feeders_increasing) or 'nenhum'}",
                f"- Balance score: {episode.transfer_balance:.3f}",
                f"- Status humano: {episode.review_status.value}",
                "",
                "| Campo | Resposta humana |",
                "|---|---|",
                "| Veredito |  |",
                "| Reviewer |  |",
                "| Confidence |  |",
                "| Reason |  |",
                "| Evidence type |  |",
                "| Selected feeders |  |",
                "| Notes |  |",
                "| training_use | false |",
                "",
            ]
        )
        for candidate_id in episode.pair_candidates:
            candidate = by_id.get(candidate_id)
            if candidate:
                lines.extend(
                    [
                        f"### Candidato {candidate.candidate_id}",
                        f"- Par: {candidate.feeder_pair[0]} x {candidate.feeder_pair[1]}",
                        f"- Classificacao: {candidate.classification.value}",
                        f"- Score: {candidate.transfer_score:.3f}",
                        f"- Delta: {candidate.delta_I_by_feeder}",
                        f"- Hipoteses alternativas: {', '.join(candidate.alternative_hypotheses) or 'nenhuma'}",
                        "",
                    ]
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_blind_run_report(
    path: Path,
    *,
    manifests: list[dict[str, Any]],
    graph: dict[str, Any],
    candidates: list[NeighborManeuverCandidate],
    episodes: list[NeighborhoodEventEpisode],
    warnings: list[str],
) -> None:
    lines = [
        "# ANDY Threads Neighbor Detection - Blind Run Report",
        "",
        REPORT_HEADER,
        "",
        "## Segurança",
        "",
        "- Inputs XLSX foram abertos em modo somente leitura.",
        "- Detector principal usou apenas `VAR == IB` entre alimentadores distintos.",
        "- Nenhum evento foi confirmado automaticamente.",
        "- Outputs reais foram salvos em `.validation_tmp/`.",
        "",
        "## Inputs",
        "",
    ]
    for manifest in manifests:
        lines.append(f"- {manifest['source_alias']}: rows={manifest['total_rows']}; ib_rows={manifest['ib_rows']}; hash16={manifest['source_hash'][:16]}")
    lines.extend(["", "## Grafo de vizinhanca", "", "```json", json.dumps(graph, indent=2, ensure_ascii=False), "```", ""])
    if warnings:
        lines.extend(["## Avisos", "", *[f"- {warning}" for warning in warnings], ""])
    lines.extend(["## Candidatos por par", "", "| Par | SE | Pico | Classificacao | Score | Balance | Centroide | Configurado |"])
    lines.append("|---|---|---|---|---:|---:|---:|---|")
    for candidate in candidates[:50]:
        lines.append(
            f"| {candidate.feeder_pair[0]} x {candidate.feeder_pair[1]} | {candidate.SE} | {candidate.event_peak} | "
            f"{candidate.classification.value} | {candidate.transfer_score:.3f} | {candidate.balance_score:.3f} | "
            f"{candidate.centroid_delta_magnitude:.3f} | {candidate.configured_neighbor_pair} |"
        )
    lines.extend(["", "## Episodios", ""])
    for episode in episodes:
        lines.extend(
            [
                f"### {episode.episode_id}",
                f"1. ALs participaram: {', '.join(sorted(set((*episode.feeders_increasing, *episode.feeders_decreasing)))) or 'nenhum'}",
                f"2. Caiu: {', '.join(episode.feeders_decreasing) or 'nenhum'}",
                f"3. Subiu: {', '.join(episode.feeders_increasing) or 'nenhum'}",
                f"4. Delta por AL: {episode.feeder_deltas}",
                f"5. Comecou: {episode.event_start}",
                f"6. Pico: {episode.event_peak}",
                f"7. Estabilizou/janela final: {episode.event_end}",
                f"8. Soma do par/vizinhanca permaneceu estavel? net_delta={episode.net_neighborhood_delta:.3f} A",
                f"9. TR permaneceu estavel? upstream_delta={episode.upstream_delta}",
                f"10. Deslocamento de centroide: {episode.centroid_evidence}",
                f"11. Balance score: {episode.transfer_balance:.3f}",
                f"12. Transfer score max: {max((c.transfer_score for c in candidates if c.candidate_id in episode.pair_candidates), default=0.0):.3f}",
                f"13. Par configurado/exploratorio: ver candidatos vinculados",
                f"14. Hipoteses alternativas: {', '.join(episode.alternative_hypotheses) or 'nenhuma'}",
                "15. Quem deve validar: Operacao com Engenharia, Protecao/Automacao e Medicao se houver flags.",
                f"16. Status humano: {episode.review_status.value}",
                "",
            ]
        )
    lines.extend(
        [
            "## Protocolo cego",
            "",
            "O horario manual da manobra ainda nao foi informado nesta execucao. A fila acima deve ser revisada sem calibrar detector por timestamp manual.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
