from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_threads import AndyThread, AndyThreadReference, ThreadEntityType, ThreadKind, ThreadParticipant
from andy_threads.context import context_from_query_filters
from andy_threads.responsibility import route_thread, validate_thread_responsibility


def main() -> int:
    ref = context_from_query_filters(
        {
            "anos_sel": [2026],
            "meses_sel": [1],
            "se_sel": ["SE1"],
            "bay_sel": ["AL1"],
            "equipamento_sel": ["EQ1"],
            "terminal_sel": ["T1"],
            "vars_sel": ["MW"],
        },
        {"lote_id": "synthetic_lote_threads_001", "dataset_version": "synthetic.v1"},
    )
    assert isinstance(ref, AndyThreadReference)
    assert ref.entity_type in {ThreadEntityType.VARIABLE, ThreadEntityType.MEASUREMENT_POINT}
    actor = ThreadParticipant("engineer.synthetic", "Engineer Synthetic", "ENGINEERING")
    thread = AndyThread(
        thread_id="thread-domain-check",
        title="Synthetic power inversion review",
        kind=ThreadKind.POWER_INVERSION,
        reference=ref,
        created_by=actor,
        owner_sector="ENGINEERING",
    )
    routing = route_thread(thread.kind, thread.reference)
    failures = validate_thread_responsibility(thread)
    blocking = [item for item in failures if not item.startswith("missing_context:")]
    if blocking:
        raise AssertionError(blocking)
    print("ANDY Threads domain: passed")
    print(f"owner_sector={routing.owner_sector.value}")
    print(f"reference_entity={ref.entity_type.value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
