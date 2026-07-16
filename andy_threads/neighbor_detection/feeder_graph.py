from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import pandas as pd

from .config import NeighborDetectionConfig
from .key_parser import is_feeder_name


@dataclass(frozen=True)
class PairDefinition:
    se: str
    first: str
    second: str
    configured_neighbor_pair: bool
    exploratory_pair: bool = False

    @property
    def pair(self) -> tuple[str, str]:
        return self.first, self.second


def build_pair_definitions(
    df: pd.DataFrame,
    config: NeighborDetectionConfig,
    *,
    all_pairs_exploratory: bool = False,
) -> tuple[list[PairDefinition], list[str]]:
    warnings: list[str] = []
    pairs: list[PairDefinition] = []
    present = {
        se: sorted({str(value).upper() for value in part["feeder"].dropna().unique() if is_feeder_name(str(value))})
        for se, part in df.groupby("se")
    }
    for se, substation in config.substations.items():
        available = set(present.get(se, []))
        for first, second in substation.neighbor_pairs:
            if first in available and second in available:
                pairs.append(PairDefinition(se=se, first=first, second=second, configured_neighbor_pair=True))
            else:
                warnings.append(f"configured_pair_missing_data:{se}:{first}:{second}")
    if all_pairs_exploratory:
        for se, feeders in present.items():
            configured = {tuple(sorted(item.pair)) for item in pairs if item.se == se}
            for first, second in combinations(feeders, 2):
                if tuple(sorted((first, second))) not in configured:
                    pairs.append(PairDefinition(se=se, first=first, second=second, configured_neighbor_pair=False, exploratory_pair=True))
    if not pairs:
        warnings.append("no_neighbor_pairs_available_requires_human_topology_or_all_pairs_exploratory")
    return pairs, warnings


def upstream_references_for(config: NeighborDetectionConfig, se: str) -> tuple[str, ...]:
    substation = config.substations.get(se.upper())
    return substation.upstream_references if substation else ()
