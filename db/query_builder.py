from __future__ import annotations

from datetime import datetime
import numbers
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


MAX_FILTER_TEXT = 120
MAX_LIST_SIZE = 200
MAX_LIMIT = 5000
DISTINCT_ALLOWLIST = {
    "SE": "SE",
    "BAY": "BAY",
    "EQUIPAMENTO": "EQUIPAMENTO",
    "TERMINAL": "TERMINAL",
    "ponto_id": "ponto_id",
    "var": "var",
}


def _norm_text(value: Optional[str], max_len: int = MAX_FILTER_TEXT) -> str:
    text = str(value or "").strip()
    if len(text) > max_len:
        raise ValueError(f"Texto acima do limite ({max_len}).")
    return text


def _norm_int(value: Optional[int], *, min_value: int, max_value: int, field: str) -> Optional[int]:
    if value is None:
        return None
    parsed: Optional[int] = None
    if isinstance(value, numbers.Integral):
        parsed = int(value)
    elif isinstance(value, str):
        v = value.strip()
        if v.isdigit():
            parsed = int(v)
    if parsed is None:
        raise ValueError(f"{field} deve ser inteiro.")
    if parsed < min_value or parsed > max_value:
        raise ValueError(f"{field} fora do intervalo permitido.")
    return parsed


def _norm_list(items: Optional[Sequence[str]], *, field: str, max_items: int = MAX_LIST_SIZE) -> List[str]:
    vals = [str(i).strip() for i in (items or []) if str(i).strip()]
    if len(vals) > max_items:
        raise ValueError(f"{field} excede o maximo de itens permitido.")
    if any(len(v) > MAX_FILTER_TEXT for v in vals):
        raise ValueError(f"{field} contem valor acima do tamanho permitido.")
    return vals


