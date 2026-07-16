from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import pandas as pd


@dataclass(frozen=True)
class TermDefinition:
    short_label: str
    description: str
    computational_basis: str = ""
    icon: str = ""
    tooltip: str = ""
    example: str = ""


@dataclass
class PatamarAnalysisContext:
    load_profile_result: Any
    query_filters: Any
    temporal_bounds: Tuple[str, str]
    term_glossary: Dict[str, TermDefinition] = field(default_factory=dict)
    sheets_preview: Dict[str, pd.DataFrame] = field(default_factory=dict)
    export_metadata: Dict[str, Any] = field(default_factory=dict)
    visual_hierarchy: Dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def has_data(self) -> bool:
        if self.load_profile_result is not None:
            frame = getattr(self.load_profile_result, "frame", None)
            if isinstance(frame, pd.DataFrame) and not frame.empty:
                return True
            summary = getattr(self.load_profile_result, "summary", None)
            if isinstance(summary, pd.DataFrame) and not summary.empty:
                return True
        return any(isinstance(df, pd.DataFrame) and not df.empty for df in self.sheets_preview.values())

    def get_term_definition(self, term: str) -> Optional[TermDefinition]:
        return self.term_glossary.get(str(term or "").strip())
