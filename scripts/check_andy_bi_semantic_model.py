from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from andy_bi.semantic_model import default_semantic_model, validate_semantic_model, write_default_semantic_model  # noqa: E402


REPORT_JSON = ROOT / "reports" / "ANDY_BI_SEMANTIC_MODEL.json"
REPORT_MD = ROOT / "reports" / "ANDY_BI_SEMANTIC_MODEL.md"


def main() -> int:
    model = default_semantic_model()
    failures = validate_semantic_model(model)
    generated = ROOT / "artifacts" / "andy_bi_semantic_model_check" / "semantic_model.json"
    write_default_semantic_model(generated)
    report = {
        "status": "passed" if not failures else "blocked",
        "failures": failures,
        "relationships": len(model["relationships"]),
        "measures": len(model["measures"]),
        "generated_model": str(generated),
        "critical_math_reimplemented_in_bi": model["critical_math_policy"]["bi_may_reimplement_mva_fp_mw_flow_patamar"],
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(_markdown(report), encoding="utf-8")
    print(f"status={report['status']}")
    print(f"report={REPORT_MD}")
    return 0 if not failures else 1


def _markdown(report: dict) -> str:
    return (
        "# ANDY BI Semantic Model Gate\n\n"
        f"- Status: {report['status']}\n"
        f"- Relationships: {report['relationships']}\n"
        f"- Measures: {report['measures']}\n"
        f"- Critical math reimplemented in BI: {report['critical_math_reimplemented_in_bi']}\n"
        f"- Generated model: {report['generated_model']}\n"
        f"- Failures: {', '.join(report['failures']) if report['failures'] else 'none'}\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
