from __future__ import annotations

from .models import NeighborClassification


def alternative_hypotheses_for(classification: NeighborClassification, upstream_moves: bool, low_balance: bool) -> tuple[str, ...]:
    hypotheses: list[str] = []
    if classification == NeighborClassification.LOAD_TRANSFER_CANDIDATE:
        hypotheses.extend(["confirmed_topology_required", "scada_switching_log_required"])
        if upstream_moves:
            hypotheses.append("possible_upstream_or_common_mode_event")
    elif classification == NeighborClassification.COMMON_MODE_EVENT_CANDIDATE:
        hypotheses.extend(["substation_common_mode_change", "upstream_event_or_measurement_batch"])
    elif classification == NeighborClassification.LOCAL_FEEDER_EVENT_CANDIDATE:
        hypotheses.extend(["local_feeder_load_change", "measurement_or_cadastre_issue"])
    elif classification == NeighborClassification.DATA_QUALITY_CANDIDATE:
        hypotheses.extend(["insufficient_common_coverage", "gap_or_missing_values"])
    if low_balance:
        hypotheses.append("transfer_balance_low")
    return tuple(dict.fromkeys(hypotheses))
