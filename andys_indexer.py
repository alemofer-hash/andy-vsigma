from __future__ import annotations

import os
import re
import json
import time
import glob
import hashlib
import unicodedata
from pathlib import Path
from typing import Any, Optional, Iterable, List, Dict, Tuple

import pandas as pd

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from config import (
    assert_readonly_source,
    assert_within_allowed_root,
    get_db_path,
    get_lake_root,
    get_source_root,
    get_work_root,
    load_config,
)
from utils.parsing import parse_number_ptbr_series, parse_timestamp_br


# ============================================================
# ✅ ANDY'S — Config + Indexação + Lake leve + Query
# Rede interna / máquina local
# ============================================================

CONFIG_FILENAME = "andys_config.json"
INGEST_FINGERPRINT_VERSION = "20260309_tsfix_v1"

FILENAME_RE = re.compile(
    r"Parâmetros\s+elétricos\s*-\s*(\d{2})_(\d{4})\s*-\s*Todas\s+SEs",
    re.IGNORECASE
)

TS_KEYS = ["E3TIMESTAMP", "TIMESTAMP", "DATAHORA", "DATA_HORA", "DATETIME", "TIME", "HORA"]
ID_KEYS = ["IDENTIFICADOR", "ID", "EQUIP", "EQUIPAMENTO", "BAY", "ALIMENTADOR", "TRANSFORMADOR", "ASSET", "CODIGO"]

VAR_PATTERNS = {
    "P":  ["P", "POTENCIAATIVA", "POTATIVA", "PACTIVA", "ACTIVEPOWER"],
    "Q":  ["Q", "POTENCIAREATIVA", "POTREATIVA", "QREATIVA", "REACTIVEPOWER"],
    "IA": ["IA", "CORRENTEIA", "IARMS"],
    "IB": ["IB", "CORRENTEIB", "IBRMS"],
    "IC": ["IC", "CORRENTEIC", "ICRMS"],
    "IN": ["IN", "CORRENTEIN", "INEUTRO", "I_NEUTRO"],
    "VA": ["VA", "TENSAOVA", "VARMS", "VAN", "V_A"],
    "VB": ["VB", "TENSAOVB", "VBRMS", "VBN", "V_B"],
    "VC": ["VC", "TENSAOVC", "VCRMS", "VCN", "V_C"],
    "VAB": ["VAB", "V_AB", "TENSAOVAB"],
    "VBC": ["VBC", "V_BC", "TENSAOVBC"],
    "VCA": ["VCA", "V_CA", "TENSAOVCA"],
    "FP": ["FP", "FATORDEPOTENCIA", "COSPHI", "COSFI"],
}
VAR_CLASS = {
    "P": "POT", "Q": "POT",
    "IA": "COR", "IB": "COR", "IC": "COR", "IN": "COR",
    "VA": "TEN", "VB": "TEN", "VC": "TEN",
    "VAB": "TEN", "VBC": "TEN", "VCA": "TEN",
    "FP": "FP",
}

CANONICAL_KEYS = {
    "SE",
    "BAY",
    "EQUIPAMENTO",
    "TERMINAL",
    "TIMESTAMP",
    "IDENTIFICADOR_RAW",
    "ponto_id",
    "context_quality",
    "parsed_terminal_ok",
}
CONTEXT_COLS = {
    "TIMESTAMP",
    "SE",
    "BAY",
    "EQUIPAMENTO",
    "TERMINAL",
    "IDENTIFICADOR_RAW",
    "ponto_id",
    "context_quality",
    "parsed_terminal_ok",
}

COLUMN_SYNONYMS = {
    "SUBESTACAO": "SE",
    "SUBESTACAOSE": "SE",
    "SE": "SE",
    "BAY": "BAY",
    "EQUIP": "EQUIPAMENTO",
    "EQUIPAMENTO": "EQUIPAMENTO",
    "IDENTIFICADOR": "IDENTIFICADOR_RAW",
    "ID": "IDENTIFICADOR_RAW",
    "TERMINAL": "TERMINAL",
    "E3TIMESTAMP": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "DATAHORA": "TIMESTAMP",
    "DATA_HORA": "TIMESTAMP",
    "DATETIME": "TIMESTAMP",
    "IN": "IN",
    "IN_": "IN",
}


def _norm(s) -> str:
    return str(s).strip() if s is not None else ""

def _compact_upper(s) -> str:
    return _norm(s).upper().replace(" ", "").replace("_", "").replace("-", "")


def _strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def normalize_column_name(name: str) -> str:
    raw = _norm(name)
    if not raw:
        return raw
    raw = re.sub(r"\s+", " ", raw).strip()
    key = _compact_upper(_strip_accents(raw))
    return COLUMN_SYNONYMS.get(key, raw)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    drop_cols = [c for c in df.columns if str(c).strip().upper().startswith("UNNAMED:")]
    out = df.drop(columns=drop_cols, errors="ignore").copy()
    new_cols: List[str] = []
    seen: Dict[str, int] = {}
    for c in out.columns:
        base = normalize_column_name(str(c))
        if base in seen:
            seen[base] += 1
            new_cols.append(f"{base}__{seen[base]}")
        else:
            seen[base] = 1
            new_cols.append(base)
    out.columns = new_cols
    return out


