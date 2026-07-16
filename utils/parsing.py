from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import pandas as pd


_LOG = logging.getLogger(__name__)
_NULL_TOKENS = {"", "na", "n/a", "nan", "none", "null", "-"}
_TS_FORMATS = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y")


def parse_timestamp_br(series: pd.Series, *, field_name: str = "timestamp") -> pd.Series:
    src = series.astype("string").str.strip()
    out = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    for fmt in _TS_FORMATS:
        pending = out.isna() & src.notna() & (src != "")
        if not pending.any():
            break
        out.loc[pending] = pd.to_datetime(src.loc[pending], format=fmt, errors="coerce", dayfirst=True)

    pending = out.isna() & src.notna() & (src != "")
    if pending.any():
        out.loc[pending] = pd.to_datetime(src.loc[pending], errors="coerce", dayfirst=True)

    total = int(len(src))
    nat_count = int(out.isna().sum())
    nat_pct = (100.0 * nat_count / total) if total else 0.0
    if nat_count > 0:
        bad_examples = src[out.isna() & src.notna() & (src != "")].drop_duplicates().head(3).tolist()
        _LOG.warning(
            "parse_timestamp_br field=%s nat_pct=%.2f nat_count=%d total=%d bad_examples=%s",
            field_name,
            nat_pct,
            nat_count,
            total,
            bad_examples,
        )
    else:
        _LOG.info("parse_timestamp_br field=%s nat_pct=0.00 nat_count=0 total=%d", field_name, total)
    return out


def parse_number_ptbr(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return float(value)

    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        return None
    if text.lower() in _NULL_TOKENS:
        return None

    norm = text
    has_comma = "," in norm
    has_dot = "." in norm
    if has_comma and has_dot:
        if norm.rfind(",") > norm.rfind("."):
            norm = norm.replace(".", "").replace(",", ".")
        else:
            norm = norm.replace(",", "")
    elif has_comma:
        norm = norm.replace(".", "").replace(",", ".")

    try:
        return float(Decimal(norm))
    except (InvalidOperation, ValueError):
        return None


def parse_number_ptbr_series(series: pd.Series) -> pd.Series:
    src = series.astype("string").str.strip()
    s = src.str.replace("\u00a0", "", regex=False).str.replace(" ", "", regex=False)
    s = s.mask(s.str.lower().isin(_NULL_TOKENS))

    out = s.copy()
    both = out.str.contains(",", na=False) & out.str.contains(r"\.", na=False)
    comma_decimal = both & (out.str.rfind(",") > out.str.rfind("."))
    dot_decimal = both & ~comma_decimal

    out.loc[comma_decimal] = out.loc[comma_decimal].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    out.loc[dot_decimal] = out.loc[dot_decimal].str.replace(",", "", regex=False)

    only_comma = out.str.contains(",", na=False) & ~out.str.contains(r"\.", na=False)
    out.loc[only_comma] = out.loc[only_comma].str.replace(",", ".", regex=False)

    return pd.to_numeric(out, errors="coerce")
