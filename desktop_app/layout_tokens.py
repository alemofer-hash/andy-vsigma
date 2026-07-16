from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtWidgets import QFormLayout, QGridLayout, QLayout, QWidget


@dataclass(frozen=True)
class LayoutFrame:
    margins: tuple[int, int, int, int]
    spacing: int
    horizontal_spacing: int | None = None
    vertical_spacing: int | None = None


@dataclass(frozen=True)
class SplitterRule:
    default_sizes: tuple[int, int]
    min_total: int
    min_first: int
    min_second: int
    handle_width: int
    max_first: int | None = None
    max_first_ratio: float | None = None
    max_second: int | None = None
    max_second_ratio: float | None = None


@dataclass(frozen=True)
class ScrollHostRule:
    min_width: int | None = None
    max_width: int | None = None
    min_height: int | None = None
    viewport_margins: tuple[int, int, int, int] = (0, 0, 0, 0)


@dataclass(frozen=True)
class DensityBudget:
    max_large_sections_above_fold: int
    max_secondary_sections_above_fold: int
    deep_analysis_below_main_flow: bool
    compact_grid_field_limit: int
    expanded_section_min_height: int
    preferred_scroll_hosts: tuple[str, ...]


SPACING_SCALE = {
    "micro": 4,
    "tight": 6,
    "compact": 8,
    "regular": 10,
    "section": 12,
    "panel": 16,
    "panel_air": 18,
    "page": 24,
}

WINDOW_DEFAULT_SIZE = (1720, 980)
WINDOW_MINIMUM_SIZE = (1320, 780)
POPUP_MINIMUM_SIZE = (520, 380)

FORM_CONTROL_HEIGHT = 38
SEARCH_FIELD_HEIGHT = 34
CHECKABLE_LIST_HEIGHT = 40
SETUP_MESSAGE_MAX_HEIGHT = 160
MAIN_MESSAGE_MAX_HEIGHT = 140

SECTION_LAYOUTS = {
    "page_setup": LayoutFrame((24, 24, 24, 24), 18),
    "page_main": LayoutFrame((16, 16, 16, 16), 12),
    "hero": LayoutFrame((20, 18, 20, 18), 10),
    "section_primary": LayoutFrame((16, 18, 16, 14), 10),
    "section_secondary": LayoutFrame((16, 18, 16, 14), 10),
    "section_deep": LayoutFrame((16, 20, 16, 16), 12),
    "section_compact": LayoutFrame((16, 18, 16, 14), 8),
    "form_grid": LayoutFrame((0, 0, 0, 0), 10, horizontal_spacing=12, vertical_spacing=10),
    "badge_row": LayoutFrame((0, 4, 0, 0), 8),
    "scroll_host": LayoutFrame((0, 0, 12, 8), 0),
    "dashboard_root": LayoutFrame((0, 0, 0, 0), 16),
    "dashboard_header": LayoutFrame((0, 0, 0, 0), 4),
    "dashboard_section": LayoutFrame((16, 18, 16, 14), 10),
    "extremes_grid": LayoutFrame((0, 0, 0, 0), 12, horizontal_spacing=12, vertical_spacing=12),
    "popup_root": LayoutFrame((12, 12, 12, 12), 8),
    "popup_row": LayoutFrame((0, 0, 0, 0), 6),
    "splash_content": LayoutFrame((74, 62, 74, 54), 12),
}

PANEL_MIN_WIDTHS = {
    "filter_min": 340,
    "filter_max": 520,
    "results_min": 900,
    "table_min": 760,
    "export_min": 390,
    "export_max": 620,
}

PANEL_MIN_HEIGHTS = {
    "table": 420,
    "export_scroll": 320,
    "extreme_card": 230,
}

CHART_MIN_HEIGHTS = {
    "temporal": 320,
    "tiers": 620,
    "pq": 620,
    "voltage": 500,
}

RESPONSIVE_BREAKPOINTS = {
    "extreme_cards_two_column": 1120,
}

SCROLL_HOST_RULES = {
    "filter": ScrollHostRule(
        min_width=PANEL_MIN_WIDTHS["filter_min"],
        max_width=PANEL_MIN_WIDTHS["filter_max"],
    ),
    "results": ScrollHostRule(),
    "export": ScrollHostRule(
        min_width=PANEL_MIN_WIDTHS["export_min"],
        max_width=PANEL_MIN_WIDTHS["export_max"],
        min_height=PANEL_MIN_HEIGHTS["export_scroll"],
        viewport_margins=SECTION_LAYOUTS["scroll_host"].margins,
    ),
}

