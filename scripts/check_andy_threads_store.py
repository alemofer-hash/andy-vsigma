from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_threads import AndyThread, DecisionRecord, DecisionType, ThreadKind, ThreadMessage, ThreadParticipant, ThreadStatus
from andy_threads.context import context_from_query_filters
from andy_threads.store import ThreadStore


def main() -> int:
    target = ROOT / ".validation_tmp" / "andy_threads_session" / "check_store" / "threads.sqlite"
    if target.exists():
        target.unlink()
    participant = ThreadParticipant("engineer.synthetic", "Engineer Synthetic", "ENGINEERING")
    ref = context_from_query_filters(
        {"se_sel": ["SE1"], "bay_sel": ["AL1"], "equipamento_sel": ["EQ1"], "terminal_sel": ["T1"]},
        {"lote_id": "synthetic_lote_threads_001", "dataset_version": "synthetic.v1"},
    )
    thread = AndyThread(
        thread_id="thread-store-check",
        title="Synthetic store check",
        kind=ThreadKind.TERMINAL_MAPPING,
        reference=ref,
        created_by=participant,
        owner_sector="CADASTRE_ASSETS",
    )
    store = ThreadStore(target)
    store.create_thread(thread)
    store.add_message(ThreadMessage("msg-store-check", thread.thread_id, participant, "Synthetic review message."))
    store.change_status(thread.thread_id, ThreadStatus.TRIAGED, participant)
    store.create_decision(
        DecisionRecord(
            "decision-store-check",
            thread.thread_id,
            DecisionType.CATALOG_ERROR,
            "Synthetic catalog mapping requires correction at source.",
            participant,
            ("synthetic-evidence-1",),
        )
    )
    exported_json = store.export_thread(thread.thread_id, "json")
    exported_md = store.export_thread(thread.thread_id, "md")
    if not isinstance(exported_json, dict) or "ANDY Threads MVP local" not in exported_md:
        raise AssertionError("store_export_failed")
    print("ANDY Threads store: passed")
    print(f"sqlite_path={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
