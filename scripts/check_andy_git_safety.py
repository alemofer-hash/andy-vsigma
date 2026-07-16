from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
JSON_REPORT = REPORT_DIR / "ANDY_GIT_SAFETY_REPORT.json"
MD_REPORT = REPORT_DIR / "ANDY_GIT_SAFETY_REPORT.md"

SECRET_NAMES = {
    ".env",
    "secrets",
    "secret",
    "credentials",
    "credential",
    "tokens",
    "token",
}
SECRET_EXTS = {".pem", ".pfx", ".key", ".token"}
DATA_EXTS = {".duckdb", ".parquet", ".xlsx", ".xlsm", ".xls", ".csv", ".feather", ".orc"}
ARCHIVE_EXTS = {".zip", ".7z", ".tar", ".tgz", ".gz"}
INSTALLER_EXTS = {".exe", ".msi", ".cab"}
LOG_EXTS = {".log", ".jsonl"}
CACHE_EXTS = {".pyc", ".pyo"}
DANGEROUS_CATEGORIES = {
    "secret_candidate",
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
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
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
    lowered_name = name.lower()
    if lowered_name in SECRET_NAMES:
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
    if suffix in {".duckdb", ".parquet"} or "andys_lake" in parts:
        return "duckdb_parquet_lake", "DuckDB/Parquet lake or catalog candidate"
    if suffix in DATA_EXTS:
        return "runtime_data", "tabular/data file candidate"
    if suffix in INSTALLER_EXTS and top in {"artifacts", "dist", "build"}:
        return "installer_output", "generated executable/package candidate"
    if top in {"docs"} or suffix in {".md", ".rst"}:
        return "docs", "documentation"
    if top == "tests" or name.startswith("test_") or name.endswith("_test.py"):
        return "tests", "test source or fixture area"
    if top in {"scripts", "tools", "prompts", "hermes_trace_v0_3_ntp_v1_1"}:
        return "tooling", "script/tooling/prompt area"
    if top in {"config", "configs"} or name in {".gitignore", ".gitattributes", "pytest.ini"} or suffix in {".ini", ".toml", ".yaml", ".yml"}:
        return "config", "configuration or policy file"
    if name in {"requirements.txt", "requirements-dev.txt", "requirements-validation.txt"}:
        return "config", "dependency manifest"
    if name == "andy_launcher.spec" or top == "installer":
        return "config", "packaging/installer source configuration"
    if suffix == ".py":
        return "source_code", "Python source code"
    return "unknown", "no conservative rule matched"


def record(path: str, source: str) -> dict[str, Any]:
    category, reason = classify(path)
    filesystem_path = ROOT / path
    size = 0
    exists = filesystem_path.exists()
    if exists and filesystem_path.is_file():
        try:
            size = filesystem_path.stat().st_size
        except OSError:
            size = 0
    return {
        "path": path.replace("\\", "/"),
        "source": source,
        "category": category,
        "dangerous": category in DANGEROUS_CATEGORIES,
        "extension": Path(path).suffix.lower(),
        "exists": exists,
        "size_bytes": size,
        "reason": reason,
    }


def staged_paths() -> list[str]:
    result = git(["diff", "--cached", "--name-only", "-z"])
    return split_z(result.stdout)


def tracked_paths() -> list[str]:
    result = git(["ls-files", "-z"])
    return split_z(result.stdout)


def status_short() -> tuple[list[str], str]:
    result = git(["status", "--short"], check=False)
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        candidate = line[3:] if len(line) > 3 else line.strip()
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        paths.append(candidate.strip('"'))
    return paths, result.stderr.strip()


def build_report() -> dict[str, Any]:
    staged = [record(path, "staged") for path in staged_paths()]
    tracked = [record(path, "tracked") for path in tracked_paths()]
    status_paths, status_stderr = status_short()
    status_candidates = [record(path, "status") for path in status_paths]

    staged_danger = [item for item in staged if item["dangerous"]]
    tracked_danger = [item for item in tracked if item["dangerous"]]
    status_danger = [item for item in status_candidates if item["dangerous"]]

    summary = {
        "staged_count": len(staged),
        "staged_danger_count": len(staged_danger),
        "tracked_count": len(tracked),
        "tracked_danger_count": len(tracked_danger),
        "status_candidate_count": len(status_candidates),
        "status_danger_count": len(status_danger),
        "staged_by_category": dict(Counter(item["category"] for item in staged)),
        "tracked_danger_by_category": dict(Counter(item["category"] for item in tracked_danger)),
        "status_danger_by_category": dict(Counter(item["category"] for item in status_danger)),
    }

    return {
        "status": "failed" if staged_danger else "passed",
        "generated_utc": now_utc(),
        "root": "<ANDY_ROOT>",
        "safety_boundary": {
            "metadata_only": True,
            "reads_file_contents": False,
            "prints_full_user_paths": False,
            "runs_app_build_installer_update": False,
        },
        "summary": summary,
        "blocking_staged_danger": staged_danger,
        "tracked_danger_sample": tracked_danger[:500],
        "status_danger_sample": status_danger[:500],
        "git_status_stderr": status_stderr,
    }


def write_reports(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    summary = report["summary"]
    lines: list[str] = [
        "# ANDY Git Safety Report",
        "",
        f"Status: `{report['status']}`",
        f"Generated UTC: `{report['generated_utc']}`",
        "Root: `<ANDY_ROOT>`",
        "",
        "## Safety Boundary",
        "",
        "- Metadata-only: `yes`",
        "- File contents read: `no`",
        "- Full user paths printed: `no`",
        "- App/build/installer/update executed: `no`",
        "",
        "## Summary",
        "",
        f"- Staged files: `{summary['staged_count']}`",
        f"- Dangerous staged files: `{summary['staged_danger_count']}`",
        f"- Tracked files: `{summary['tracked_count']}`",
        f"- Dangerous tracked files: `{summary['tracked_danger_count']}`",
        f"- Git status paths inspected: `{summary['status_candidate_count']}`",
        f"- Dangerous status paths: `{summary['status_danger_count']}`",
        "",
        "## Blocking Staged Danger",
        "",
    ]

    if report["blocking_staged_danger"]:
        lines.extend(["| Path | Category | Reason |", "|---|---|---|"])
        for item in report["blocking_staged_danger"]:
            lines.append(f"| `{item['path']}` | `{item['category']}` | {item['reason']} |")
    else:
        lines.append("- None detected.")

    lines.extend(["", "## Tracked Dangerous Sample", ""])
    if report["tracked_danger_sample"]:
        lines.extend(["| Path | Category | Reason |", "|---|---|---|"])
        for item in report["tracked_danger_sample"][:200]:
            lines.append(f"| `{item['path']}` | `{item['category']}` | {item['reason']} |")
    else:
        lines.append("- None detected.")

    lines.extend(["", "## Current Status Dangerous Sample", ""])
    if report["status_danger_sample"]:
        lines.extend(["| Path | Category | Reason |", "|---|---|---|"])
        for item in report["status_danger_sample"][:200]:
            lines.append(f"| `{item['path']}` | `{item['category']}` | {item['reason']} |")
    else:
        lines.append("- None detected.")

    if report["git_status_stderr"]:
        lines.extend(["", "## Git Status Warnings", ""])
        for line in report["git_status_stderr"].splitlines()[:100]:
            lines.append(f"- `{line}`")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This gate fails only for dangerous staged files.",
            "- Tracked dangerous files are reported as migration/sanitize risks, not automatically removed.",
            "- Do not use `git add .`; stage explicit reviewed files only.",
            "",
        ]
    )
    MD_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    report = build_report()
    write_reports(report)
    print(f"ANDY git safety: {report['status']}")
    print(f"Staged files: {report['summary']['staged_count']}")
    print(f"Dangerous staged files: {report['summary']['staged_danger_count']}")
    print("Wrote reports/ANDY_GIT_SAFETY_REPORT.md")
    print("Wrote reports/ANDY_GIT_SAFETY_REPORT.json")
    return 1 if report["blocking_staged_danger"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
