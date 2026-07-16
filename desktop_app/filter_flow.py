from __future__ import annotations

from typing import Iterable, List, Mapping, Optional, Sequence


FILTER_ORDER = ["ano", "mes", "SE", "BAY", "EQUIPAMENTO", "TERMINAL", "var"]
FILTER_DEPENDENCIES: Mapping[str, List[str]] = {
    "ano": [],
    "mes": ["ano"],
    "SE": ["ano", "mes"],
    "BAY": ["ano", "mes", "SE"],
    "EQUIPAMENTO": ["ano", "mes", "SE", "BAY"],
    "TERMINAL": ["ano", "mes", "SE", "BAY", "EQUIPAMENTO"],
    "var": ["ano", "mes", "SE", "BAY", "EQUIPAMENTO", "TERMINAL"],
}


# --- NEW: normalize scalar combo-like selection values to canonical text ---
def normalize_single_value(value: object) -> str:
    text = str(value or "").strip()
    return text


# --- NEW: preserve valid user choice, otherwise prune or auto-fill the only possible value ---
def reconcile_single_selection(current_value: object, valid_options: Sequence[object]) -> tuple[str, bool, bool]:
    valid = [str(v).strip() for v in valid_options if str(v).strip()]
    valid = list(dict.fromkeys(valid))
    current = normalize_single_value(current_value)

    if current and current in valid:
        return current, False, False
    if len(valid) == 1:
        selected = valid[0]
        return selected, current != selected, True
    return "", bool(current), False


# --- NEW: prune invalid multi-select values while preserving user order ---
def reconcile_multi_selection(current_values: Optional[Sequence[object]], valid_options: Sequence[object]) -> tuple[List[str], bool]:
    valid = {str(v).strip() for v in valid_options if str(v).strip()}
    out: List[str] = []
    for raw in current_values or []:
        text = str(raw or "").strip()
        if text and text in valid and text not in out:
            out.append(text)
    before = [str(v or "").strip() for v in (current_values or []) if str(v or "").strip()]
    return out, out != before


# --- NEW: determine whether a progressive step is unlocked by its upstream context ---
def is_step_enabled(step: str, selections: Mapping[str, object]) -> bool:
    deps = FILTER_DEPENDENCIES.get(step, [])
    for dep in deps:
        value = selections.get(dep)
        if dep == "ano":
            if value is None or str(value).strip() == "":
                return False
        else:
            if not normalize_single_value(value):
                return False
    return True


# --- NEW: true when the full locator chain is specific enough to load variables/results ---
def is_context_resolved(selections: Mapping[str, object]) -> bool:
    return is_step_enabled("var", selections)


# --- NEW: build a human-readable guidance message for incomplete progressive context ---
def next_required_step_label(selections: Mapping[str, object]) -> str:
    labels = {
        "ano": "Ano",
        "mes": "Mes",
        "SE": "SE",
        "BAY": "BAY",
        "EQUIPAMENTO": "Equipamento",
        "TERMINAL": "Terminal",
    }
    for step in FILTER_ORDER[:-1]:
        if step == "ano":
            if selections.get("ano") is None or str(selections.get("ano", "")).strip() == "":
                return labels[step]
            continue
        if not normalize_single_value(selections.get(step)):
            return labels[step]
    return ""
