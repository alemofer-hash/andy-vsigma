from __future__ import annotations

import math
from typing import Mapping, Optional


DEFAULT_CURRENT_POLICY = "max_abs_phase"
SUPPORTED_CURRENT_POLICIES = {"max_abs_phase", "first_available_phase"}


def apparent_power_mva_from_current(i_a: float, v_ll_kv: float) -> float:
    return math.sqrt(3.0) * float(v_ll_kv) * float(i_a) / 1000.0


def apparent_power_mva_from_pq(p_mw: float, q_mvar: float) -> float:
    return math.sqrt((float(p_mw) ** 2) + (float(q_mvar) ** 2))


def fp_magnitude_from_q_and_s(q_mvar: float, s_mva: float) -> float:
    s_value = float(s_mva)
    if s_value == 0:
        return math.nan
    ratio = float(q_mvar) / s_value
    ratio = max(-1.0, min(1.0, ratio))
    return math.sqrt(max(0.0, 1.0 - (ratio ** 2)))


def fp_signed_from_pq(p_mw: float, q_mvar: float) -> float:
    apparent_power = apparent_power_mva_from_pq(p_mw, q_mvar)
    if apparent_power == 0:
        return math.nan
    return float(p_mw) / apparent_power


def mw_from_s_fp(s_mva: float, fp: float) -> float:
    return float(s_mva) * float(fp)


def _coerce_phase_value(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def current_reference(
    values: Mapping[str, float],
    policy: str = DEFAULT_CURRENT_POLICY,
) -> float | None:
    normalized_policy = str(policy or DEFAULT_CURRENT_POLICY).strip().lower()
    if normalized_policy not in SUPPORTED_CURRENT_POLICIES:
        raise ValueError(f"Politica de corrente nao suportada: {policy}")

    phases = [
        ("IA", _coerce_phase_value(values.get("IA"))),
        ("IB", _coerce_phase_value(values.get("IB"))),
        ("IC", _coerce_phase_value(values.get("IC"))),
    ]

    if normalized_policy == "first_available_phase":
        for _, phase_value in phases:
            if phase_value is not None:
                return abs(phase_value)
        return None

    candidates = [abs(phase_value) for _, phase_value in phases if phase_value is not None]
    if not candidates:
        return None
    return max(candidates)
