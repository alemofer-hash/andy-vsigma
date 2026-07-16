from __future__ import annotations

import inspect

from andys_indexer import rebuild_long_lake_from_canonical


def test_rebuild_long_lake_from_canonical_is_public_module_api() -> None:
    assert callable(rebuild_long_lake_from_canonical)
    signature = inspect.signature(rebuild_long_lake_from_canonical)
    assert "work_root" in signature.parameters
    assert "source_root" in signature.parameters
    assert "allowed_root" in signature.parameters
    assert "only_mismatched" in signature.parameters
    assert "target_months" in signature.parameters
