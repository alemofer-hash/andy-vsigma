from __future__ import annotations

from pathlib import Path

from andy_bi.dataset_builder import build_andy_bi_dataset
from andy_bi.parity import compare_summaries, summarize_dataset


def test_parity_summary_matches_same_dataset(tmp_path: Path) -> None:
    build_andy_bi_dataset(out_dir=tmp_path, fmt="both", synthetic=True, lote_id="parity_lote")

    summary = summarize_dataset(tmp_path)
    findings = compare_summaries(summary, summary)

    assert findings == []
    assert summary["critical_metrics"]["inversao_count"] == 1
