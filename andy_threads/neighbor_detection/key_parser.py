from __future__ import annotations

from .models import FeederKey


def parse_andy_key(value: str) -> FeederKey:
    parts = [part.strip() for part in str(value or "").split("|")]
    if len(parts) != 5:
        raise ValueError("expected_key_format_SE_FEEDER_EQUIP_TERMINAL_VAR")
    se, feeder, equipment, terminal, variable = parts
    if not all((se, feeder, equipment, terminal, variable)):
        raise ValueError("key_contains_empty_segment")
    return FeederKey(
        se=se.upper(),
        feeder=feeder.upper(),
        equipment=equipment,
        terminal=terminal,
        variable=variable.upper(),
    )


def is_feeder_name(value: str) -> bool:
    text = str(value or "").strip().upper()
    return text.startswith("AL") and len(text) > 2
