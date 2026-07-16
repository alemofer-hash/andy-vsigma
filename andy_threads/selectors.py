from __future__ import annotations

from typing import Any, Mapping

from .context import build_query_signature, compute_filter_hash, context_from_bi_selection, context_from_export_options, context_from_query_filters
from .references import AndyThreadReference


def reference_for_selection(selection: Mapping[str, Any]) -> AndyThreadReference:
    if "report_page" in selection or "visual_id" in selection:
        return context_from_bi_selection(selection)
    if "fmt" in selection or "export_id" in selection:
        return context_from_export_options(selection)
    return context_from_query_filters(selection)
