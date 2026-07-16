# ANDY - Validation Logs

## Execucao mais recente

- Data/Hora: `2026-03-10 15:08:30 -03:00`
- Comando:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\run_validation_suite.ps1`
- Suite executada:
  - `tests/validation`
- Resultado:
  - `VALIDATION PASSED`
  - `29 passed in 15.35s`
  - `Combinatorial cases executed: 29`
  - `Feature families covered: 5`
  - `Failed combinations: 0`

## Artefatos gerados

- Relatorio completo:
  - `artifacts/validation_report.log`
- JUnit XML:
  - `artifacts/validation_junit.xml`
- Workspace temporario de validacao:
  - `.validation_tmp`

## Escopo validado

- Smoke de imports e entrypoints principais
- Ingestao CSV/XLSX para lake temporario
- DuckDB e view `medicoes`
- Query builder (filtros e resolucao hierarquica)
- Caminho principal de consulta (`query_page`)
- Export CSV e export XLSX dashboard
- Compatibilidade da selecao XLSX por `ponto_id`
