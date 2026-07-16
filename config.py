from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DEFAULT_WORK_ROOT = r"C:\Users\G05835236\Documents\Dados2025"
DEFAULT_SOURCE_ROOT = r"\\sfspoa03.ceee.local\DivEng\ELIPSE"
PROJECT_DIRNAME = "ANDYS_LAKE"
DUCKDB_FILENAME = "andys.duckdb"
DEFAULT_EXPORT_DIRNAME = "ANDYS_EXPORTS"

# Export auditor defaults
EXCEL_MAX_ROWS = 1_048_576
EXCEL_SAFE_HEADROOM = 0.95
XLSX_MAX_TIMESTAMPS_DEFAULT = 100_000
PERFORMANCE_WARN_ROWS = 2_000_000
FILESIZE_WARN_MB = 150
TIME_SUGGESTION_BUCKETS = (
    (365, "1D"),
    (180, "6H"),
    (30, "1H"),
    (7, "15min"),
)


def _to_bool(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _normalize_source_root(raw: str) -> str:
    """
    Normaliza apenas em memoria. Exemplo: '\\\\server\\share\\ELIPSE.' -> '\\\\server\\share\\ELIPSE'
    """
    text = str(raw or "").strip()
    if not text:
        return text
    return text.rstrip(" ./\\")


def _real(path: str) -> Path:
    return Path(path).expanduser().resolve()


def is_subpath(path: str, root: str) -> bool:
    p = _real(path)
    r = _real(root)
    return p == r or r in p.parents


def safe_join_root(root: str, path: str) -> str:
    root_resolved = _real(root)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root_resolved / candidate
    resolved = candidate.expanduser().resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ValueError("Path fora da raiz permitida.")
    return str(resolved)


def assert_within_allowed_root(path: str, allowed_root: Optional[str]) -> str:
    if not allowed_root:
        return str(_real(path))
    resolved = safe_join_root(allowed_root, path)
    return str(_real(resolved))


def assert_readonly_source(path: str, source_root: str, mode: str = "r") -> None:
    normalized_mode = (mode or "").lower()
    writes = any(token in normalized_mode for token in {"w", "a", "x", "+"})
    if writes and is_subpath(path, source_root):
        raise PermissionError("Operacao de escrita bloqueada: caminho dentro de ANDYS_SOURCE_ROOT (somente leitura).")


def get_source_root(source_root: str) -> str:
    normalized = _normalize_source_root(source_root)
    if not normalized:
        raise ValueError("ANDYS_SOURCE_ROOT nao pode ser vazio.")
    p = Path(normalized).expanduser()
    if not p.is_absolute():
        raise ValueError("ANDYS_SOURCE_ROOT deve ser absoluto.")
    return str(p.resolve())


def get_work_root(work_root: str) -> str:
    p = Path(work_root).expanduser()
    if not p.is_absolute():
        raise ValueError("ANDYS_WORK_ROOT deve ser absoluto.")
    return str(p.resolve())


def get_default_work_root() -> str:
    return get_work_root(os.environ.get("ANDYS_WORK_ROOT") or DEFAULT_WORK_ROOT)


def get_lake_root(work_root: str) -> str:
    return str(Path(get_work_root(work_root)) / PROJECT_DIRNAME)


def _expand_path(raw: str) -> Path:
    return Path(os.path.expandvars(str(raw))).expanduser()


def resolve_db_path(
    *,
    work_root: str,
    lake_root: Optional[str] = None,
    db_path_override: Optional[str] = None,
    allowed_root: Optional[str] = None,
    source_root: Optional[str] = None,
) -> str:
    lake_root_resolved = lake_root or get_lake_root(work_root)
    raw = db_path_override or os.environ.get("ANDYS_DB_PATH")
    if raw:
        candidate = _expand_path(raw)
        if not candidate.is_absolute():
            if allowed_root:
                candidate = Path(safe_join_root(allowed_root, str(candidate)))
            else:
                candidate = Path(os.path.abspath(str(candidate)))
    else:
        candidate = Path(lake_root_resolved) / DUCKDB_FILENAME

    resolved = candidate.resolve()
    if resolved.suffix.lower() != ".duckdb":
        raise ValueError("ANDYS_DB_PATH deve apontar para arquivo .duckdb.")

    db_path = str(resolved)
    if allowed_root:
        db_path = assert_within_allowed_root(db_path, allowed_root)
    if source_root and is_subpath(db_path, source_root):
        raise ValueError("ANDYS_DB_PATH nao pode apontar para ANDYS_SOURCE_ROOT.")
    return db_path


def get_db_path(work_root: str, db_path_override: Optional[str] = None) -> str:
    return resolve_db_path(work_root=work_root, db_path_override=db_path_override)


def ensure_db_exists(db_path: str, *, lake_root: Optional[str] = None) -> None:
    p = Path(db_path)
    if p.exists() and p.is_file():
        return
    where = str(p.resolve())
    if lake_root:
        raise FileNotFoundError(
            f"DuckDB nao encontrado em '{where}'. Rode andys_indexer.py para gerar '{Path(lake_root) / DUCKDB_FILENAME}' ou ajuste ANDYS_DB_PATH."
        )
    raise FileNotFoundError(
        f"DuckDB nao encontrado em '{where}'. Rode andys_indexer.py ou ajuste ANDYS_DB_PATH."
    )


def detect_db_paths_in_lake(
    lake_root: str,
    *,
    allowed_root: Optional[str] = None,
    filename: str = DUCKDB_FILENAME,
) -> list[str]:
    lake = Path(lake_root).resolve()
    if not lake.exists() or not lake.is_dir():
        return []
    if allowed_root and not is_subpath(str(lake), allowed_root):
        return []
    out: list[str] = []
    for hit in lake.rglob(filename):
        if not hit.is_file():
            continue
        hit_s = str(hit.resolve())
        if allowed_root and not is_subpath(hit_s, allowed_root):
            continue
        out.append(hit_s)
    return sorted(set(out))


def get_export_dir(work_root: str, export_dir_override: Optional[str] = None) -> str:
    if export_dir_override:
        return str(Path(export_dir_override).expanduser().resolve())
    return str(Path(get_work_root(work_root)) / DEFAULT_EXPORT_DIRNAME)


@dataclass(frozen=True)
class AppConfig:
    env: str
    is_prod: bool
    source_root: str
    work_root: str
    lake_root: str
    db_path: str
    export_dir: str
    allowed_root: Optional[str]
    log_level: str
    audit_log_path: Optional[str]
    role_env: str
    user_env: str
    auth_role_header: str
    auth_user_header: str
    admin_diag_enabled: bool

    def validate_paths(self) -> None:
        source = Path(self.source_root)
        if not source.exists():
            raise FileNotFoundError(f"ANDYS_SOURCE_ROOT indisponivel: {self.source_root}")
        if not source.is_dir():
            raise ValueError("ANDYS_SOURCE_ROOT deve apontar para um diretorio.")

        if self.allowed_root:
            for p, label in [
                (self.work_root, "ANDYS_WORK_ROOT"),
                (self.lake_root, "LAKE_ROOT"),
                (self.db_path, "ANDYS_DB_PATH"),
                (self.export_dir, "ANDYS_EXPORT_DIR"),
            ]:
                if not is_subpath(p, self.allowed_root):
                    raise ValueError(f"{label} fora de ANDYS_ALLOWED_ROOT.")
            if self.audit_log_path and not is_subpath(self.audit_log_path, self.allowed_root):
                raise ValueError("ANDYS_AUDIT_LOG_PATH fora de ANDYS_ALLOWED_ROOT.")

        # Guardrail de integridade: nada de saida apontando para source root.
        for p, label in [
            (self.work_root, "ANDYS_WORK_ROOT"),
            (self.lake_root, "LAKE_ROOT"),
            (self.db_path, "ANDYS_DB_PATH"),
            (self.export_dir, "ANDYS_EXPORT_DIR"),
        ]:
            if is_subpath(p, self.source_root):
                raise ValueError(f"{label} nao pode apontar para ANDYS_SOURCE_ROOT.")
        if self.audit_log_path and is_subpath(self.audit_log_path, self.source_root):
            raise ValueError("ANDYS_AUDIT_LOG_PATH nao pode apontar para ANDYS_SOURCE_ROOT.")

    def validate(self) -> None:
        if self.env not in {"dev", "prod"}:
            raise ValueError("ANDYS_ENV deve ser 'dev' ou 'prod'.")
        if self.is_prod:
            if not self.allowed_root:
                raise ValueError("ANDYS_ALLOWED_ROOT e obrigatorio em producao.")
            if "ANDYS_SOURCE_ROOT" not in os.environ:
                raise ValueError("ANDYS_SOURCE_ROOT e obrigatorio em producao.")
        self.validate_paths()


def load_config(
    *,
    source_root_override: Optional[str] = None,
    work_root_override: Optional[str] = None,
    db_path_override: Optional[str] = None,
    export_dir_override: Optional[str] = None,
) -> AppConfig:
    env = str(os.environ.get("ANDYS_ENV", "dev")).strip().lower() or "dev"
    is_prod = env == "prod"

    source_root_raw = source_root_override or os.environ.get("ANDYS_SOURCE_ROOT") or DEFAULT_SOURCE_ROOT
    work_root_raw = work_root_override or os.environ.get("ANDYS_WORK_ROOT") or DEFAULT_WORK_ROOT

    source_root = get_source_root(source_root_raw)
    work_root = get_work_root(work_root_raw)
    lake_root = get_lake_root(work_root)
    allowed_root = os.environ.get("ANDYS_ALLOWED_ROOT")
    if allowed_root:
        allowed_root = str(Path(allowed_root).expanduser().resolve())
        work_root = assert_within_allowed_root(work_root, allowed_root)
        lake_root = assert_within_allowed_root(lake_root, allowed_root)
    db_path = resolve_db_path(
        work_root=work_root,
        lake_root=lake_root,
        db_path_override=db_path_override or os.environ.get("ANDYS_DB_PATH"),
        allowed_root=allowed_root,
        source_root=source_root,
    )
    export_dir = get_export_dir(work_root, export_dir_override or os.environ.get("ANDYS_EXPORT_DIR"))

    if allowed_root:
        db_path = assert_within_allowed_root(db_path, allowed_root)
        export_dir = assert_within_allowed_root(export_dir, allowed_root)

    audit_log_path = os.environ.get("ANDYS_AUDIT_LOG_PATH")
    if audit_log_path:
        audit_log_path = str(Path(audit_log_path).expanduser().resolve())
        if allowed_root:
            audit_log_path = assert_within_allowed_root(audit_log_path, allowed_root)

    cfg = AppConfig(
        env=env,
        is_prod=is_prod,
        source_root=source_root,
        work_root=work_root,
        lake_root=lake_root,
        db_path=db_path,
        export_dir=export_dir,
        allowed_root=allowed_root,
        log_level=str(os.environ.get("ANDYS_LOG_LEVEL", "INFO")).strip().upper(),
        audit_log_path=audit_log_path,
        role_env=str(os.environ.get("ANDYS_ROLE", "admin")).strip().lower(),
        user_env=str(os.environ.get("ANDYS_USER", "anonymous")).strip(),
        auth_role_header=str(os.environ.get("ANDYS_AUTH_ROLE_HEADER", "X-ANDYS-ROLE")).strip(),
        auth_user_header=str(os.environ.get("ANDYS_AUTH_USER_HEADER", "X-ANDYS-USER")).strip(),
        admin_diag_enabled=_to_bool(os.environ.get("ANDYS_ADMIN_DIAG", "0")),
    )
    cfg.validate()
    return cfg
