# ANDY

Aplicacao para ingestao, catalogacao e exploracao de medicoes eletricas, com foco em:
- pipeline de ingestao (CSV/XLSX -> Parquet + DuckDB),
- consulta e exportacao via UI Streamlit,
- geracao de dashboard XLSX com grafico dinamico,
- controles de seguranca para uso em producao.

## 1. Visao geral

O projeto organiza arquivos brutos de medicoes em um data lake local (`ANDYS_LAKE`) e disponibiliza consultas em DuckDB pela view `medicoes`.

Fluxo principal:
1. `andys_indexer.py` encontra arquivos de entrada e gera Parquets particionados.
2. O indexador cria/atualiza o catalogo DuckDB (`medicoes` e `medicoes_canon`).
3. `andys_table_app.py`: app Streamlit (consulta + exportacao + auditoria pre-export).
4. `andys_report_runner.py` permite gerar dashboard XLSX por CLI.
5. `andys_viewer.py` oferece inspecao rapida do lake por linha de comando.

## 2. Estrutura do repositorio

- `andys_indexer.py`: ingestao e indexacao de arquivos brutos.
- `andys_table_app.py`: app Streamlit (consulta + exportacao + auditoria pre-export).
- `andys_report_runner.py`: geracao de relatorio XLSX por CLI.
- `andys_viewer.py`: utilitarios CLI para exploracao do DuckDB.
- `config.py`: configuracao central por ambiente e validacao de paths.
- `db/query_builder.py`: montagem segura de filtros, ordenacao e paginacao SQL.
- `security/auth.py`: contexto de usuario e RBAC (`viewer`, `exporter`, `admin`).
- `security/audit.py`: trilha de auditoria para exportacoes.
- `security/errors.py`: tratamento padronizado de erros para usuario.
- `xlsx_selection.py`: modelo canonico da selecao XLSX por equipamento.
- `tests/`: testes de pipeline, seguranca de query e validacoes.
- `SECURITY_REQUIREMENTS_PROD.md`: baseline de seguranca para producao.
- `RUN_SECURITY_CHECKS.md`: comandos de verificacao local.

## 3. Requisitos

- Python 3.11+ (recomendado usar venv)
- Windows PowerShell (comandos abaixo)
- Dependencias:
  - pandas 2.3.3
  - duckdb 1.4.4
  - pyarrow 23.0.1
  - streamlit 1.54.0
  - openpyxl 3.1.5

## 4. Instalacao

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

## 5. Configuracao

Variaveis de ambiente suportadas:

- `ANDYS_ENV`: `dev` (default) ou `prod`
- `ANDYS_SOURCE_ROOT`: raiz de entrada (somente leitura), ex: `\\sfspoa03.ceee.local\DivEng\ELIPSE`
- `ANDYS_WORK_ROOT`: raiz local de trabalho (leitura/escrita)
- `ANDYS_DB_PATH`: caminho do DuckDB
- `ANDYS_EXPORT_DIR`: pasta de exportacao
- `ANDYS_ALLOWED_ROOT`: raiz permitida para db/export (bloqueia escape de path)
- `ANDYS_LOG_LEVEL`: nivel de log (default `INFO`)
- `ANDYS_AUDIT_LOG_PATH`: arquivo de auditoria JSONL
- `ANDYS_ROLE`: role em dev (`viewer`, `exporter`, `admin`)
- `ANDYS_USER`: usuario em dev
- `ANDYS_AUTH_ROLE_HEADER`: header de role em prod (default `X-ANDYS-ROLE`)
- `ANDYS_AUTH_USER_HEADER`: header de usuario em prod (default `X-ANDYS-USER`)
- `ANDYS_ADMIN_DIAG`: habilita diagnostico admin (`1`/`0`)

Comportamento por ambiente:

- `dev`: permite editar caminhos na sidebar do app.
- `prod`: caminhos somente por ambiente; valida raiz permitida e paths absolutos.

Separacao obrigatoria de integridade:
- `ANDYS_SOURCE_ROOT`: apenas leitura (CSV/XLSX de origem). Nunca recebe manifest/cache/log/export.
- `ANDYS_ALLOWED_ROOT` + `ANDYS_WORK_ROOT`: destino de escrita (lake, duckdb, manifest, logs, exports).