def _validate_timestamp(ts: Optional[str], *, field: str) -> Optional[str]:
    if not ts:
        return None
    ts_value = _norm_text(ts, 19)
    try:
        datetime.strptime(ts_value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError(f"{field} invalido. Use YYYY-MM-DD HH:MM:SS.") from exc
    return ts_value


def _in_placeholders(values: Iterable[object]) -> str:
    return "(" + ",".join(["?"] * len(list(values))) + ")"


# --- CHANGED: suporte a filtro por ponto_id exato e busca por ponto_id ---
def build_filters(
    *,
    equips_selected: Optional[Sequence[str]],
    equip_like: Optional[str],
    vars_sel: Optional[Sequence[str]],
    se_sel: Optional[Sequence[str]] = None,
    bay_sel: Optional[Sequence[str]] = None,
    equipamento_sel: Optional[Sequence[str]] = None,
    terminal_sel: Optional[Sequence[str]] = None,
    ponto_ids_sel: Optional[Sequence[str]] = None,
    ponto_id_like: Optional[str] = None,
    advanced_equals: Optional[Dict[str, Sequence[str]]] = None,
    advanced_ranges: Optional[Dict[str, Tuple[float, float]]] = None,
    ano: Optional[int],
    mes: Optional[int],
    meses_sel: Optional[Sequence[int]] = None,
    t0: Optional[str] = None,
    t1: Optional[str] = None,
) -> Tuple[str, Tuple[object, ...]]:
    clauses: List[str] = []
    params: List[object] = []

    ano_v = _norm_int(ano, min_value=2000, max_value=2100, field="ano")
    mes_v = _norm_int(mes, min_value=1, max_value=12, field="mes")
    meses_v = [
        item
        for item in (_norm_int(m, min_value=1, max_value=12, field="mes") for m in (meses_sel or []))
        if item is not None
    ]
    t0_v = _validate_timestamp(t0, field="t0")
    t1_v = _validate_timestamp(t1, field="t1")
    equip_like_v = _norm_text(equip_like)
    equips_v = _norm_list(equips_selected, field="equips_selected")
    vars_v = _norm_list(vars_sel, field="vars_sel")
    se_v = _norm_list(se_sel, field="se_sel")
    bay_v = _norm_list(bay_sel, field="bay_sel")
    equipamento_v = _norm_list(equipamento_sel, field="equipamento_sel")
    terminal_v = _norm_list(terminal_sel, field="terminal_sel")
    ponto_ids_v = _norm_list(ponto_ids_sel, field="ponto_ids_sel")
    ponto_like_v = _norm_text(ponto_id_like)

    if ano_v is not None:
        clauses.append("ano = ?")
        params.append(ano_v)
    if mes_v is not None:
        clauses.append("mes = ?")
        params.append(mes_v)
    elif meses_v:
        clauses.append(f"mes IN {_in_placeholders(meses_v)}")
        params.extend(meses_v)

    if equips_v and not equipamento_v:
        clauses.append(f"equip_id IN {_in_placeholders(equips_v)}")
        params.extend(equips_v)
    elif equip_like_v:
        clauses.append("(LOWER(equip_id) LIKE '%' || ? || '%' OR LOWER(CAST(EQUIPAMENTO AS VARCHAR)) LIKE '%' || ? || '%')")
        params.extend([equip_like_v.lower(), equip_like_v.lower()])

    if vars_v:
        clauses.append(f"var IN {_in_placeholders(vars_v)}")
        params.extend(vars_v)

    if se_v:
        clauses.append(f"SE IN {_in_placeholders(se_v)}")
        params.extend(se_v)
    if bay_v:
        clauses.append(f"BAY IN {_in_placeholders(bay_v)}")
        params.extend(bay_v)
    if equipamento_v:
        clauses.append(f"EQUIPAMENTO IN {_in_placeholders(equipamento_v)}")
        params.extend(equipamento_v)
    if terminal_v:
        clauses.append(f"CAST(TERMINAL AS VARCHAR) IN {_in_placeholders(terminal_v)}")
        params.extend(terminal_v)
    if ponto_ids_v:
        clauses.append(f"CAST(ponto_id AS VARCHAR) IN {_in_placeholders(ponto_ids_v)}")
        params.extend(ponto_ids_v)
    if ponto_like_v:
        clauses.append("LOWER(CAST(ponto_id AS VARCHAR)) LIKE '%' || ? || '%'")
        params.append(ponto_like_v.lower())

    for col, values in (advanced_equals or {}).items():
        safe_col = _norm_text(col, 80)
        if not safe_col.replace("_", "").isalnum():
            raise ValueError("Coluna de filtro avancado invalida.")
        vv = _norm_list(values, field=f"advanced_{safe_col}")
        if vv:
            clauses.append(f"CAST({safe_col} AS VARCHAR) IN {_in_placeholders(vv)}")
            params.extend(vv)

    for col, rng in (advanced_ranges or {}).items():
        safe_col = _norm_text(col, 80)
        if not safe_col.replace("_", "").isalnum():
            raise ValueError("Coluna de range avancado invalida.")
        lo, hi = float(rng[0]), float(rng[1])
        clauses.append(f"CAST({safe_col} AS DOUBLE) BETWEEN ? AND ?")
        params.extend([lo, hi])

    if t0_v:
        clauses.append("timestamp >= CAST(? AS TIMESTAMP)")
        params.append(t0_v)
    if t1_v:
        clauses.append("timestamp <= CAST(? AS TIMESTAMP)")
        params.append(t1_v)

    return (" AND ".join(clauses) if clauses else "TRUE"), tuple(params)


# --- CHANGED: suporte a include_empty e filtros hierarquicos reutilizando build_filters ---
def build_distinct_query(
    *,
    target_col: str,
    ano: Optional[int] = None,
    mes: Optional[int] = None,
    t0: Optional[str] = None,
    t1: Optional[str] = None,
    se_sel: Optional[Sequence[str]] = None,
    bay_sel: Optional[Sequence[str]] = None,
    equipamento_sel: Optional[Sequence[str]] = None,
    terminal_sel: Optional[Sequence[str]] = None,
    ponto_ids_sel: Optional[Sequence[str]] = None,
    ponto_id_like: Optional[str] = None,
    limit: Optional[int] = None,
    include_empty: bool = False,
) -> Tuple[str, Tuple[object, ...]]:
    col_key = _norm_text(target_col, 32)
    if col_key not in DISTINCT_ALLOWLIST:
        raise ValueError("Coluna de DISTINCT nao permitida.")
    col_sql = DISTINCT_ALLOWLIST[col_key]

    where_sql, params = build_filters(
        equips_selected=None,
        equip_like=None,
        vars_sel=None,
        se_sel=se_sel,
        bay_sel=bay_sel,
        equipamento_sel=equipamento_sel,
        terminal_sel=terminal_sel,
        ponto_ids_sel=ponto_ids_sel,
        ponto_id_like=ponto_id_like,
        advanced_equals=None,
        advanced_ranges=None,
        ano=ano,
        mes=mes,
        t0=t0,
        t1=t1,
    )
    sql = (
        f"SELECT DISTINCT CAST({col_sql} AS VARCHAR) AS v "
        f"FROM medicoes WHERE {where_sql} "
        f"AND {col_sql} IS NOT NULL "
    )
    if not include_empty:
        sql += f"AND CAST({col_sql} AS VARCHAR) <> '' "
    sql += "ORDER BY 1"
    out_params: Tuple[object, ...] = tuple(params)
    if limit is not None:
        lim = int(limit)
        if lim < 1 or lim > MAX_LIMIT:
            raise ValueError("Limit fora do intervalo permitido.")
        sql += " LIMIT ?"
        out_params = tuple(params) + (lim,)
    sql += ";"
    return sql, out_params


# --- NEW: query dedicada para pontos candidatos em cascata ---
def build_ponto_query(
    *,
    ano: Optional[int],
    mes: Optional[int],
    se_sel: Optional[Sequence[str]] = None,
    bay_sel: Optional[Sequence[str]] = None,
    equipamento_sel: Optional[Sequence[str]] = None,
    terminal_sel: Optional[Sequence[str]] = None,
    ponto_id_like: Optional[str] = None,
    limit: int = 500,
) -> Tuple[str, Tuple[object, ...]]:
    return build_distinct_query(
        target_col="ponto_id",
        ano=ano,
        mes=mes,
        se_sel=se_sel,
        bay_sel=bay_sel,
        equipamento_sel=equipamento_sel,
        terminal_sel=terminal_sel,
        ponto_id_like=ponto_id_like,
        limit=limit,
    )


# --- NEW: query de variaveis limitada aos ponto_id selecionados ---
def build_vars_for_pontos_query(
    *,
    ano: Optional[int],
    mes: Optional[int],
    ponto_ids_sel: Sequence[str],
) -> Tuple[str, Tuple[object, ...]]:
    where_sql, params = build_filters(
        equips_selected=None,
        equip_like=None,
        vars_sel=None,
        ponto_ids_sel=ponto_ids_sel,
        ano=ano,
        mes=mes,
        t0=None,
        t1=None,
    )
    sql = f"SELECT DISTINCT var FROM medicoes WHERE {where_sql} ORDER BY var;"
    return sql, tuple(params)


# --- NEW: descoberta de variaveis por filtros de contexto (evita IN gigante de ponto_id) ---
def build_vars_for_context_query(
    *,
    ano: Optional[int],
    mes: Optional[int],
    se_sel: Optional[Sequence[str]] = None,
    bay_sel: Optional[Sequence[str]] = None,
    equipamento_sel: Optional[Sequence[str]] = None,
    terminal_sel: Optional[Sequence[str]] = None,
    ponto_id_like: Optional[str] = None,
) -> Tuple[str, Tuple[object, ...]]:
    where_sql, params = build_filters(
        equips_selected=None,
        equip_like=None,
        vars_sel=None,
        se_sel=se_sel,
        bay_sel=bay_sel,
        equipamento_sel=equipamento_sel,
        terminal_sel=terminal_sel,
        ponto_id_like=ponto_id_like,
        ano=ano,
        mes=mes,
        t0=None,
        t1=None,
    )
    sql = f"SELECT DISTINCT var FROM medicoes WHERE {where_sql} ORDER BY var;"
    return sql, tuple(params)


def build_order_by(
    sort_key: str,
    sort_dir: str,
    allowlist: dict[str, str],
) -> str:
    key = _norm_text(sort_key, 64)
    direction = _norm_text(sort_dir, 8).upper()
    if key not in allowlist:
        raise ValueError("Coluna de ordenacao nao permitida.")
    if direction not in {"ASC", "DESC"}:
        raise ValueError("Direcao de ordenacao invalida.")
    return f"ORDER BY {allowlist[key]} {direction}"


def build_pagination(limit: int, offset: int) -> Tuple[str, Tuple[int, int]]:
    if not isinstance(limit, int) or not isinstance(offset, int):
        raise ValueError("Paginacao invalida.")
    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError("Limit fora do intervalo permitido.")
    if offset < 0:
        raise ValueError("Offset invalido.")
    return "LIMIT ? OFFSET ?", (limit, offset)