SPLITTER_RULES = {
    "main": SplitterRule(
        default_sizes=(400, 1280),
        min_total=1180,
        min_first=PANEL_MIN_WIDTHS["filter_min"],
        min_second=PANEL_MIN_WIDTHS["results_min"],
        handle_width=14,
        max_first=PANEL_MIN_WIDTHS["filter_max"],
        max_first_ratio=0.34,
    ),
    "results": SplitterRule(
        default_sizes=(980, 420),
        min_total=1120,
        min_first=720,
        min_second=420,
        handle_width=12,
        max_second=PANEL_MIN_WIDTHS["export_max"],
        max_second_ratio=0.46,
    ),
}

COCKPIT_DENSITY_BUDGET = DensityBudget(
    max_large_sections_above_fold=2,
    max_secondary_sections_above_fold=1,
    deep_analysis_below_main_flow=True,
    compact_grid_field_limit=6,
    expanded_section_min_height=500,
    preferred_scroll_hosts=("filter", "results", "export"),
)


def spacing(step: str) -> int:
    return int(SPACING_SCALE[step])


def section_layout_key(priority: str) -> str:
    normalized = str(priority or "").strip().lower()
    if normalized == "deep":
        return "section_deep"
    if normalized == "compact":
        return "section_compact"
    if normalized == "primary":
        return "section_primary"
    return "section_secondary"


def apply_layout_frame(layout: QLayout, frame: LayoutFrame | str) -> QLayout:
    resolved = SECTION_LAYOUTS[frame] if isinstance(frame, str) else frame
    left, top, right, bottom = resolved.margins
    layout.setContentsMargins(left, top, right, bottom)
    layout.setSpacing(int(resolved.spacing))

    if resolved.horizontal_spacing is not None and hasattr(layout, "setHorizontalSpacing"):
        layout.setHorizontalSpacing(int(resolved.horizontal_spacing))
    if resolved.vertical_spacing is not None and hasattr(layout, "setVerticalSpacing"):
        layout.setVerticalSpacing(int(resolved.vertical_spacing))
    return layout


def apply_section_geometry(
    widget: QWidget,
    *,
    min_width: int | None = None,
    max_width: int | None = None,
    min_height: int | None = None,
) -> QWidget:
    if min_width is not None:
        widget.setMinimumWidth(int(min_width))
    if max_width is not None:
        widget.setMaximumWidth(int(max_width))
    if min_height is not None:
        widget.setMinimumHeight(int(min_height))
    return widget


def normalized_splitter_sizes(rule: SplitterRule, sizes: Optional[list[int]]) -> list[int]:
    current = list(sizes or list(rule.default_sizes))
    if len(current) < 2:
        return list(rule.default_sizes)

    total = max(sum(int(value) for value in current[:2]), int(rule.min_total))
    min_first = int(rule.min_first)
    min_second = int(rule.min_second)
    max_first = total - min_second

    if rule.max_first is not None:
        max_first = min(max_first, int(rule.max_first))
    if rule.max_first_ratio is not None:
        max_first = min(max_first, int(total * float(rule.max_first_ratio)))

    if rule.max_second is not None or rule.max_second_ratio is not None:
        max_second = total - min_first
        if rule.max_second is not None:
            max_second = min(max_second, int(rule.max_second))
        if rule.max_second_ratio is not None:
            max_second = min(max_second, int(total * float(rule.max_second_ratio)))
        min_first = max(min_first, total - max_second)

    if min_first > max_first:
        min_first = int(rule.min_first)
        max_first = total - min_second

    first = min(max(int(current[0]), min_first), max_first)
    second = total - first
    return [first, second]


def splitter_rule(name: str) -> SplitterRule:
    return SPLITTER_RULES[str(name).strip().lower()]


def scroll_host_rule(name: str) -> ScrollHostRule:
    return SCROLL_HOST_RULES[str(name).strip().lower()]


def chart_min_height(name: str) -> int:
    return int(CHART_MIN_HEIGHTS[str(name).strip().lower()])


def should_place_below_main_flow(surface_kind: str) -> bool:
    normalized = str(surface_kind or "").strip().lower()
    return COCKPIT_DENSITY_BUDGET.deep_analysis_below_main_flow and normalized in {"deep", "deep_analysis", "analysis"}


def prefers_compact_grid(field_count: int) -> bool:
    return int(field_count) <= COCKPIT_DENSITY_BUDGET.compact_grid_field_limit
