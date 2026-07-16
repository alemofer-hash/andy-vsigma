from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "andy_threads/models.py",
    "andy_threads/references.py",
    "andy_threads/sector_lens.py",
    "andy_threads/responsibility.py",
    "andy_threads/policy.py",
    "andy_threads/store.py",
    "andy_threads/audit.py",
    "andy_threads/context.py",
    "andy_threads/serialization.py",
    "config/andy_threads_policy.example.json",
    "config/andy_threads_sector_matrix.example.json",
    "docs/ANDY_THREADS_PRODUCT_CHARTER.md",
    "docs/ANDY_THREADS_SECTOR_DISCOVERY.md",
    "docs/ANDY_THREADS_RESPONSIBILITY_MATRIX.md",
    "docs/ANDY_THREADS_DATA_CONTRACT.md",
    "docs/ANDY_THREADS_ACCESS_POLICY.md",
    "docs/ANDY_THREADS_MVP_ROADMAP.md",
    "docs/ANDY_THREADS_SESSION_01_REPORT.md",
]


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        print("ANDY Threads readiness: failed")
        print("missing=" + ",".join(missing))
        return 1
    for script in ("check_andy_threads_domain.py", "check_andy_threads_policy.py", "check_andy_threads_store.py"):
        subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, check=True)
    print("ANDY Threads readiness: passed")
    print("real_provider_enabled=false")
    print("store_scope=.validation_tmp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
