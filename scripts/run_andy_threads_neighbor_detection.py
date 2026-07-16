from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_threads.neighbor_detection.config import load_neighborhood_config, with_cli_pair
from andy_threads.neighbor_detection.runner import run_neighbor_detection


def parse_hours(value: str | None, default: tuple[float, ...]) -> tuple[float, ...]:
    if not value:
        return default
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ANDY Threads neighbor feeder IB detection lab.")
    parser.add_argument("--input", action="append", default=[], help="Input XLSX file. Can be provided multiple times.")
    parser.add_argument("--neighborhood-config", default="config/andy_threads_feeder_neighborhood.example.json")
    parser.add_argument("--blind-run", action="store_true")
    parser.add_argument("--output", default=".validation_tmp/andy_threads_neighbor_detection")
    parser.add_argument("--generate-ui-runtime", action="store_true")
    parser.add_argument("--generate-thread-occurrences", action="store_true")
    parser.add_argument("--pair", action="append", default=[], help="Declared pair in format SE:AL3:AL4.")
    parser.add_argument("--all-pairs-exploratory", action="store_true")
    parser.add_argument("--pre-hours")
    parser.add_argument("--post-hours")
    parser.add_argument("--min-persistence", type=int)
    parser.add_argument("--max-offset-intervals", type=int)
    parser.add_argument("--disable-centroid", action="store_true", help="Accepted for CLI compatibility; centroid remains reported as disabled residue.")
    parser.add_argument("--disable-upstream", action="store_true", help="Accepted for CLI compatibility; upstream remains reported as disabled residue.")
    parser.add_argument("--profile-only", action="store_true")
    args = parser.parse_args()

    if not args.input:
        parser.error("--input is required")

    config = load_neighborhood_config(args.neighborhood_config)
    if args.pair:
        config = with_cli_pair(config, args.pair)
    if args.pre_hours or args.post_hours or args.min_persistence or args.max_offset_intervals:
        from andy_threads.neighbor_detection.config import NeighborDetectionConfig

        config = NeighborDetectionConfig(
            substations=config.substations,
            pre_windows_hours=parse_hours(args.pre_hours, config.pre_windows_hours),
            post_windows_hours=parse_hours(args.post_hours, config.post_windows_hours),
            min_persistence_samples=args.min_persistence or config.min_persistence_samples,
            max_pair_time_offset_intervals=args.max_offset_intervals or config.max_pair_time_offset_intervals,
            robust_z_threshold=config.robust_z_threshold,
            min_balance_for_transfer=config.min_balance_for_transfer,
            min_quality_score=config.min_quality_score,
            min_common_coverage=config.min_common_coverage,
            paper_reproduction_mode=config.paper_reproduction_mode,
            paper_window_samples=config.paper_window_samples,
            paper_overlap=config.paper_overlap,
        )

    result = run_neighbor_detection(
        inputs=[Path(item) for item in args.input],
        config=config,
        output_root=Path(args.output),
        all_pairs_exploratory=args.all_pairs_exploratory,
        blind_run=args.blind_run,
        generate_thread_occurrences=args.generate_thread_occurrences,
        generate_ui_runtime=args.generate_ui_runtime,
        profile_only=args.profile_only,
    )
    print("ANDY Threads neighbor detection: completed")
    print(f"run_dir={result.run_dir}")
    print(f"inputs={len(result.manifests)}")
    print(f"candidates={len(result.candidates)}")
    print(f"episodes={result.episode_count}")
    if result.warnings:
        print("warnings=" + ";".join(result.warnings))
    print("ib_only=true")
    print("training_use=false")
    print("operational_confirmation=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
