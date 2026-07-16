from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from andy_bi.pilot_report import build_pilot_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the ANDY BI Web pilot report from a synthetic/publicable dataset.")
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "andy_bi_dataset"))
    parser.add_argument("--out", default=str(ROOT / "artifacts" / "andy_bi_pilot_report"))
    parser.add_argument("--title", default="ANDY BI Web Pilot")
    parser.add_argument("--allow-non-synthetic", action="store_true", help="Review-only override. Defaults to synthetic-only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_pilot_report(
        dataset_dir=args.dataset,
        out_dir=args.out,
        title=args.title,
        require_synthetic=not args.allow_non_synthetic,
    )
    print(f"status={result.status}")
    print(f"synthetic={result.synthetic}")
    print(f"out={result.out_dir}")
    print(f"html={result.html_path}")
    print(f"manifest={result.manifest_path}")
    print(f"validation_report={result.validation_report_path}")
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