## 6. Ingestao e indexacao

### 6.1 Entrada esperada

- Arquivos em toda a arvore do `ANDYS_SOURCE_ROOT` (varredura recursiva), por exemplo:
  - `Parametros eletricos - 01_2025 - Todas SEs.csv`
  - `Parametros eletricos - 02_2025 - Todas SEs.xlsx`
- O parser extrai `mes/ano` do nome (`MM_YYYY`) quando disponivel.
- Se o nome nao tiver `MM_YYYY`, o indexador deriva `ano/mes` a partir do timestamp da medicao.

### 6.2 Robustez da ingestao

Para CSV, o indexador detecta automaticamente:
- encoding (`utf-8-sig`, `utf-8`, `cp1252`, `latin1`),
- separador (`;`, `,`, `TAB`, `|`),
- linha real de cabecalho.

Tambem aplica:
- normalizacao de colunas (sinonimos para `SE`, `BAY`, `EQUIPAMENTO`, `TERMINAL`, `TIMESTAMP`),
- parse de terminal a partir de `IDENTIFICADOR`/`EQUIPAMENTO`,
- derivacao de `ponto_id = SE|BAY|EQUIPAMENTO|TERMINAL`,
- classificacao de qualidade de contexto (`OK`, `PARSED`, `MISSING`).

### 6.3 Saida gerada

No root configurado, o pipeline cria:
- `ANDYS_LAKE/ano=YYYY/mes=MM/medicoes_*.parquet` (formato LONG),
- `ANDYS_LAKE/canonico/ano=YYYY/mes=MM/medicoes_canon_*.parquet`,
- `ANDYS_LAKE/manifest.json` (fingerprint por arquivo),
- `ANDYS_LAKE/andys.duckdb` (views `medicoes` e `medicoes_canon`).

### 6.4 Executar indexacao

```powershell
.\.venv\Scripts\python.exe .\andys_indexer.py
```

Observacao:
- Entrada sempre em `ANDYS_SOURCE_ROOT` (somente leitura).
- Saida sempre em `ANDYS_WORK_ROOT`/`ANDYS_ALLOWED_ROOT` (lake, duckdb, manifest, logs e exports).
- O indexador nunca escreve no share de origem.

## 7. App Streamlit

Executar:

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\andys_table_app.py
```

Funcionalidades principais:
- resumo do lake (linhas, periodo, variaveis, top equipamentos),
- filtros hierarquicos em cascata (`SE -> BAY -> EQUIPAMENTO -> TERMINAL -> ponto_id`),
- busca textual por `ponto_id` e selecao primaria por pontos,
- variaveis carregadas por escopo dos `ponto_id` selecionados (`DISTINCT var`),
- filtros avancados em colunas adicionais,
- tabela paginada com ordenacao allowlist,
- auditoria pre-exportacao (risk engine) com:
  - estimativas leves (`COUNT`, `DISTINCT`, `MIN/MAX`) sem puxar dataset inteiro,
  - findings por severidade (`INFO/WARN/ERROR`),
  - recomendacoes acionaveis (recorte de periodo, timefloor, agregacao, max_timestamps),
  - bloqueio hard-stop para XLSX quando limite fisico do Excel e inevitavel,
  - confirmacao explicita para `WARN`/soft-error antes de forcar exportacao,
  - trilha de auditoria persistente em JSONL (`event=export_audit`),
- exportacao:
  - CSV LONG completo,
  - CSV WIDE (timestamp x series),
  - XLSX dashboard (motor BI).

Regra de negocio importante:
- para equipamentos `TR*`, Terminal e obrigatorio para exportar (evita ambiguidade).

## 8. Selecao XLSX (derivada de pontos)

Formato canonico (contrato mantido no motor XLSX):

```json
{
  "EQP_001": ["IA", "IB", "VA"],
  "EQP_002": ["P", "Q"]
}
```

Regras:
- o fluxo primario da UI e selecionar `ponto_id` + variaveis,
- o app converte automaticamente para `{"EQUIPAMENTO": ["VAR1", ...]}`,
- cada equipamento derivado dos pontos deve ter ao menos 1 variavel,
- pares `(equip, var)` sao expandidos internamente para compor as series do dashboard.

## 9. Relatorio XLSX por CLI

### 9.1 Selftest ponta-a-ponta

```powershell
.\.venv\Scripts\python.exe .\andys_report_runner.py --selftest
```

Valida:
- leitura da view `medicoes`,
- geracao de arquivo XLSX,
- presenca de abas esperadas (`VIEW_MX`, `DASHBOARD`),
- grafico e series minimas.

### 9.2 Gerar relatorio customizado

```powershell
.\.venv\Scripts\python.exe .\andys_report_runner.py `
  --db "C:\Users\...\Dados2025\ANDYS_LAKE\andys.duckdb" `
  --outdir "C:\Users\...\Dados2025\ANDYS_REPORTS" `
  --equip "TR-001" --equip "AL-002" `
  --from "2025-01-01 00:00:00" `
  --to   "2025-01-02 23:59:59" `
  --var IA --var IB `
  --agg max `
  --timefloor 15min
