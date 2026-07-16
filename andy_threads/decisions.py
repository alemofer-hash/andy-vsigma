from __future__ import annotations

from .models import DecisionRecord, DecisionType


def decision_requires_review(decision: DecisionRecord) -> bool:
    return decision.decision_type in {
        DecisionType.MEASUREMENT_SUSPECT,
        DecisionType.NEEDS_FIELD_CHECK,
        DecisionType.NEEDS_SOURCE_CORRECTION,
    }


__all__ = ["DecisionRecord", "DecisionType", "decision_requires_review"]
