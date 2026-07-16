from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_publication_docs_exist_and_state_no_custom_login() -> None:
    required = [
        ROOT / "docs" / "ANDY_BI_WEB_CORPORATE_PRODUCT_BRIEF.md",
        ROOT / "docs" / "ANDY_BI_WEB_TARGET_ARCHITECTURE.md",
        ROOT / "docs" / "ANDY_BI_DATA_CONTRACT.md",
        ROOT / "docs" / "ANDY_BI_RLS_ABAC_POLICY.md",
        ROOT / "docs" / "ANDY_BI_CORPORATE_PUBLICATION_PROCEDURE.md",
        ROOT / "docs" / "ANDY_BI_PILOT_REPORT_SPEC.md",
        ROOT / "docs" / "ANDY_BI_PARITY_VALIDATION.md",
    ]

    for path in required:
        assert path.exists(), path
    product = (ROOT / "docs" / "ANDY_BI_WEB_CORPORATE_PRODUCT_BRIEF.md").read_text(encoding="utf-8")
    assert "Nao criar login proprio" in product or "nao criar login proprio" in product
