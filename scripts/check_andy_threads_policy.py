from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_threads import AndyThread, ThreadKind, ThreadParticipant
from andy_threads.context import context_from_query_filters
from andy_threads.policy import MockThreadUserContext, ThreadAccessRequest, ThreadAction, evaluate_thread_access


def main() -> int:
    ref = context_from_query_filters(
        {"se_sel": ["SE1"], "bay_sel": ["AL1"], "vars_sel": ["MW"]},
        {"lote_id": "synthetic_lote_threads_001", "dataset_version": "synthetic.v1"},
    )
    thread = AndyThread(
        thread_id="thread-policy-check",
        title="Synthetic policy check",
        kind=ThreadKind.POWER_INVERSION,
        reference=ref,
        created_by=ThreadParticipant("engineer.synthetic", "Engineer Synthetic", "ENGINEERING"),
        owner_sector="ENGINEERING",
    )
    anonymous = evaluate_thread_access(ThreadAccessRequest(ThreadAction.READ_THREAD, None, thread=thread))
    if anonymous.allowed:
        raise AssertionError("anonymous_user_should_be_denied")
    owner = MockThreadUserContext("engineer.synthetic", "ENGINEERING", substations=("SE1",), feeders=("AL1",))
    owner_decision = evaluate_thread_access(ThreadAccessRequest(ThreadAction.CREATE_THREAD, owner, thread=thread))
    if not owner_decision.allowed:
        raise AssertionError(owner_decision.reason)
    operation = MockThreadUserContext("operator.synthetic", "OPERATION", substations=("SE1",), feeders=("AL1",))
    comment_decision = evaluate_thread_access(ThreadAccessRequest(ThreadAction.COMMENT, operation, thread=thread))
    if not comment_decision.allowed:
        raise AssertionError(comment_decision.reason)
    export_denied = evaluate_thread_access(ThreadAccessRequest(ThreadAction.EXPORT_THREAD, owner, thread=thread))
    if export_denied.allowed:
        raise AssertionError("export_without_permission_should_be_denied")
    print("ANDY Threads policy: passed")
    print("deny_by_default=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
