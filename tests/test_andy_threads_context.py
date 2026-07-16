from __future__ import annotations

from andy_threads.context import build_query_signature, compute_filter_hash, context_from_query_filters


def test_context_from_query_filters_accepts_dict() -> None:
    ref = context_from_query_filters({"se_sel": ["SE1"], "bay_sel": ["AL1"]}, {"lote_id": "lote-1"})
    assert ref.se == "SE1"
    assert ref.bay_or_feeder == "AL1"
    assert ref.lote_id == "lote-1"


def test_hash_is_stable_and_changes_when_filter_changes() -> None:
    first = compute_filter_hash({"se": "SE1", "bay": "AL1"})
    same = compute_filter_hash({"bay": "AL1", "se": "SE1"})
    changed = compute_filter_hash({"se": "SE1", "bay": "AL2"})
    assert first == same
    assert first != changed


def test_query_signature_is_stable() -> None:
    assert build_query_signature({"se": "SE1"}) == build_query_signature({"se": "SE1"})


def test_context_does_not_store_dataframe_payload() -> None:
    ref = context_from_query_filters({"se": "SE1", "dataframe": object()})
    assert ref.filter_hash
