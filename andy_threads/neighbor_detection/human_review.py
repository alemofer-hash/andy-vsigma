from __future__ import annotations

from .models import HumanNeighborReview

VALID_VERDICTS = {
    "MANOBRA_CONFIRMADA",
    "TRANSFERENCIA_CONFIRMADA",
    "MUDANCA_DE_CARGA",
    "EVENTO_COMUM",
    "EVENTO_LOCAL",
    "ARTEFATO_DE_MEDICAO",
    "ERRO_DE_CADASTRO",
    "INCONCLUSIVO",
    "OUTRO",
}


def validate_human_review(payload: dict[str, object]) -> HumanNeighborReview:
    verdict = str(payload.get("verdict") or "").strip().upper()
    if verdict not in VALID_VERDICTS:
        raise ValueError("invalid_neighbor_review_verdict")
    return HumanNeighborReview(
        reviewer=str(payload.get("reviewer") or ""),
        timestamp=str(payload.get("timestamp") or ""),
        confidence=float(payload.get("confidence") or 0.0),
        reason=str(payload.get("reason") or ""),
        evidence_type=str(payload.get("evidence_type") or ""),
        selected_feeders=tuple(str(item).strip().upper() for item in payload.get("selected_feeders", []) if str(item).strip()),
        notes=str(payload.get("notes") or ""),
        verdict=verdict,
        training_use=bool(payload.get("training_use", False)),
    )
