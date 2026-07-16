from __future__ import annotations

import datetime as dt
from typing import Iterable, List, Optional, Sequence, Tuple

import pandas as pd


def normalize_month_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        month = int(str(value).strip())
    except Exception:
        return None
    if 1 <= month <= 12:
        return month
    return None


def normalize_year_int(value: object, *, min_year: int = 2000, max_year: int = 2100) -> Optional[int]:
    if value is None:
        return None
    try:
        year = int(str(value).strip())
    except Exception:
        return None
    if int(min_year) <= year <= int(max_year):
        return year
    return None


def normalize_day_value(value: object) -> Optional[str]:
    if value is None:
        return None
    try:
        ts = pd.Timestamp(value)
    except Exception:
        return None
    if pd.isna(ts):
        return None
    if ts.tzinfo is not None:
        ts = ts.tz_convert(None)
    return ts.date().isoformat()


def normalize_month_list(raw_values: object, *, valid_months: Sequence[int]) -> List[int]:
    if not isinstance(raw_values, (list, tuple)):
        return []
    valid = {int(m) for m in valid_months}
    out: List[int] = []
    for raw in raw_values:
        month = normalize_month_int(raw)
        if month is None or month not in valid or month in out:
            continue
        out.append(month)
    return out


def latest_available_year_month(by_month: pd.DataFrame) -> Tuple[int, int]:
    if by_month.empty:
        raise ValueError("Sem dados de ano/mes para selecionar padrao.")
    pairs = [
        (int(row.ano), int(row.mes))
        for row in by_month[["ano", "mes"]].itertuples(index=False)
        if normalize_month_int(row.mes) is not None
    ]
    if not pairs:
        raise ValueError("Sem pares de ano/mes validos em medicoes.")
    return max(pairs, key=lambda p: (p[0], p[1]))


def months_for_year(by_month: pd.DataFrame, year: int) -> List[int]:
    if by_month.empty:
        return []
    return sorted(
        {
            int(m)
            for m in by_month[by_month["ano"] == int(year)]["mes"].tolist()
            if normalize_month_int(m) is not None
        }
    )


def months_for_years(
    by_month: pd.DataFrame,
    years: Sequence[int],
    *,
    min_year: int = 2000,
    max_year: int = 2100,
) -> List[int]:
    years_norm = set(coerce_anos_sel(years, min_year=min_year, max_year=max_year))
    if by_month.empty or not years_norm:
        return []
    return sorted(
        {
            int(row.mes)
            for row in by_month[["ano", "mes"]].itertuples(index=False)
            if int(row.ano) in years_norm and normalize_month_int(row.mes) is not None
        }
    )


def month_bounds(ano: int, mes: int) -> Tuple[str, str]:
    start = dt.datetime(int(ano), int(mes), 1, 0, 0, 0)
    if int(mes) == 12:
        next_month = dt.datetime(int(ano) + 1, 1, 1, 0, 0, 0)
    else:
        next_month = dt.datetime(int(ano), int(mes) + 1, 1, 0, 0, 0)
    end = next_month - dt.timedelta(seconds=1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def month_selection_bounds(ano: int, meses_sel: Sequence[int]) -> Tuple[str, str]:
    meses_norm = sorted({int(m) for m in meses_sel})
    if not meses_norm:
        raise ValueError("Selecione ao menos um mes.")
    t0, _ = month_bounds(int(ano), int(meses_norm[0]))
    _, t1 = month_bounds(int(ano), int(meses_norm[-1]))
    return t0, t1


def coerce_dias_sel(dias_sel: Iterable[object]) -> Tuple[str, ...]:
    normalized = [d for d in (normalize_day_value(v) for v in dias_sel) if d is not None]
    return tuple(dict.fromkeys(normalized))


def day_selection_bounds(dias_sel: Sequence[str]) -> Tuple[str, str]:
    dias_norm = sorted(set(coerce_dias_sel(dias_sel)))
    if not dias_norm:
        raise ValueError("Selecione ao menos um dia.")
    start = dt.datetime.strptime(dias_norm[0], "%Y-%m-%d")
    end = dt.datetime.strptime(dias_norm[-1], "%Y-%m-%d") + dt.timedelta(days=1, seconds=-1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def format_selected_days_label(dias_sel: Sequence[str], *, max_items: int = 6) -> str:
    dias_norm = list(coerce_dias_sel(dias_sel))
    if not dias_norm:
        return ""
    if len(dias_norm) <= max_items:
        return ", ".join(dias_norm)
    return ", ".join(dias_norm[:max_items]) + f" (+{len(dias_norm) - max_items})"


def coerce_meses_sel(meses_sel: Sequence[object], *, mes: object = None) -> Tuple[int, ...]:
    if meses_sel:
        normalized = [m for m in (normalize_month_int(v) for v in meses_sel) if m is not None]
        return tuple(dict.fromkeys(normalized))
    month = normalize_month_int(mes)
    if month is not None:
        return (month,)
    return ()


def coerce_anos_sel(
    anos_sel: Sequence[object],
    *,
    min_year: int = 2000,
    max_year: int = 2100,
) -> Tuple[int, ...]:
    normalized = [y for y in (normalize_year_int(v, min_year=min_year, max_year=max_year) for v in anos_sel) if y is not None]
    return tuple(dict.fromkeys(normalized))


def effective_years(
    ano: object,
    anos_sel: Sequence[object],
    *,
    min_year: int = 2000,
    max_year: int = 2100,
) -> Tuple[int, ...]:
    years = coerce_anos_sel(anos_sel, min_year=min_year, max_year=max_year)
    if years:
        return years
    year = normalize_year_int(ano, min_year=min_year, max_year=max_year)
    return (year,) if year is not None else ()


def year_month_selection_bounds(
    anos_sel: Sequence[object],
    meses_sel: Sequence[object],
    *,
    min_year: int = 2000,
    max_year: int = 2100,
) -> Tuple[str, str]:
    anos_norm = list(coerce_anos_sel(anos_sel, min_year=min_year, max_year=max_year))
    if not anos_norm:
        raise ValueError("Selecione ao menos um ano.")
    meses_norm = sorted({int(m) for m in coerce_meses_sel(meses_sel)})
    if not meses_norm:
        raise ValueError("Selecione ao menos um mes.")
    start = pd.Timestamp(int(min(anos_norm)), int(meses_norm[0]), 1, 0, 0, 0)
    max_year_value = int(max(anos_norm))
    max_month = int(meses_norm[-1])
    if max_month == 12:
        next_month = pd.Timestamp(max_year_value + 1, 1, 1, 0, 0, 0)
    else:
        next_month = pd.Timestamp(max_year_value, max_month + 1, 1, 0, 0, 0)
    end = next_month - pd.Timedelta(seconds=1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")
