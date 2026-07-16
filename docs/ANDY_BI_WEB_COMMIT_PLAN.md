# ANDY BI Web Commit Plan

## Regra

Nao usar `git add .`. Nao commitar artifacts, reports runtime, datasets gerados,
logs, exports, configs privadas ou paths sensiveis.

## Commit 1 - ANDY BI Web: data contract and dataset builder

Inclui:

- `andy_bi/schema_version.py`
- `andy_bi/data_contract.py`
- `andy_bi/dataset_schema.py`
- `andy_bi/publish_manifest.py`
- `andy_bi/semantic_dataset.py`
- `andy_bi/dataset_builder.py`
- `scripts/build_andy_bi_dataset.py`
- `scripts/check_andy_bi_dataset_contract.py`
- `scripts/check_andy_bi_dataset_builder.py`
- `config/andy_bi_dataset_schema.example.json`
- `config/andy_bi_publish_manifest.example.json`
- testes de contrato, builder e manifest.

## Commit 2 - ANDY BI Web: semantic model, RLS and refresh governance

Inclui:

- `andy_bi/semantic_model.py`
- `andy_bi/access_model.py`
- `andy_bi/rls_policy.py`
- `andy_bi/refresh_plan.py`
- `scripts/check_andy_bi_semantic_model.py`
- `scripts/check_andy_bi_rls_policy.py`
- `config/andy_bi_semantic_model.example.json`
- `config/andy_bi_rls_policy.example.json`
- `config/andy_bi_refresh.example.json`
- docs e testes correspondentes.

## Commit 3 - ANDY BI Web: parity validation and publication package

Inclui:

- `andy_bi/parity.py`
- `andy_bi/export_package.py`
- `scripts/check_andy_bi_parity.py`
- `scripts/build_andy_bi_corporate_package.py`
- `scripts/check_andy_bi_publication_package.py`
- docs de publicacao, workspace, piloto e paridade.
- testes correspondentes.

## Commit 4 - ANDY BI Web: identity readiness docs and roadmap

Inclui documentos e scripts BI previamente preparados que sustentam readiness:

- `andy_bi/identity.py`
- `andy_bi/providers.py`
- `andy_bi/policy.py`
- `andy_bi/enforcement.py`
- `andy_bi/https_security.py`
- `scripts/check_andy_bi_*.py`
- `tests/test_andy_bi_*.py`
- `docs/ANDY_BI_*.md`
- `README.md`

## Fora do commit

- `artifacts/`
- `reports/`
- `.validation_tmp/`
- `*.parquet`
- `*.duckdb`
- `*.xlsx`
- `*.csv`
- `*.private.json`
- `.env`
- secrets, credentials e tokens.
