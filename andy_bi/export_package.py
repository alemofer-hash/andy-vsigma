from __future__ import annotations

import shutil
from pathlib import Path

from .data_contract import write_default_contract
from .dataset_builder import build_andy_bi_dataset
from .refresh_plan import write_default_refresh_plan
from .rls_policy import write_default_rls_policy
from .semantic_model import write_default_semantic_model


ROOT = Path(__file__).resolve().parents[1]

DOCS_FOR_PACKAGE = [
    "ANDY_BI_CORPORATE_PUBLICATION_PROCEDURE.md",
    "ANDY_BI_DATA_CONTRACT.md",
    "ANDY_BI_WORKSPACE_REQUEST_CHECKLIST.md",
    "ANDY_BI_RLS_ABAC_POLICY.md",
    "ANDY_BI_PILOT_REPORT_SPEC.md",
    "ANDY_BI_PARITY_VALIDATION.md",
    "ANDY_BI_REFRESH_STRATEGY.md",
    "ANDY_BI_WEB_TARGET_ARCHITECTURE.md",
]


def build_corporate_package(out_dir: str | Path = ROOT / "artifacts" / "andy_bi_corporate_package") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_readme(out / "README_FOR_TI_BI.md")
    _copy_docs(out)
    _write_owner_matrix_template(out / "owner_matrix_template.md")

    config_dir = out / "config_examples"
    config_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted((ROOT / "config").glob("andy_bi_*.example.json")):
        shutil.copy2(path, config_dir / path.name)

    schema_dir = out / "schema"
    write_default_contract(schema_dir / "andy_bi_dataset_schema.json")
    write_default_semantic_model(schema_dir / "andy_bi_semantic_model.json")
    write_default_rls_policy(schema_dir / "andy_bi_rls_policy.json")
    write_default_refresh_plan(schema_dir / "andy_bi_refresh_plan.json")

    sample_dir = out / "sample_dataset"
    result = build_andy_bi_dataset(out_dir=sample_dir, fmt="both", lote_id="andy_bi_corporate_package_demo", synthetic=True)

    validation_dir = out / "validation_reports"
    validation_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(result.validation_report_path, validation_dir / "sample_dataset_validation_report.md")
    shutil.copy2(result.manifest_path, validation_dir / "sample_dataset_manifest.json")
    return out


def _copy_docs(out: Path) -> None:
    for name in DOCS_FOR_PACKAGE:
        source = ROOT / "docs" / name
        if source.exists():
            shutil.copy2(source, out / name)


def _write_readme(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "# ANDY BI Corporate Package",
                "",
                "Pacote local para revisao de TI/BI. Ele nao publica dataset, nao configura remote,",
                "nao contem credenciais e usa sample dataset sintetico.",
                "",
                "## Conteudo",
                "",
                "- documentos de publicacao e governanca;",
                "- contratos JSON e exemplos de configuracao;",
                "- sample_dataset sintetico para validacao de estrutura;",
                "- relatorios de validacao gerados localmente.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_owner_matrix_template(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "# ANDY BI Owner Matrix Template",
                "",
                "| Papel | Nome/Grupo | Responsabilidade | Aprovacao necessaria |",
                "|---|---|---|---|",
                "| Owner funcional | A definir | Prioridade e aceite de negocio | Sim |",
                "| Owner tecnico | A definir | Refresh, operacao e rollback | Sim |",
                "| Dono do dado | A definir | Escopo e classificacao dos dados | Sim |",
                "| Aprovador seguranca | A definir | RLS/ABAC e exposicao | Sim |",
                "| BI owner | A definir | Workspace, app interno e modelo semantico | Sim |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
