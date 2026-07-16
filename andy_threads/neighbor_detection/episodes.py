from __future__ import annotations

from .models import NeighborhoodEventEpisode


def episode_summary_lines(episode: NeighborhoodEventEpisode) -> list[str]:
    down = ", ".join(episode.feeders_decreasing) or "nenhum"
    up = ", ".join(episode.feeders_increasing) or "nenhum"
    return [
        f"SE: {episode.SE}",
        f"ALs com queda: {down}",
        f"ALs com subida: {up}",
        f"Pico candidato: {episode.event_peak}",
        f"Delta liquido da vizinhanca: {episode.net_neighborhood_delta:.2f} A",
        f"Balance score: {episode.transfer_balance:.3f}",
        f"Status humano: {episode.review_status.value}",
    ]