```

Opcoes uteis:
- `--agg`: `max` ou `last`
- `--timefloor`: ex. `15min`, `1H`, `1D`
- `--equip-slots`, `--var-slots`: capacidade de selecao no dashboard
- `--max-timestamps`: limite de timestamps no XLSX

## 10. Viewer CLI

Comandos:

```powershell
# Resumo do lake
.\.venv\Scripts\python.exe .\andys_viewer.py overview

# Amostra inicial
.\.venv\Scripts\python.exe .\andys_viewer.py sample --n 20

# Buscar equipamento
.\.venv\Scripts\python.exe .\andys_viewer.py search "TR-"

# Detalhe de equipamento
.\.venv\Scripts\python.exe .\andys_viewer.py equip "TR-001"

# Recorte por intervalo
.\.venv\Scripts\python.exe .\andys_viewer.py query `
  --equip "TR-001" `
  --from "2025-01-01 00:00:00" `
  --to   "2025-01-01 23:59:59" `
  --var IA --var IB `
  --out recorte.csv
```

## 11. Seguranca e governanca

Implementado no codigo:
- RBAC: `viewer` (leitura), `exporter` (exporta), `admin` (diagnostico/admin),
- SQL com parametros bind para filtros/paginacao,
- `ORDER BY` restrito por allowlist,
- validacao de entradas (tipos, tamanhos, intervalos),
- sanitizacao de erro para usuario final em producao,
- trilha de auditoria para exportacoes (`audit_export`).
- trilha de auditoria de risco pre-export (`export_audit`) com decisoes e recomendacoes aplicadas.
- log de risco com filtros sanitizados (intervalo de datas, contagem de selecoes e flags), sem payload sensivel.

Para producao, seguir tambem o documento:
- `SECURITY_REQUIREMENTS_PROD.md`

## 12. Testes e checks

Executar testes:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Auditoria de dependencias:

```powershell
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```

Cobertura atual dos testes inclui:
- pipeline de ingestao e uniao de schemas,
- normalizacao de colunas e derivacao de contexto,
- seguranca de query builder,
- validacao de paths,
- normalizacao/expansao/validacao da selecao XLSX,
- auditoria pre-export (`tests/test_export_auditor.py`),
- aplicacao de recomendacoes no estado do app (`tests/test_streamlit_audit_state.py`).

## 13. Troubleshooting

- `Tabela/view 'medicoes' nao encontrada`:
  - execute primeiro `andys_indexer.py` para montar lake/catalogo.
- `Recorte vazio`:
  - revise equipamentos, intervalo de tempo e variaveis.
- `Para TRs, selecione Terminal`:
  - aplique filtro de terminal (1/2) ao exportar.
- `Falha ao salvar XLSX`:
  - feche o arquivo no Excel ou altere nome/destino.
- `Path fora da raiz permitida`:
  - ajuste `ANDYS_ALLOWED_ROOT` e paths de DB/export.

## 14. Changelog

Mudancas recentes:
- pipeline CSV canonico com contexto eletrico (`SE/BAY/EQUIPAMENTO/TERMINAL`),
- `ponto_id` e `context_quality`,
- novo fluxo de selecao XLSX por equipamento,
- bloqueio fail-fast para equipamento sem variavel no XLSX,
- novos testes para ingestao e seguranca.

Detalhes completos em `CHANGELOG.md`.
