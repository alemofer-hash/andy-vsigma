from __future__ import annotations

from typing import Any, Dict, List, Tuple


Selections = Dict[str, List[str]]


def normalize_selections(raw: Any) -> Selections:
    canonical: Selections = {}
    if raw is None:
        return canonical

    if isinstance(raw, dict):
        for equip, vars_raw in raw.items():
            equip_id = str(equip).strip()
            if not equip_id:
                continue
            vars_list: List[str]
            if isinstance(vars_raw, (list, tuple, set)):
                vars_list = [str(v).strip() for v in vars_raw]
            elif vars_raw is None:
                vars_list = []
            else:
                vars_list = [str(vars_raw).strip()]

            dedup: List[str] = []
            seen = set()
            for vv in vars_list:
                if vv and vv not in seen:
                    seen.add(vv)
                    dedup.append(vv)
            canonical[equip_id] = dedup
        return canonical

    # Legacy: lista de pares [(equip, var), ...] ou dicts.
    if isinstance(raw, (list, tuple)):
        for item in raw:
            equip_id = ""
            var = ""
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                equip_id = str(item[0]).strip()
                var = str(item[1]).strip()
            elif isinstance(item, dict):
                equip_id = str(item.get("equip_id", "")).strip()
                var = str(item.get("var", "")).strip()

            if not equip_id:
                continue
            canonical.setdefault(equip_id, [])
            if var and var not in canonical[equip_id]:
                canonical[equip_id].append(var)
        return canonical

    return canonical


def migrate_legacy_pairs(raw_pairs: Any) -> Selections:
    return normalize_selections(raw_pairs)


def expand_pairs(selections: Selections) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    canonical = normalize_selections(selections)
    for equip_id in sorted(canonical.keys()):
        for var in canonical[equip_id]:
            pairs.append((equip_id, var))
    return pairs


def validate_selections(selections: Selections, required_equips: List[str]) -> None:
    canonical = normalize_selections(selections)
    missing_equips = [e for e in required_equips if e not in canonical]
    if missing_equips:
        raise ValueError("Existem equipamentos sem configuracao de variaveis.")

    empties = [e for e in required_equips if not canonical.get(e)]
    if empties:
        raise ValueError("Selecione ao menos 1 variavel para cada equipamento.")


# --- CHANGED: conversao ponto_id->selecao XLSX mantendo deduplicacao estavel ---
def pontos_to_xlsx_selection(selected_pontos: List[str], selected_vars: List[str]) -> Selections:
    result: Selections = {}
    vars_dedup: List[str] = []
    for v in selected_vars or []:
        vv = str(v).strip()
        if vv and vv not in vars_dedup:
            vars_dedup.append(vv)
    if not vars_dedup:
        return {}

    for ponto in selected_pontos or []:
        parts = str(ponto).split("|")
        equip = parts[2].strip() if len(parts) > 2 else ""
        if not equip:
            continue
        result.setdefault(equip, [])
        for vv in vars_dedup:
            if vv not in result[equip]:
                result[equip].append(vv)
    return {k: result[k] for k in sorted(result)}
