# ANDY BI Data Contract

## Principio

O contrato de dados e a fronteira entre a engine Python do ANDY e o BI
corporativo. Ele define fatos, dimensoes, manifestos, versoes e campos de
auditoria. O BI consome esse contrato; nao substitui a engine.

## Campos obrigatorios por lote

- `dataset_version`
- `schema_version`
- `build_timestamp`
- `source_fingerprint`
- `source_period_start`
- `source_period_end`
- `lote_id`
- `hash_lote`
- `created_by_runtime`
- `andy_engine_version`
- `validation_status`
- `source_cadence_summary`
- `row_counts`
- `quality_flags`
- `audit_summary`

## Tabelas fato

| Tabela | Objetivo |
|---|---|
| `fact_medicoes_long` | Medicoes normalizadas em formato LONG |
| `fact_power_flow` | MW, MVAR, MVA, FP assinado, quadrante, sentido e inversao precomputados |
| `fact_load_profile` | Agregacoes por periodo/patamar |
| `fact_catalog_quality` | Cobertura temporal, pontos, arquivos, cadencia e lacunas |
| `fact_access_audit` | Eventos redigidos/mock de build, acesso, exportacao e auditoria |

## Dimensoes

- `dim_date`
- `dim_time`
- `dim_source`
- `dim_subestacao`
- `dim_bay_alimentador`
- `dim_equipamento`
- `dim_terminal`
- `dim_variavel`
- `dim_cadencia`
- `dim_patamar`
- `dim_lote`
- `dim_quality_flag`
- `dim_access_scope`

## Regras de seguranca

- Dados reais nao entram em testes unitarios.
- Manifesto de exemplo nao contem endpoint, caminho privado, token ou segredo.
- Dataset sintetico pode ser publicado somente como artefato de validacao local.
- Dataset real exige owner, workspace, RLS/ABAC e aceite humano.

## Artefatos

- Schema default: `andy_bi.data_contract.default_data_contract()`.
- Config exemplo: `config/andy_bi_dataset_schema.example.json`.
- Builder local: `scripts/build_andy_bi_dataset.py`.
