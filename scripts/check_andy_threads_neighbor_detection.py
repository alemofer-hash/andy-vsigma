from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_MODULES = [
    "andy_threads.neighbor_detection.config",
    "andy_threads.neighbor_detection.models",
    "andy_threads.neighbor_detection.workbook_intake",
    "andy_threads.neighbor_detection.key_parser",
    "andy_threads.neighbor_detection.feeder_graph",
    "andy_threads.neighbor_detection.cadence",
    "andy_threads.neighbor_detection.synchronization",
    "andy_threads.neighbor_detection.preprocessing",
    "andy_threads.neighbor_detection.pair_state",
    "andy_threads.neighbor_detection.robust_step",
    "andy_threads.neighbor_detection.centroid_pair",
    "andy_threads.neighbor_detection.transfer_score",
    "andy_threads.neighbor_detection.common_mode",
    "andy_threads.neighbor_detection.neighborhood_fusion",
    "andy_threads.neighbor_detection.episodes",
    "andy_threads.neighbor_detection.upstream_reference",
    "andy_threads.neighbor_detection.occurrence_adapter",
    "andy_threads.neighbor_detection.human_review",
    "andy_threads.neighbor_detection.reporting",
    "andy_threads.neighbor_detection.runner",
]

REQUIRED_FILES = [
    "config/andy_threads_feeder_neighborhood.example.json",
    "docs/ANDY_THREADS_FEEDER_NEIGHBORHOOD_QUESTIONS.md",
    "scripts/run_andy_threads_neighbor_detection.py",
]


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    import_failures: list[str] = []
    for module in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:
            import_failures.append(f"{module}:{exc}")
    config_path = ROOT / "config/andy_threads_feeder_neighborhood.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    flag = importlib.import_module("andy_threads.neighbor_detection.config").is_neighbor_detection_enabled()
    failures = []
    if missing:
        failures.append("missing_files=" + ",".join(missing))
    if import_failures:
        failures.append("import_failures=" + "|".join(import_failures))
    if flag:
        failures.append("feature_flag_should_be_off_by_default")
    if config.get("substations", {}).get("MOS", {}).get("neighbor_pairs") != [["AL3", "AL4"]]:
        failures.append("mos_al3_al4_example_pair_missing")
    if failures:
        print("ANDY Threads neighbor detection readiness: failed")
        for failure in failures:
            print(failure)
        return 1
    print("ANDY Threads neighbor detection readiness: passed")
    print("feature_flag_default=false")
    print("detector_core=selected_current_feeder_pair")
    print("operational_confirmation=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
