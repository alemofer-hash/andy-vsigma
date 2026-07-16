from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from andy_bi.dataset_builder import build_andy_bi_dataset  # noqa: E402
from andy_bi.parity import compare_summaries, summarize_dataset, write_parity_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check ANDY BI dataset parity summaries.")
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "andy_bi_dataset_parity_sample"))
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--out", default=str(ROOT / "artifacts" / "andy_bi_parity_report.md"))
    parser.add_argument("--json-out", default=str(ROOT / "reports" / "ANDY_BI_PARITY.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset = Path(args.dataset)
    if not dataset.exists():
        build_andy_bi_dataset(out_dir=dataset, fmt="both", synthetic=True, lote_id="andy_bi_parity_demo")
    baseline = Path(args.baseline) if args.baseline else dataset
    left = summarize_dataset(dataset)
    right = summarize_dataset(baseline)
    findings = compare_summaries(left, right)
    report_path = write_parity_report(args.out, findings, str(dataset), str(baseline))
    json_report = Path(args.json_out)
    json_report.parent.mkdir(parents=True, exist_ok=True)
    json_report.write_text(
        json.dumps(
            {
                "status": "passed" if not findings else "blocked",
                "dataset": str(dataset),
                "baseline": str(baseline),
                "findings": [item.as_dict() for item in findings],
                "report": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"status={'passed' if not findings else 'blocked'}")
    print(f"report={report_path}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
