# ANDY BI Pilot Synthetic Validation

## Objetivo

Construir um relatorio piloto local, estatico e publicavel para revisao em Dev,
usando somente dataset sintetico gerado pelo ANDY. Este artefato demonstra a
organizacao visual e semantica do BI sem depender de Power BI instalado, gateway,
workspace real, provider real ou dados operacionais.

## Artefatos gerados

Comando:

```powershell
.\.venv\Scripts\python.exe scripts\build_andy_bi_pilot_report.py --dataset artifacts\andy_bi_dataset --out artifacts\andy_bi_pilot_report
```

Saida:

- `artifacts/andy_bi_pilot_report/index.html`
- `artifacts/andy_bi_pilot_report/pilot_report_manifest.json`
- `artifacts/andy_bi_pilot_report/pilot_validation_report.md`

## Paginas cobertas

- Cockpit Executivo ANDY.
- Catalogo de Medicoes.
- Patamar e Carga.
- Fluxo P/Q e Inversao.
- Qualidade e Auditoria.
- Paridade ANDY Desktop.

## Garantias

- Dataset sintetico obrigatorio por padrao.
- Nenhum dado real.
- Nenhum path corporativo real.
- Nenhuma credencial.
- Nenhum provider real.
- Nenhuma publicacao automatica.
- HTML autocontido, sem CDN e sem chamada externa.

## Uso esperado

O piloto serve para alinhar produto e BI antes de construir o relatorio em uma
plataforma corporativa. Depois da aprovacao visual e semantica, a equipe de BI
pode reproduzir as paginas no workspace Dev usando o mesmo contrato de dados.

## Gate

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_pilot_report.py
```

O gate bloqueia se o manifesto nao for sintetico, se indicar publicacao real ou
se o HTML contiver padroes privados/credenciais.
