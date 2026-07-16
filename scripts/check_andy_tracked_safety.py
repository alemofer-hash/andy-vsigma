from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
JSON_REPORT = REPORT_DIR / "ANDY_TRACKED_SAFETY_REPORT.json"
MD_REPORT = REPORT_DIR / "ANDY_TRACKED_SAFETY_REPORT.md"

PROHIBITED = {
    "venv",
    "build_output",
    "installer_output",
    "update_output",
    "runtime_data",
    "duckdb_parquet_lake",
    "validation_data",
    "log",
    "cache",
    "archive",
    "secret_candidate",
    "unknown_risky",
}

SECRET_NAMES = {".env", "secrets", "secret", "credentials", "credential", "tokens", "token"}
SECRET_EXTS = {".pem", ".pfx", ".key", ".token"}
DATA_EXTS = {".duckdb", ".parquet", ".xlsx", ".xlsm", ".xls", ".csv", ".feather", ".orc"}
ARCHIVE_EXTS = {".zip", ".7z", ".tar", ".tgz", ".gz"}
INSTALLER_EXTS = {".exe", ".msi", ".cab"}
LOG_EXTS = {".log", ".jsonl"}
CACHE_EXTS = {".pyc", ".pyo"}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mb(size: int) -> float:
    return round(size / (1024 * 1024), 3)


def git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def split_z(output: str) -> list[str]:
    return [item for item in output.split("\0") if item]


def path_parts(relpath: str) -> list[str]:
    return [part.lower() for part in Path(relpath).parts]


def has_secret_name(parts: list[str], name: str, suffix: str) -> bool:
    if name.lower() in SECRET_NAMES:
        return True
    if suffix in SECRET_EXTS:
        return True
    return any(part in SECRET_NAMES for part in parts)


def classify(relpath: str) -> tuple[str, str]:
    path = Path(relpath)
    suffix = path.suffix.lower()
    parts = path_parts(relpath)
    name = path.name.lower()
    top = parts[0] if parts else ""
    joined = "/".join(parts)

    if has_secret_name(parts, name, suffix):
        return "secret_candidate", "path or extension indicates credential material"
    if top in {".venv", ".venv-1", ".venv-2"} or top.startswith(".venv-") or top == "venv":
        return "venv", "local Python virtual environment"
    if top == "build":
        return "build_output", "PyInstaller build output"
    if top == "dist":
        return "build_output", "packaged application output"
    if joined.startswith("artifacts/installer"):
        return "installer_output", "generated installer artifact area"
    if joined.startswith("artifacts/updates"):
        return "update_output", "generated update artifact area"
    if top == "artifacts":
        return "runtime_data", "generated artifacts/support/runtime capture area"
    if top in {".validation_tmp", "validation_reports"}:
        return "validation_data", "generated validation data"
    if joined.startswith("cyber_audit/reports") or joined.startswith("enterprise_release_gate/reports"):
        return "validation_data", "generated audit/release report data"
    if top == "reports":
        return "validation_data", "generated local reports"
    if top == "_archive" or suffix in ARCHIVE_EXTS:
        return "archive", "archive or backup-like file"
    if top == "__pycache__" or "__pycache__" in parts or top in {".pytest_cache", ".mypy_cache", ".ruff_cache"}:
        return "cache", "tool or Python cache"
    if "cache" in parts or suffix in CACHE_EXTS:
        return "cache", "cache directory or bytecode"
    if suffix in LOG_EXTS or "logs" in parts:
        return "log", "log or JSONL operational trace"
    if "fixtures" in parts:
        return "tests", "approved fixture/test area"
    if suffix in {".duckdb", ".parquet"} or "andys_lake" in parts:
        return "duckdb_parquet_lake", "DuckDB/Parquet lake or catalog candidate"
    if suffix in DATA_EXTS:
        return "runtime_data", "tabular/data file candidate"
    if suffix in INSTALLER_EXTS and top in {"artifacts", "dist", "build", "installer"}:
        return "installer_output", "generated executable/package candidate"
    if top == "docs" or suffix in {".md", ".rst"}:
        return "docs", "documentation"
    if top == "tests" or name.startswith("test_") or name.endswith("_test.py"):
        return "tests", "test source"
    if top in {"scripts", "tools", "prompts", "hermes_trace_v0_3_ntp_v1_1"}:
        return "tooling", "script/tooling/prompt area"
    if top in {"config", "configs"} or name in {".gitignore", ".gitattributes", "pytest.ini"} or suffix in {".ini", ".toml", ".yaml", ".yml"}:
        return "config", "configuration or policy file"
    if name in {"requirements.txt", "requirements-dev.txt", "requirements-validation.txt"}:
        return "config", "dependency manifest"
    if name == "andy_launcher.spec" or (top == "installer" and suffix == ".iss"):
        return "config", "packaging/installer source configuration"
    if suffix == ".py":
        return "source_code", "Python source code"
    if top in {"andy", "andy_core", "andy_boundary", "desktop_app", "db", "audit", "security", "source_guardian", "k_supervisor", "utils", "assets"}:
        return "source_code", "source package or source asset"
    return "unknown_risky", "no allow rule matched; review before baseline"