def parse_terminal_from_identificador(identificador: Any) -> Optional[str]:
    txt = _norm(identificador)
    if not txt:
        return None
    m = re.search(r"terminal\s*([12])", txt, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\bT\s*([12])\b", txt, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def parse_terminal_from_equipamento(equipamento: Any) -> Optional[str]:
    txt = _norm(equipamento)
    if not txt:
        return None
    m = re.search(r"\bTR[-\s]?\d+\s*(?:T|TERMINAL)\s*([12])\b", txt, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def build_ponto_id(se: Any, bay: Any, equipamento: Any, terminal: Any) -> str:
    se_txt = _norm(se) or "-"
    bay_txt = _norm(bay) or "-"
    equip_txt = _norm(equipamento) or "-"
    term_txt = _norm(terminal) or "-"
    return f"{se_txt}|{bay_txt}|{equip_txt}|{term_txt}"


def _canonical_var_name(name: Any) -> str:
    k = _compact_upper(_strip_accents(str(name)))
    for base, aliases in VAR_PATTERNS.items():
        base_k = _compact_upper(base)
        if k == base_k:
            return base
        for alias in aliases:
            if k == _compact_upper(alias):
                return base
    for base in sorted(VAR_PATTERNS, key=len, reverse=True):
        base_k = _compact_upper(base)
        if len(base_k) > 1 and k.endswith(base_k):
            return base
    return _norm(name)


def _normalize_timestamp_series(series: pd.Series) -> pd.Series:
    return parse_timestamp_br(series, field_name="TIMESTAMP")


def _normalize_decimal_numeric(series: pd.Series) -> pd.Series:
    return parse_number_ptbr_series(series)


def _ensure_context_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_columns(df)
    for col in ["SE", "BAY", "EQUIPAMENTO", "TERMINAL", "TIMESTAMP", "IDENTIFICADOR_RAW"]:
        if col not in out.columns:
            out[col] = None

    # Compatibilidade de identificador/equipamento.
    if out["EQUIPAMENTO"].isna().all() and "IDENTIFICADOR_RAW" in out.columns:
        out["EQUIPAMENTO"] = out["IDENTIFICADOR_RAW"]

    out["TIMESTAMP"] = _normalize_timestamp_series(out["TIMESTAMP"])
    out["IDENTIFICADOR_RAW"] = out["IDENTIFICADOR_RAW"].astype(str)
    out["EQUIPAMENTO"] = out["EQUIPAMENTO"].astype(str)
    out["SE"] = out["SE"].astype(str)
    out["BAY"] = out["BAY"].astype(str)

    parsed_ok = []
    terminals: List[str] = []
    for _, row in out[["EQUIPAMENTO", "TERMINAL", "IDENTIFICADOR_RAW"]].iterrows():
        equip = _norm(row["EQUIPAMENTO"])
        t = _norm(row["TERMINAL"])
        used_parse = False
        if not t:
            t = parse_terminal_from_identificador(row["IDENTIFICADOR_RAW"]) or parse_terminal_from_equipamento(equip) or ""
            used_parse = bool(t)
        terminals.append(t)
        parsed_ok.append(used_parse)

    out["TERMINAL"] = terminals
    out["parsed_terminal_ok"] = parsed_ok
    out["ponto_id"] = [
        build_ponto_id(se, bay, equip, term)
        for se, bay, equip, term in zip(out["SE"], out["BAY"], out["EQUIPAMENTO"], out["TERMINAL"])
    ]

    quality: List[str] = []
    for _, row in out[["EQUIPAMENTO", "TERMINAL", "parsed_terminal_ok"]].iterrows():
        equip = _norm(row["EQUIPAMENTO"]).upper()
        term = _norm(row["TERMINAL"])
        is_tr = bool(re.match(r"^TR[-\s]?\d+", equip))
        if is_tr and not term:
            quality.append("MISSING")
        elif row["parsed_terminal_ok"]:
            quality.append("PARSED")
        else:
            quality.append("OK")
    out["context_quality"] = quality
    return out


def backfill_context_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Backfill de contexto para historico sem SE/BAY/TERMINAL.
    Mantem NULL quando nao for possivel inferir e marca context_quality.
    """
    return _ensure_context_columns(df)

def _best_match_col(columns: Iterable[str], candidates: List[str]) -> Optional[str]:
    comp = {_compact_upper(c): c for c in columns}
    for cand in candidates:
        k = _compact_upper(cand)
        if k in comp:
            return comp[k]
    for c in columns:
        kc = _compact_upper(c)
        for cand in candidates:
            if _compact_upper(cand) in kc:
                return c
    return None

def _detect_vars(columns: Iterable[str]) -> Tuple[List[str], Dict[str, str]]:
    comp = {_compact_upper(c): c for c in columns}
    found: Dict[str, str] = {}

    for base, aliases in VAR_PATTERNS.items():
        for a in aliases:
            ka = _compact_upper(a)
            if ka in comp:
                found[base] = comp[ka]
                break

    for base in ["IA", "IB", "IC", "IN", "VA", "VB", "VC", "VAB", "VBC", "VCA", "FP", "P", "Q"]:
        if base not in found:
            for c in columns:
                if _compact_upper(c).endswith(base):
                    found[base] = c
                    break

    order = ["P", "Q", "IA", "IB", "IC", "IN", "VA", "VB", "VC", "VAB", "VBC", "VCA", "FP"]
    vars_detectadas = [found[b] for b in order if b in found]

    var_class: Dict[str, str] = {}
    for base, orig in found.items():
        var_class[orig] = VAR_CLASS.get(base, "")

    return vars_detectadas, var_class


# --- NEW: descoberta dinamica de colunas de medicao fora do contexto ---
def get_variable_cols(df: pd.DataFrame) -> List[str]:
    """
    Return all non-context columns from the canonical dataframe.
    This helper is primarily for tests and future reuse.
    """
    context_upper = {c.upper() for c in CONTEXT_COLS}
    return [c for c in df.columns if str(c).upper() not in context_upper]

def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def _lake_root(work_root: str) -> str:
    return get_lake_root(work_root)

def _config_path(work_root: str) -> str:
    return os.path.join(_lake_root(work_root), CONFIG_FILENAME)

def _duckdb_path(work_root: str) -> str:
    return get_db_path(work_root)

def _manifest_path(work_root: str) -> str:
    return os.path.join(_lake_root(work_root), "manifest.json")


def _safe_source_open_read(path: str, source_root: str):
    assert_readonly_source(path, source_root, mode="rb")
    return open(path, "rb")


def _file_sha256(path: str, source_root: str) -> str:
    h = hashlib.sha256()
    with _safe_source_open_read(path, source_root) as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _guard_output_path(path: str, *, source_root: str, allowed_root: Optional[str]) -> str:
    resolved = assert_within_allowed_root(path, allowed_root)
    assert_readonly_source(resolved, source_root, mode="wb")
    return resolved

def _parse_month_year(filename: str) -> Optional[Tuple[int, int]]:
    m = FILENAME_RE.search(filename)
    if not m:
        m = re.search(r"(\d{2})_(\d{4})", filename)
        if not m:
            return None
    mm = int(m.group(1))
    yy = int(m.group(2))
    if mm < 1 or mm > 12:
        return None
    return (yy, mm)

# ============================================================
# ✅ CSV Robust: detecta encoding + separador + linha de header real
# ============================================================
CSV_ENCODINGS_TRY = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
CSV_SEPS_TRY = [";", ",", "\t", "|"]
CSV_SCAN_MAX_LINES = 200
CSV_DEBUG_DETECTION = os.environ.get("ANDYS_CSV_DEBUG", "1") == "1"


def _split_csv_line(line: str, sep: str) -> List[str]:
    return [p.strip().strip('"').strip("'") for p in line.rstrip("\r\n").split(sep)]


def _read_head_lines(path: str, encoding: str, max_lines: int = CSV_SCAN_MAX_LINES) -> List[str]:
    lines: List[str] = []
    with open(path, "r", encoding=encoding) as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            lines.append(line)
    return lines


def _score_header_tokens(columns: List[str]) -> Tuple[int, bool, bool]:
    col_ts = _best_match_col(columns, TS_KEYS)
    col_id = _best_match_col(columns, ID_KEYS)
    vars_detectadas, _ = _detect_vars(columns)

    has_ts = col_ts is not None
    has_id = col_id is not None
    # Prioriza presença de TS+ID; variáveis elétricas aumentam confiança.
    score = (100 if has_ts and has_id else 0) + (10 if has_ts or has_id else 0) + len(vars_detectadas)
    return score, has_ts, has_id


def _detect_csv_layout(
    path: str,
    preview_rows: int = 80,
    scan_lines: int = CSV_SCAN_MAX_LINES,
) -> Tuple[pd.DataFrame, str, str, int]:
    """
    Detecta:
    - encoding
    - separador
    - skiprows (linhas anteriores ao cabeçalho real)
    Retorna também um preview já lido com essa configuração.
    """
    last_err: Optional[Exception] = None

    for enc in CSV_ENCODINGS_TRY:
        try:
            lines = _read_head_lines(path, encoding=enc, max_lines=scan_lines)
        except UnicodeDecodeError as e:
            last_err = e
            continue
        except Exception as e:
            last_err = e
            continue

        best: Optional[Tuple[int, int, str, List[str]]] = None
        # (score, header_idx, sep, columns)
        for sep in CSV_SEPS_TRY:
            for idx, raw in enumerate(lines):
                line = raw.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    continue

                cols = _split_csv_line(raw, sep)
                if len(cols) <= 1:
                    continue

                score, has_ts, has_id = _score_header_tokens(cols)
                if not (has_ts and has_id):
                    continue

                candidate = (score, idx, sep, cols)
                if best is None or candidate[0] > best[0]:
                    best = candidate

        if best is None:
            continue

        _, header_idx, sep, _ = best
        try:
            preview = pd.read_csv(
                path,
                nrows=preview_rows,
                sep=sep,
                encoding=enc,
                skiprows=header_idx,
                engine="c",
                dtype=str,
                low_memory=False,
                on_bad_lines="skip",
            )
        except Exception as e:
            last_err = e
            continue

        cols = list(preview.columns)
        col_ts = _best_match_col(cols, TS_KEYS)
        col_id = _best_match_col(cols, ID_KEYS)
        if col_ts is None or col_id is None:
            continue

        return preview, enc, sep, header_idx

    # fallback tolerante de encoding para não abortar em byte inválido
    for sep in CSV_SEPS_TRY:
        try:
            preview = pd.read_csv(
                path,
                nrows=preview_rows,
                sep=sep,
                encoding="latin1",
                engine="c",
                dtype=str,
                low_memory=False,
                on_bad_lines="skip",
            )
            cols = list(preview.columns)
            col_ts = _best_match_col(cols, TS_KEYS)
            col_id = _best_match_col(cols, ID_KEYS)
            if col_ts is not None and col_id is not None:
                return preview, "latin1", sep, 0
        except Exception as e:
            last_err = e

    raise ValueError(f"Falha ao detectar layout do CSV (encoding/sep/header). Último erro: {last_err}")


def _read_csv_chunks(
    path: str,
    usecols: Optional[List[str]],
    chunksize: int,
    encoding: str,
    sep: str,
    skiprows: int,
):
    """
    Gera chunks com layout já detectado.
    dtype=str evita problemas com decimal vírgula em CSV com ';'.
    """
    kw = dict(
        sep=sep,
        encoding=encoding,
        skiprows=skiprows,
        engine="c",
        low_memory=False,
        chunksize=chunksize,
        on_bad_lines="skip",
        dtype=str,
    )
    if usecols is not None:
        kw["usecols"] = usecols
    return pd.read_csv(path, **kw)


def treinar_andys(work_root: str, source_root: str, allowed_root: Optional[str]) -> None:
    lake = _guard_output_path(_lake_root(work_root), source_root=source_root, allowed_root=allowed_root)
    _ensure_dir(lake)

    cfg = {
        "env_label": "Andy's",
        "source_root": source_root,
        "work_root": work_root,
        "lake_path": lake,
        "duckdb_path": _duckdb_path(work_root),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    cfg_path = _guard_output_path(_config_path(work_root), source_root=source_root, allowed_root=allowed_root)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    manifest_path = _guard_output_path(_manifest_path(work_root), source_root=source_root, allowed_root=allowed_root)
    if not os.path.exists(manifest_path):
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"files": {}}, f, ensure_ascii=False, indent=2)

    print("[OK] Andy's configurado.")
    print("[OK] Source root (read-only):", source_root)
    print("[OK] Work root:", work_root)
    print("[OK] Lake:", lake)


def listar_arquivos_brutos(source_root: str) -> List[str]:
    patterns = [
        os.path.join(source_root, "**", "*.xlsx"),
        os.path.join(source_root, "**", "*.xlsm"),
        os.path.join(source_root, "**", "*.csv"),
    ]
    files: List[str] = []
    try:
        for p in patterns:
            files.extend(glob.glob(p, recursive=True))
    except PermissionError as exc:
        raise PermissionError(f"Permissao negada ao listar arquivos em ANDYS_SOURCE_ROOT: {source_root}") from exc
    except OSError as exc:
        raise OSError(f"Falha ao acessar ANDYS_SOURCE_ROOT ({source_root}). Verifique conectividade/rede.") from exc
    out = []
    for fp in files:
        if os.path.isfile(fp):
            out.append(fp)
    return sorted(set(out))


# --- CHANGED: usa helper get_variable_cols para manter descoberta dinamica ---
def _canonical_to_long(df_canon: pd.DataFrame, ano: Optional[int], mes: Optional[int]) -> pd.DataFrame:
    if df_canon.empty:
        return pd.DataFrame(columns=["timestamp", "equip_id", "var", "classe", "valor", "ano", "mes"])

    out = df_canon.copy()
    base_exclude = {str(c).upper() for c in CONTEXT_COLS}
    measure_cols: List[str] = []
    converted: Dict[str, pd.Series] = {}
    for col in get_variable_cols(out):
        if str(col).upper() in base_exclude:
            continue
        num = _normalize_decimal_numeric(out[col])
        if num.notna().any():
            measure_cols.append(col)
            converted[col] = num

    for col, num in converted.items():
        out[col] = num

    if not measure_cols:
        return pd.DataFrame(columns=["timestamp", "equip_id", "var", "classe", "valor", "ano", "mes"])

    id_vars = [c for c in out.columns if c not in measure_cols]
    long = out.melt(
        id_vars=id_vars,
        value_vars=measure_cols,
        var_name="var",
        value_name="valor",
    ).dropna(subset=["valor", "EQUIPAMENTO"])

    long["timestamp"] = _normalize_timestamp_series(long["TIMESTAMP"])
    long = long.dropna(subset=["timestamp"])
    long["equip_id"] = long["EQUIPAMENTO"].astype(str)
    long["var"] = long["var"].map(_canonical_var_name)
    long["valor"] = pd.to_numeric(long["valor"], errors="coerce")
    long["classe"] = long["var"].map(lambda v: VAR_CLASS.get(_compact_upper(v), ""))
    if ano is not None and mes is not None:
        long["ano"] = int(ano)
        long["mes"] = int(mes)
    else:
        long["ano"] = long["timestamp"].dt.year
        long["mes"] = long["timestamp"].dt.month
    long = long.dropna(subset=["ano", "mes"])
    long["ano"] = long["ano"].astype(int)
    long["mes"] = long["mes"].astype(int)
    return long


def ler_para_canonico_e_long(filepath: str, chunksize_csv: int = 200_000) -> Tuple[pd.DataFrame, pd.DataFrame]:
    ext = os.path.splitext(filepath)[1].lower()
    name = os.path.basename(filepath)
    ym = _parse_month_year(name)
    ano: Optional[int]
    mes: Optional[int]
    if ym is None:
        ano, mes = None, None
    else:
        ano, mes = ym

    if ext in [".xlsx", ".xlsm"]:
        preview = pd.read_excel(filepath, nrows=20, engine="openpyxl")
        cols = list(preview.columns)

        col_ts = _best_match_col(cols, TS_KEYS)
        col_id = _best_match_col(cols, ID_KEYS)
        if col_ts is None or col_id is None:
            raise ValueError(f"[{name}] Nao detectei TIMESTAMP/IDENTIFICADOR no XLSX.")

        vars_detectadas, var_class = _detect_vars(cols)
        if not vars_detectadas:
            raise ValueError(f"[{name}] Nao detectei variaveis de medicao no XLSX.")

        usecols = [col_ts, col_id] + vars_detectadas
        df = pd.read_excel(filepath, usecols=usecols, engine="openpyxl")

        df[col_id] = df[col_id].astype(str)
        df[col_ts] = _normalize_timestamp_series(df[col_ts])
        df = df.dropna(subset=[col_ts, col_id])

        long = df.melt(
            id_vars=[col_ts, col_id],
            value_vars=vars_detectadas,
            var_name="var",
            value_name="valor",
        ).dropna(subset=["valor"])

        long = long.rename(columns={col_ts: "timestamp", col_id: "equip_id"})
        long = long.dropna(subset=["timestamp"])
        long["var"] = long["var"].map(_canonical_var_name)
        long["valor"] = _normalize_decimal_numeric(long["valor"])
        long["classe"] = long["var"].map(lambda v: VAR_CLASS.get(_compact_upper(v), "")).fillna("")
        if ano is not None and mes is not None:
            long["ano"] = int(ano)
            long["mes"] = int(mes)
        else:
            long["ano"] = long["timestamp"].dt.year
            long["mes"] = long["timestamp"].dt.month
        long = long.dropna(subset=["ano", "mes"])
        long["ano"] = long["ano"].astype(int)
        long["mes"] = long["mes"].astype(int)
        out_long = long[["timestamp", "equip_id", "var", "classe", "valor", "ano", "mes"]]
        canon = pd.DataFrame(
            {
                "TIMESTAMP": out_long["timestamp"],
                "EQUIPAMENTO": out_long["equip_id"],
                "SE": "",
                "BAY": "",
                "TERMINAL": "",
                "IDENTIFICADOR_RAW": out_long["equip_id"],
            }
        )
        canon = _ensure_context_columns(canon)
        return canon, out_long

    if ext == ".csv":
        preview, enc, sep, skiprows = _detect_csv_layout(filepath, preview_rows=80, scan_lines=CSV_SCAN_MAX_LINES)
        if CSV_DEBUG_DETECTION:
            print(f"[CSV-DETECT] arquivo={name}")
            print(f"[CSV-DETECT] encoding={enc} sep='{sep}' skiprows={skiprows}")
            print(f"[CSV-DETECT] colunas={list(preview.columns)[:30]}")

        canon_parts: List[pd.DataFrame] = []
        long_parts: List[pd.DataFrame] = []
        for chunk in _read_csv_chunks(
            filepath,
            usecols=None,
            chunksize=chunksize_csv,
            encoding=enc,
            sep=sep,
            skiprows=skiprows,
        ):
            chunk = normalize_columns(chunk)
            chunk = _ensure_context_columns(chunk)
            chunk = chunk.dropna(subset=["TIMESTAMP", "EQUIPAMENTO"])
            if chunk.empty:
                continue
            canon_parts.append(chunk)
            long_parts.append(_canonical_to_long(chunk, ano=ano, mes=mes))

        if not canon_parts:
            empty_canon = pd.DataFrame(columns=["TIMESTAMP", "SE", "BAY", "EQUIPAMENTO", "TERMINAL", "IDENTIFICADOR_RAW"])
            empty_long = pd.DataFrame(columns=["timestamp", "equip_id", "var", "classe", "valor", "ano", "mes"])
            return empty_canon, empty_long

        canon_df = pd.concat(canon_parts, ignore_index=True, sort=False)
        long_df = pd.concat(long_parts, ignore_index=True, sort=False) if long_parts else pd.DataFrame(
            columns=["timestamp", "equip_id", "var", "classe", "valor", "ano", "mes"]
        )
        return canon_df, long_df

    raise ValueError(f"Extensao nao suportada: {ext}")


def ler_para_long(filepath: str, chunksize_csv: int = 200_000) -> pd.DataFrame:
    _, df_long = ler_para_canonico_e_long(filepath=filepath, chunksize_csv=chunksize_csv)
    return df_long


def escrever_parquet_particionado(work_root: str, df_long: pd.DataFrame, *, source_root: str, allowed_root: Optional[str]) -> str:
    lake = _guard_output_path(_lake_root(work_root), source_root=source_root, allowed_root=allowed_root)
    _ensure_dir(lake)

    if df_long.empty:
        return ""

    outputs: List[str] = []
    grouped = df_long.groupby(["ano", "mes"], dropna=False)
    for (ano_raw, mes_raw), part in grouped:
        ano = int(ano_raw)
        mes = int(mes_raw)
        out_dir = _guard_output_path(
            os.path.join(lake, f"ano={ano}", f"mes={mes:02d}"),
            source_root=source_root,
            allowed_root=allowed_root,
        )
        _ensure_dir(out_dir)
        out_file = _guard_output_path(
            os.path.join(out_dir, f"medicoes_{ano}_{mes:02d}.parquet"),
            source_root=source_root,
            allowed_root=allowed_root,
        )
        table = pa.Table.from_pandas(part, preserve_index=False)
        pq.write_table(table, out_file, compression="zstd")
        outputs.append(out_file)

    return ";".join(outputs)


def escrever_parquet_canonico(work_root: str, df_canon: pd.DataFrame, ano: int, mes: int, *, source_root: str, allowed_root: Optional[str]) -> str:
    lake = _guard_output_path(_lake_root(work_root), source_root=source_root, allowed_root=allowed_root)
    _ensure_dir(lake)
    if df_canon.empty:
        return ""
    outputs: List[str] = []
    parts: List[Tuple[int, int, pd.DataFrame]] = []
    if ano > 0 and mes > 0:
        parts = [(int(ano), int(mes), df_canon)]
    else:
        ts = _normalize_timestamp_series(df_canon.get("TIMESTAMP"))
        aux = df_canon.copy()
        aux["_ANO"] = ts.dt.year
        aux["_MES"] = ts.dt.month
        aux = aux.dropna(subset=["_ANO", "_MES"])
        for (a, m), part in aux.groupby(["_ANO", "_MES"], dropna=False):
            parts.append((int(a), int(m), part.drop(columns=["_ANO", "_MES"])))

    for a, m, part_df in parts:
        out_dir = _guard_output_path(
            os.path.join(lake, "canonico", f"ano={a}", f"mes={m:02d}"),
            source_root=source_root,
            allowed_root=allowed_root,
        )
        _ensure_dir(out_dir)
        out_file = _guard_output_path(
            os.path.join(out_dir, f"medicoes_canon_{a}_{m:02d}.parquet"),
            source_root=source_root,
            allowed_root=allowed_root,
        )
        table = pa.Table.from_pandas(part_df, preserve_index=False)
        pq.write_table(table, out_file, compression="zstd")
        outputs.append(out_file)
    return ";".join(outputs)


def _load_manifest(work_root: str) -> dict:
    with open(_manifest_path(work_root), "r", encoding="utf-8") as f:
        return json.load(f)

def _save_manifest(work_root: str, manifest: dict, *, source_root: str, allowed_root: Optional[str]) -> None:
    manifest_path = _guard_output_path(_manifest_path(work_root), source_root=source_root, allowed_root=allowed_root)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def construir_catalogo_duckdb(work_root: str, *, source_root: str, allowed_root: Optional[str]) -> None:
    lake = _guard_output_path(_lake_root(work_root), source_root=source_root, allowed_root=allowed_root)
    db_path = _guard_output_path(_duckdb_path(work_root), source_root=source_root, allowed_root=allowed_root)

    con = duckdb.connect(db_path)
    try:
        con.execute("PRAGMA threads=4;")

        parquet_glob = os.path.join(lake, "ano=*/mes=*/medicoes_*.parquet").replace("\\", "/")
        canon_glob = os.path.join(lake, "canonico/ano=*/mes=*/medicoes_canon_*.parquet").replace("\\", "/")

        # Idempotente: recria a view a cada execução para refletir os Parquets atuais.
        con.execute("DROP VIEW IF EXISTS medicoes;")
        con.execute(f"""
            CREATE VIEW medicoes AS
            SELECT * FROM read_parquet('{parquet_glob}', union_by_name=true);
        """)
        con.execute("DROP VIEW IF EXISTS medicoes_canon;")
        con.execute(f"""
            CREATE VIEW medicoes_canon AS
            SELECT * FROM read_parquet('{canon_glob}', union_by_name=true);
        """)

        # ANALYZE em VIEW falha no DuckDB; manter apenas a view evita crash.
        print("[OK] DuckDB catalog: view medicoes criada. ANALYZE pulado (view).")
    finally:
        con.close()


def rebuild_long_lake_from_canonical(
    work_root: str,
    *,
    source_root: str,
    allowed_root: Optional[str],
    only_mismatched: bool = False,
    target_months: Optional[List[Tuple[int, int]]] = None,
) -> Dict[str, Any]:
    """Rebuild the LONG lake from already indexed canonical Parquet files.

    This public wrapper exists for packaged desktop repair paths. It does not
    read or write the corporate source tree; it only reads the local canonical
    lake and rewrites local LONG Parquet partitions, then refreshes DuckDB.
    """
    source_root_norm = get_source_root(source_root)
    work_root_norm = get_work_root(work_root)
    allowed_root_norm = allowed_root
    if allowed_root_norm:
        allowed_root_norm = str(Path(allowed_root_norm).expanduser().resolve())
        work_root_norm = assert_within_allowed_root(work_root_norm, allowed_root_norm)

    lake = _guard_output_path(_lake_root(work_root_norm), source_root=source_root_norm, allowed_root=allowed_root_norm)
    pattern = os.path.join(lake, "canonico", "ano=*", "mes=*", "medicoes_canon_*.parquet")
    canon_files = sorted(glob.glob(pattern))
    wanted_months = {(int(a), int(m)) for a, m in (target_months or [])}

    month_parts: Dict[Tuple[int, int], List[pd.DataFrame]] = {}
    processed_files: List[str] = []
    rows_canon = 0
    rows_long = 0
    skipped_existing = 0

    for canon_file in canon_files:
        match = re.search(r"ano=(\d{4})[\\/]+mes=(\d{1,2})", canon_file)
        if not match:
            continue
        ano = int(match.group(1))
        mes = int(match.group(2))
        month_key = (ano, mes)
        if wanted_months and month_key not in wanted_months:
            continue

        long_file = os.path.join(lake, f"ano={ano}", f"mes={mes:02d}", f"medicoes_{ano}_{mes:02d}.parquet")
        if only_mismatched and os.path.exists(long_file) and os.path.getmtime(long_file) >= os.path.getmtime(canon_file):
            skipped_existing += 1
            continue

        df_canon = pq.read_table(canon_file).to_pandas()
        df_long = _canonical_to_long(df_canon, ano=ano, mes=mes)
        rows_canon += int(len(df_canon))
        rows_long += int(len(df_long))
        if not df_long.empty:
            month_parts.setdefault(month_key, []).append(df_long)
        processed_files.append(canon_file)

    outputs: List[str] = []
    for (ano, mes), parts in sorted(month_parts.items()):
        merged = pd.concat(parts, ignore_index=True, sort=False) if len(parts) > 1 else parts[0]
        output = escrever_parquet_particionado(
            work_root_norm,
            merged,
            source_root=source_root_norm,
            allowed_root=allowed_root_norm,
        )
        if output:
            outputs.extend([item for item in str(output).split(";") if item])

    if processed_files or outputs:
        construir_catalogo_duckdb(work_root_norm, source_root=source_root_norm, allowed_root=allowed_root_norm)

    return {
        "status": "ok",
        "work_root": work_root_norm,
        "canonical_files_found": len(canon_files),
        "canonical_files_processed": len(processed_files),
        "skipped_existing": skipped_existing,
        "months_rebuilt": [f"{ano}-{mes:02d}" for ano, mes in sorted(month_parts.keys())],
        "rows_canon": rows_canon,
        "rows_long": rows_long,
        "outputs": outputs,
        "duckdb_catalog_rebuilt": bool(processed_files or outputs),
    }


def indexar_tudo(
    *,
    source_root: Optional[str] = None,
    work_root: Optional[str] = None,
    allowed_root: Optional[str] = None,
) -> None:
    cfg = load_config(source_root_override=source_root, work_root_override=work_root)
    source_root_norm = get_source_root(source_root or cfg.source_root)
    work_root_norm = get_work_root(work_root or cfg.work_root)
    allowed_root_norm = allowed_root if allowed_root is not None else cfg.allowed_root
    if allowed_root_norm:
        allowed_root_norm = str(Path(allowed_root_norm).expanduser().resolve())
        work_root_norm = assert_within_allowed_root(work_root_norm, allowed_root_norm)

    treinar_andys(work_root_norm, source_root_norm, allowed_root_norm)
    files = listar_arquivos_brutos(source_root_norm)
    if not files:
        print("[WARN] Nenhum arquivo encontrado no padrao esperado em:", source_root_norm)
        return

    manifest = _load_manifest(work_root_norm)
    manifest.setdefault("files", {})

    for fp in files:
        name = os.path.basename(fp)
        try:
            st = os.stat(fp)
        except PermissionError as exc:
            raise PermissionError(f"Permissao negada ao ler arquivo-fonte: {fp}") from exc
        except OSError as exc:
            raise OSError(f"Falha de I/O ao acessar arquivo-fonte: {fp}") from exc
        size = int(st.st_size)
        mtime = int(st.st_mtime)
        source_sha256 = _file_sha256(fp, source_root_norm)
        source_rel = os.path.relpath(fp, source_root_norm)

        print("\n" + "-" * 60)
        print("[FILE] Arquivo:", source_rel)
        print("[FILE] Tamanho:", size)

        key = f"{INGEST_FINGERPRINT_VERSION}:{size}:{mtime}:{source_sha256}"
        old = manifest["files"].get(source_rel)
        if old and old.get("fingerprint") == key:
            print("[OK] Ja indexado (sem mudancas): pulando.")
            continue

        t0 = time.time()
        try:
            df_canon, df_long = ler_para_canonico_e_long(fp)
        except Exception as exc:
            print(f"[WARN] Falha ao processar '{source_rel}': {exc}")
            manifest["files"][source_rel] = {
                "fingerprint": key,
                "ingest_fingerprint_version": INGEST_FINGERPRINT_VERSION,
                "source_path": fp,
                "source_size": size,
                "source_mtime": mtime,
                "source_sha256": source_sha256,
                "error": str(exc)[:300],
                "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            _save_manifest(work_root_norm, manifest, source_root=source_root_norm, allowed_root=allowed_root_norm)
            continue
        print("[OK] Linhas CANON:", len(df_canon))
        print("[OK] Linhas LONG:", len(df_long))

        out_parquet = escrever_parquet_particionado(
            work_root_norm,
            df_long,
            source_root=source_root_norm,
            allowed_root=allowed_root_norm,
        )
        ym = _parse_month_year(name)
        if ym is None and not df_long.empty:
            ym = (int(df_long["ano"].min()), int(df_long["mes"].min()))
        ym = ym or (0, 0)
        out_canon = escrever_parquet_canonico(
            work_root_norm,
            df_canon,
            ano=int(ym[0]),
            mes=int(ym[1]),
            source_root=source_root_norm,
            allowed_root=allowed_root_norm,
        )
        dt = time.time() - t0

        print("[OK] Parquet LONG:", out_parquet)
        print("[OK] Parquet CANON:", out_canon)
        print(f"[TIME] {dt:.1f}s")

        manifest["files"][source_rel] = {
            "fingerprint": key,
            "ingest_fingerprint_version": INGEST_FINGERPRINT_VERSION,
            "source_path": fp,
            "source_size": size,
            "source_mtime": mtime,
            "source_sha256": source_sha256,
            "rows_canon": int(len(df_canon)),
            "rows_long": int(len(df_long)),
            "parquet": out_parquet,
            "parquet_canon": out_canon,
            "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        _save_manifest(work_root_norm, manifest, source_root=source_root_norm, allowed_root=allowed_root_norm)

    construir_catalogo_duckdb(work_root_norm, source_root=source_root_norm, allowed_root=allowed_root_norm)
    print("\n[OK] Indexacao finalizada e catalogo DuckDB pronto.")


def query_recorte(
    work_root: str,
    equips: List[str],
    t0: str,
    t1: str,
    vars_: Optional[List[str]] = None,
    as_wide: bool = True,
) -> pd.DataFrame:
    db_path = _duckdb_path(work_root)
    con = duckdb.connect(db_path)

    equips_clean = [str(e).strip() for e in equips if str(e).strip()]
    if not equips_clean:
        return pd.DataFrame()

    clauses = [f"EQUIPAMENTO IN ({','.join(['?'] * len(equips_clean))})", "timestamp >= CAST(? AS TIMESTAMP)", "timestamp <= CAST(? AS TIMESTAMP)"]
    params: List[Any] = list(equips_clean) + [t0, t1]
    if vars_:
        v_clean = [str(v).strip() for v in vars_ if str(v).strip()]
        if v_clean:
            clauses.append(f"var IN ({','.join(['?'] * len(v_clean))})")
            params.extend(v_clean)

    q = f"""
        SELECT
            timestamp, SE, BAY, EQUIPAMENTO, TERMINAL, ponto_id,
            equip_id, var, classe, valor
        FROM medicoes
        WHERE {' AND '.join(clauses)}
        ORDER BY timestamp ASC;
    """

    df = con.execute(q, params).df()
    con.close()

    if not as_wide or df.empty:
        return df

    wide = (
        df.pivot_table(
            index=["timestamp", "SE", "BAY", "EQUIPAMENTO", "TERMINAL", "ponto_id"],
            columns="var",
            values="valor",
            aggfunc="last",
        )
        .reset_index()
    )
    return wide


if __name__ == "__main__":
    indexar_tudo()
