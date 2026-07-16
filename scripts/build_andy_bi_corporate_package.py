from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from andy_bi.export_package import build_corporate_package  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the local ANDY BI package for TI/BI review.")
    parser.add_argument("--out", default=str(ROOT / "artifacts" / "andy_bi_corporate_package"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = build_corporate_package(args.out)
    print(f"status=passed")
    print(f"package={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
