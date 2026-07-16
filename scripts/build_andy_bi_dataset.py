from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from andy_bi.dataset_builder import build_andy_bi_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a governed local ANDY BI dataset package.")
    parser.add_argument("--format", choices=("parquet", "csv", "both"), default="parquet")
    parser.add_argument("--out", default=str(ROOT / "artifacts" / "andy_bi_dataset"))
    parser.add_argument("--lote-id", default="andy_bi_demo_lote")
    parser.add_argument("--source-db", default=None, help="Optional local DuckDB path. Requires --allow-local-data.")
    parser.add_argument("--synthetic", action="store_true", help="Force synthetic/demo data.")
    parser.add_argument("--allow-local-data", action="store_true", help="Explicitly allow local DuckDB extraction review path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_andy_bi_dataset(
        out_dir=args.out,
        fmt=args.format,
        source_db=args.source_db,
        lote_id=args.lote_id,
        synthetic=True if args.synthetic else None,
        allow_local_data=args.allow_local_data,
    )
    print(f"status={result.validation_status}")
    print(f"synthetic={result.synthetic}")
    print(f"out={result.out_dir}")
    print(f"manifest={result.manifest_path}")
    print(f"schema={result.schema_path}")
    print(f"validation_report={result.validation_report_path}")
    return 0 if result.validation_status == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
