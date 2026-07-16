from __future__ import annotations

from andy_threads import AndyThread, AndyThreadReference, DecisionRecord, DecisionType, ThreadEntityType, ThreadKind, ThreadMessage, ThreadParticipant, ThreadStatus
from andy_threads.store import ThreadStore


def _thread() -> AndyThread:
    return AndyThread(
        "thread-store",
        "Store",
        ThreadKind.TERMINAL_MAPPING,
        AndyThreadReference(ThreadEntityType.TERMINAL, se="SE1", bay_or_feeder="AL1", equipamento="EQ1", terminal="T1"),
        ThreadParticipant("cadastre.synthetic", "Cadastre Synthetic", "CADASTRE_ASSETS"),
        owner_sector="CADASTRE_ASSETS",
    )


def test_store_initializes_and_roundtrips(tmp_path) -> None:
    store = ThreadStore(tmp_path / "threads.sqlite")
    thread = _thread()
    store.create_thread(thread)
    assert store.get_thread(thread.thread_id)["thread_id"] == thread.thread_id
    assert store.list_threads_by_reference(thread.reference)


def test_store_adds_message_status_decision_and_exports(tmp_path) -> None:
    store = ThreadStore(tmp_path / "threads.sqlite")
    thread = _thread()
    participant = thread.created_by
    store.create_thread(thread)
    store.add_message(ThreadMessage("msg-store", thread.thread_id, participant, "Synthetic message"))
    store.change_status(thread.thread_id, ThreadStatus.TRIAGED, participant)
    store.create_decision(
        DecisionRecord(
            "decision-store",
            thread.thread_id,
            DecisionType.CATALOG_ERROR,
            "Synthetic catalog correction required.",
            participant,
            ("synthetic-evidence",),
        )
    )
    exported = store.export_thread(thread.thread_id, "json")
    markdown = store.export_thread(thread.thread_id, "md")
    assert isinstance(exported, dict)
    assert "ANDY Threads MVP local" in markdown
    assert store.search_threads(status=ThreadStatus.TRIAGED)
