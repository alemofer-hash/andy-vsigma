from __future__ import annotations

from andy_threads.references import (
    AndyThreadReference,
    ThreadEntityType,
    hash_filter_payload,
    reference_from_query_filters,
    reference_public_summary,
    validate_reference,
)


def test_minimal_reference_is_valid() -> None:
    ref = AndyThreadReference(ThreadEntityType.SUBSTATION, se="SE1")
    assert validate_reference(ref) == []


def test_reference_without_identifier_fails() -> None:
    ref = AndyThreadReference(ThreadEntityType.SUBSTATION)
    assert "technical_identifier_required" in validate_reference(ref)


def test_filter_hash_is_stable() -> None:
    payload_a = {"se_sel": ["SE1"], "bay_sel": ["AL1"]}
    payload_b = {"bay_sel": ["AL1"], "se_sel": ["SE1"]}
    assert hash_filter_payload(payload_a) == hash_filter_payload(payload_b)


def test_public_summary_omits_empty_fields() -> None:
    ref = AndyThreadReference(ThreadEntityType.VARIABLE, se="SE1", variavel="MW")
    summary = reference_public_summary(ref)
    assert summary["entity_type"] == "VARIABLE"
    assert "terminal" not in summary


def test_reference_from_query_filters_maps_fields() -> None:
    ref = reference_from_query_filters(
        {"se_sel": ["SE1"], "bay_sel": ["AL1"], "vars_sel": ["MW"], "source_cadence_sel": ["15min"]},
        {"dataset_version": "synthetic.v1"},
    )
    assert ref.se == "SE1"
    assert ref.bay_or_feeder == "AL1"
    assert ref.variavel == "MW"
    assert ref.source_cadence == "15min"
    assert ref.filter_hash