def record(path: str) -> dict[str, Any]:
    category, reason = classify(path)
    fs_path = ROOT / path
    size = 0
    exists = False
    try:
        exists = fs_path.exists()
        if fs_path.is_file():
            size = fs_path.stat().st_size
    except OSError:
        exists = False
    return {
        "path": path.replace("\\", "/"),
        "category": category,
        "extension": Path(path).suffix.lower(),
        "size_bytes": size,
        "size_mb": mb(size),
        "exists": exists,
        "reason": reason,
        "prohibited": category in PROHIBITED,
    }


def build_report() -> dict[str, Any]:
    tracked = split_z(git(["ls-files", "-z"]).stdout)
    records = [record(path) for path in tracked]
    blocked = [item for item in records if item["prohibited"]]
    counts = Counter(item["category"] for item in blocked)
    bytes_by_category: defaultdict[str, int] = defaultdict(int)
    for item in blocked:
        bytes_by_category[item["category"]] += int(item["size_bytes"])

    return {
        "status": "failed" if blocked else "passed",
        "expected_before_untrack": bool(blocked),
        "generated_utc": now_utc(),
        "root": "<ANDY_ROOT>",
        "safety_boundary": {
            "metadata_only": True,
            "reads_file_contents": False,
            "moves_or_deletes_files": False,
            "runs_git_rm": False,
        },
        "summary": {
            "tracked_total": len(records),
            "blocked_total": len(blocked),
            "blocked_by_category": dict(sorted(counts.items())),
            "blocked_mb_by_category": {key: mb(value) for key, value in sorted(bytes_by_category.items())},
        },
        "blocked_tracked": blocked,
    }


def write_reports(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    summary = report["summary"]

    lines = [
        "# ANDY Tracked Safety Report",
        "",
        f"Status: `{report['status']}`",
        f"Expected before approved untrack: `{report['expected_before_untrack']}`",
        f"Generated UTC: `{report['generated_utc']}`",
        "",
        "## Summary",
        "",
        f"- Tracked files: `{summary['tracked_total']}`",
        f"- Blocked tracked files: `{summary['blocked_total']}`",
        "",
        "## Blocked By Category",
        "",
        "| Category | Count | MB |",
        "|---|---:|---:|",
    ]
    for category, count in summary["blocked_by_category"].items():
        lines.append(f"| `{category}` | {count} | {summary['blocked_mb_by_category'].get(category, 0.0)} |")

    lines.extend(
        [
            "",
            "## Blocked Sample",
            "",
            "| Path | Category | Ext | MB | Reason |",
            "|---|---|---|---:|---|",
        ]
    )
    for item in report["blocked_tracked"][:500]:
        lines.append(f"| `{item['path']}` | `{item['category']}` | `{item['extension']}` | {item['size_mb']} | {item['reason']} |")
    if len(report["blocked_tracked"]) > 500:
        lines.append(f"| `_omitted_` |  |  |  | `{len(report['blocked_tracked']) - 500}` additional blocked rows omitted from Markdown |")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This check is expected to fail before the approved untrack plan is executed.",
            "- It reads only Git path metadata and filesystem stat metadata.",
            "- It does not delete, move or untrack files.",
            "",
        ]
    )
    MD_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    report = build_report()
    write_reports(report)
    print(f"ANDY tracked safety: {report['status']}")
    print(f"Tracked files: {report['summary']['tracked_total']}")
    print(f"Blocked tracked files: {report['summary']['blocked_total']}")
    print("Wrote reports/ANDY_TRACKED_SAFETY_REPORT.md")
    print("Wrote reports/ANDY_TRACKED_SAFETY_REPORT.json")
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
