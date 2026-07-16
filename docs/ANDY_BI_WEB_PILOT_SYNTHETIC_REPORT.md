# ANDY BI Web Pilot Synthetic Report

## Status

GO tecnico para revisao com dataset sintetico/publicavel.

## Objetivo

Construir o primeiro relatorio piloto local do ANDY BI Web usando apenas dados
sinteticos, sem provider real, sem workspace real, sem publicacao automatica e
sem reimplementar matematica eletrica fora da engine Python.

## Artefatos gerados

- `artifacts/andy_bi_dataset/manifest.json`
- `artifacts/andy_bi_dataset/schema.json`
- `artifacts/andy_bi_dataset/*.parquet`
- `artifacts/andy_bi_dataset/*.csv`
- `artifacts/andy_bi_pilot_report/index.html`
- `artifacts/andy_bi_pilot_report/pilot_report_manifest.json`
- `artifacts/andy_bi_pilot_report/pilot_validation_report.md`
- `artifacts/andy_bi_corporate_package/pilot_report/index.html`

Esses artefatos ficam fora do Git por policy de hygiene.

## Paginas cobertas

- Cockpit Executivo ANDY.
- Catalogo de Medicoes.
- Patamar e Carga.
- Fluxo P/Q e Inversao.
- Qualidade e Auditoria.
- Paridade ANDY Desktop.

## Validacao

Comandos executados:

```powershell
.\.venv\Scripts\python.exe scripts\build_andy_bi_dataset.py --format both --out artifacts\andy_bi_dataset --synthetic
.\.venv\Scripts\python.exe scripts\build_andy_bi_pilot_report.py --dataset artifacts\andy_bi_dataset --out artifacts\andy_bi_pilot_report
.\.venv\Scripts\python.exe scripts\check_andy_bi_pilot_report.py
.\.venv\Scripts\python.exe scripts\check_andy_bi_publication_package.py
```

Resultado:

- Dataset: valid.
- Pilot report: passed.
- Publication package: passed.

## Safety boundary

- `synthetic=true`.
- `published_to_corporate_bi=false`.
- `contains_real_data=false`.
- `uses_real_identity_provider=false`.
- `safe_for_publication_review=true`.

## Observacao operacional

O piloto HTML e um artefato de alinhamento e validacao. Ele nao substitui o
relatorio corporativo real. O proximo passo e reproduzir essa estrutura no
workspace Dev da plataforma BI escolhida, ainda com dataset sintetico.
