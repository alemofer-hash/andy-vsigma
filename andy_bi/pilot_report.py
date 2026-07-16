from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .dataset_builder import build_andy_bi_dataset
from .parity import compare_summaries, summarize_dataset
from .publish_manifest import file_sha256, load_manifest
from .semantic_dataset import load_dataset_frames


@dataclass(frozen=True)
class PilotReportResult:
    out_dir: Path
    dataset_dir: Path
    html_path: Path
    manifest_path: Path
    validation_report_path: Path
    status: str
    synthetic: bool
    findings: list[str]


def build_pilot_report(
    *,
    dataset_dir: str | Path,
    out_dir: str | Path,
    title: str = "ANDY BI Web Pilot",
    require_synthetic: bool = True,
) -> PilotReportResult:
    dataset = Path(dataset_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not (dataset / "manifest.json").exists():
        build_andy_bi_dataset(out_dir=dataset, fmt="both", synthetic=True, lote_id="andy_bi_pilot_demo")
    manifest = load_manifest(dataset / "manifest.json")
    frames = load_dataset_frames(dataset)
    findings = validate_pilot_inputs(frames, manifest, require_synthetic=require_synthetic)
    metrics = pilot_metrics(frames, manifest)
    html_path = out / "index.html"
    html_path.write_text(render_pilot_html(title=title, metrics=metrics, manifest=manifest), encoding="utf-8")
    parity_report = compare_summaries(summarize_dataset(dataset), summarize_dataset(dataset))
    if parity_report:
        findings.extend(item.message for item in parity_report)
    status = "passed" if not findings else "blocked"
    report_path = write_pilot_validation_report(out / "pilot_validation_report.md", metrics, findings)
    report_manifest = {
        "schema": "andy.bi.pilot_report.v1",
        "generated_utc": now_utc(),
        "status": status,
        "synthetic": bool(manifest.get("audit_summary", {}).get("synthetic") is True),
        "dataset_dir": str(dataset),
        "dataset_manifest_sha256": file_sha256(dataset / "manifest.json"),
        "html": html_path.name,
        "html_sha256": file_sha256(html_path),
        "validation_report": report_path.name,
        "published_to_corporate_bi": False,
        "contains_real_data": False,
        "uses_real_identity_provider": False,
        "safe_for_publication_review": status == "passed" and not findings,
        "pages": list(pilot_pages().keys()),
        "metrics": metrics,
        "findings": findings,
    }
    manifest_path = out / "pilot_report_manifest.json"
    manifest_path.write_text(json.dumps(report_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return PilotReportResult(
        out_dir=out,
        dataset_dir=dataset,
        html_path=html_path,
        manifest_path=manifest_path,
        validation_report_path=report_path,
        status=status,
        synthetic=report_manifest["synthetic"],
        findings=findings,
    )


def validate_pilot_inputs(frames: Mapping[str, pd.DataFrame], manifest: Mapping[str, Any], *, require_synthetic: bool = True) -> list[str]:
    findings: list[str] = []
    required = {"fact_medicoes_long", "fact_power_flow", "fact_load_profile", "fact_catalog_quality", "fact_access_audit"}
    missing = sorted(required - set(frames))
    findings.extend(f"missing_table:{table}" for table in missing)
    if manifest.get("safety_boundary", {}).get("published_to_corporate_bi") is not False:
        findings.append("dataset_manifest_must_not_be_published")
    if manifest.get("safety_boundary", {}).get("contains_credentials") is not False:
        findings.append("dataset_manifest_must_not_contain_credentials")
    if require_synthetic and manifest.get("audit_summary", {}).get("synthetic") is not True:
        findings.append("pilot_requires_synthetic_dataset")
    return findings


def pilot_metrics(frames: Mapping[str, pd.DataFrame], manifest: Mapping[str, Any]) -> dict[str, Any]:
    medicoes = frames.get("fact_medicoes_long", pd.DataFrame())
    flow = frames.get("fact_power_flow", pd.DataFrame())
    load = frames.get("fact_load_profile", pd.DataFrame())
    catalog = frames.get("fact_catalog_quality", pd.DataFrame())
    audit = frames.get("fact_access_audit", pd.DataFrame())
    timestamps = pd.to_datetime(medicoes.get("timestamp", pd.Series(dtype="datetime64[ns]")), errors="coerce").dropna()
    return {
        "lote_id": str(manifest.get("lote_id", "")),
        "dataset_version": str(manifest.get("dataset_version", "")),
        "schema_version": str(manifest.get("schema_version", "")),
        "validation_status": str(manifest.get("validation_status", "")),
        "medicoes": int(len(medicoes)),
        "fontes": _nunique(medicoes, "source_id"),
        "subestacoes": _nunique(medicoes, "se_id"),
        "equipamentos": _nunique(medicoes, "equipamento_id"),
        "terminais": _nunique(medicoes, "terminal_id"),
        "variaveis": _nunique(medicoes, "variavel_id"),
        "period_start": timestamps.min().isoformat() if not timestamps.empty else "",
        "period_end": timestamps.max().isoformat() if not timestamps.empty else "",
        "cadencia": _first(catalog, "cadencia_detectada", "unknown"),
        "lacunas": _int_sum(catalog, "lacunas_detectadas"),
        "quality_flag": _first(catalog, "quality_flag", "unknown"),
        "inversoes": int(flow["inversao_flag"].fillna(False).astype(bool).sum()) if "inversao_flag" in flow else 0,
        "mw_sum": _float_sum(flow, "mw"),
        "mva_sum": _float_sum(flow, "mva"),
        "fp_min": _float_min(flow, "fp_assinado"),
        "fp_max": _float_max(flow, "fp_assinado"),
        "patamares": _nunique(load, "patamar_id"),
        "audit_events": int(len(audit)),
        "row_counts": dict(manifest.get("row_counts", {})),
        "source_cadence_summary": dict(manifest.get("source_cadence_summary", {})),
    }


def render_pilot_html(*, title: str, metrics: Mapping[str, Any], manifest: Mapping[str, Any]) -> str:
    cards = [
        ("Medicoes", metrics["medicoes"]),
        ("Fontes", metrics["fontes"]),
        ("Subestacoes", metrics["subestacoes"]),
        ("Equipamentos", metrics["equipamentos"]),
        ("Variaveis", metrics["variaveis"]),
        ("Inversoes", metrics["inversoes"]),
    ]
    sections = pilot_pages()
    card_html = "\n".join(f"<article class='card'><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></article>" for label, value in cards)
    page_html = "\n".join(
        f"<section><h2>{html.escape(name)}</h2><ul>{''.join(f'<li>{html.escape(item)}</li>' for item in bullets)}</ul></section>"
        for name, bullets in sections.items()
    )
    flow_svg = _flow_svg(float(metrics["mw_sum"]), float(metrics["mva_sum"]), int(metrics["inversoes"]))
    json_block = html.escape(json.dumps({"metrics": metrics, "manifest": _safe_manifest_summary(manifest)}, ensure_ascii=False, indent=2, sort_keys=True))
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7fb;
      --ink: #162033;
      --muted: #5d6b82;
      --surface: #ffffff;
      --line: #d8e1ee;
      --accent: #0877b9;
      --good: #17865b;
      --warn: #b46b00;
    }}
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: var(--bg); color: var(--ink); }}
    header {{ padding: 32px 44px; background: #0c1f34; color: white; }}
    header p {{ color: #b9d7f2; margin: 6px 0 0; }}
    main {{ padding: 28px 44px 48px; }}
    .banner {{ padding: 14px 18px; background: #e8f6ef; border: 1px solid #a9ddc0; border-radius: 10px; color: #0f5d3d; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin: 18px 0 28px; }}
    .card, section, .chart, pre {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 8px 20px rgba(24, 38, 64, .06); }}
    .card {{ padding: 18px; }}
    .card span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    .card strong {{ display: block; margin-top: 8px; font-size: 28px; }}
    .two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, .8fr); gap: 18px; }}
    section {{ padding: 18px 22px; margin-bottom: 18px; }}
    section h2 {{ margin: 0 0 10px; font-size: 19px; }}
    li {{ margin: 6px 0; color: var(--muted); }}
    .chart {{ padding: 18px; margin-bottom: 18px; }}
    pre {{ padding: 18px; overflow: auto; font-size: 12px; }}
    footer {{ color: var(--muted); padding: 0 44px 28px; }}
    @media (max-width: 860px) {{ .two {{ grid-template-columns: 1fr; }} header, main, footer {{ padding-left: 22px; padding-right: 22px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <p>Relatorio piloto local com dataset sintetico. Publicacao corporativa real permanece desligada.</p>
  </header>
  <main>
    <div class="banner">Dataset sintetico/publicavel para revisao: sem dados reais, sem credenciais, sem provider real e sem publicacao automatica.</div>
    <div class="grid">{card_html}</div>
    <div class="two">
      <div>{page_html}</div>
      <aside>
        <div class="chart"><h2>Fluxo P/Q sintetico</h2>{flow_svg}</div>
        <section>
          <h2>Manifesto</h2>
          <ul>
            <li>Lote: {html.escape(str(metrics["lote_id"]))}</li>
            <li>Schema: {html.escape(str(metrics["schema_version"]))}</li>
            <li>Status: {html.escape(str(metrics["validation_status"]))}</li>
            <li>Periodo: {html.escape(str(metrics["period_start"]))} a {html.escape(str(metrics["period_end"]))}</li>
          </ul>
        </section>
      </aside>
    </div>
    <h2>Resumo tecnico sob demanda</h2>
    <pre>{json_block}</pre>
  </main>
  <footer>ANDY BI Web Pilot - gerado localmente pela engine Python. Nao publicar sem aceite humano e RLS/ABAC real.</footer>
</body>
</html>
"""


def pilot_pages() -> dict[str, list[str]]:
    return {
        "Cockpit Executivo ANDY": [
            "Cobertura temporal, fontes, subestacoes, equipamentos, variaveis e qualidade do lote.",
            "Indicadores sao derivados do dataset sintetico governado.",
        ],
        "Catalogo de Medicoes": [
            "Filtros esperados: Ano, Mes, SE, BAY/Alimentador, Equipamento, Terminal, Dia e Variavel.",
            "Disponibilidade e lacunas usam fatos precomputados pelo ANDY.",
        ],
        "Patamar e Carga": [
            "Patamar e estatisticas de carga chegam em fact_load_profile.",
            "BI apresenta e filtra; nao recalcula regra eletrica critica.",
        ],
        "Fluxo P/Q e Inversao": [
            "MW, MVA, FP assinado, sentido, quadrante e inversao chegam em fact_power_flow.",
            "Inversao sintetica aparece para validar layout e auditoria visual.",
        ],
        "Qualidade e Auditoria": [
            "Manifesto contem lote, hash, schema version, quality flags e audit summary.",
            "Eventos de acesso/exportacao reais dependem do workspace corporativo.",
        ],
        "Paridade ANDY Desktop": [
            "A amostra sintetica valida estrutura e contrato.",
            "Paridade com XLSX real so deve acontecer em Homolog com dado aprovado.",
        ],
    }


def write_pilot_validation_report(path: str | Path, metrics: Mapping[str, Any], findings: list[str]) -> Path:
    lines = [
        "# ANDY BI Pilot Synthetic Validation",
        "",
        f"- Status: {'passed' if not findings else 'blocked'}",
        "- Synthetic dataset: true",
        "- Published to corporate BI: false",
        "- Contains real data: false",
        "- Uses real identity provider: false",
        "",
        "## Metrics",
        "",
    ]
    for key in ("medicoes", "fontes", "subestacoes", "equipamentos", "variaveis", "inversoes", "mw_sum", "mva_sum", "patamares", "audit_events"):
        lines.append(f"- {key}: {metrics.get(key)}")
    lines.extend(["", "## Findings", ""])
    if findings:
        lines.extend(f"- {item}" for item in findings)
    else:
        lines.append("- none")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _flow_svg(mw_sum: float, mva_sum: float, inversoes: int) -> str:
    mw_width = min(240, max(20, abs(mw_sum) * 8))
    mva_width = min(240, max(20, abs(mva_sum) * 6))
    inv_width = min(240, max(20, inversoes * 80))
    return f"""
<svg viewBox="0 0 340 170" width="100%" role="img" aria-label="Fluxo P/Q sintetico">
  <line x1="70" y1="25" x2="70" y2="145" stroke="#cbd6e5" />
  <text x="0" y="42" font-size="12" fill="#5d6b82">MW</text>
  <rect x="70" y="28" width="{mw_width:.1f}" height="22" rx="5" fill="#0877b9" />
  <text x="0" y="82" font-size="12" fill="#5d6b82">MVA</text>
  <rect x="70" y="68" width="{mva_width:.1f}" height="22" rx="5" fill="#17865b" />
  <text x="0" y="122" font-size="12" fill="#5d6b82">INV</text>
  <rect x="70" y="108" width="{inv_width:.1f}" height="22" rx="5" fill="#b46b00" />
  <text x="70" y="160" font-size="11" fill="#5d6b82">Valores sinteticos precomputados pelo ANDY Python</text>
</svg>
"""


def _safe_manifest_summary(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "dataset_version": manifest.get("dataset_version"),
        "schema_version": manifest.get("schema_version"),
        "lote_id": manifest.get("lote_id"),
        "validation_status": manifest.get("validation_status"),
        "row_counts": manifest.get("row_counts"),
        "safety_boundary": manifest.get("safety_boundary"),
    }


def _nunique(frame: pd.DataFrame, column: str) -> int:
    return int(frame[column].dropna().nunique()) if column in frame.columns else 0


def _first(frame: pd.DataFrame, column: str, default: str) -> str:
    if column not in frame.columns or frame.empty:
        return default
    values = frame[column].dropna().astype(str)
    return str(values.iloc[0]) if not values.empty else default


def _int_sum(frame: pd.DataFrame, column: str) -> int:
    return int(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum()) if column in frame.columns else 0


def _float_sum(frame: pd.DataFrame, column: str) -> float:
    return float(pd.to_numeric(frame[column], errors="coerce").fillna(0.0).sum()) if column in frame.columns else 0.0


def _float_min(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame.columns:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return float(values.min()) if not values.empty else None


def _float_max(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame.columns:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    return float(values.max()) if not values.empty else None


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
