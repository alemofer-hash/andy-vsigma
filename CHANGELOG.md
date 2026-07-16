# Changelog

## 2026-03-02 - Pipeline CSV canonico (SE/BAY/EQUIPAMENTO/TERMINAL)
- Ingestao CSV robusta com fallback de separador/encoding.
- Normalizacao de colunas com sinonimos para chaves canônicas:
  - `SE`, `BAY`, `EQUIPAMENTO`, `TERMINAL`, `TIMESTAMP`, `IDENTIFICADOR_RAW`.
- Inclusao de colunas derivadas:
  - `ponto_id`
  - `context_quality` (`OK`, `PARSED`, `MISSING`)
- Persistencia de tabela canonica (superset) e view `medicoes_canon` no DuckDB.
- UI atualizada com filtros de contexto: Data, SE, Bay, Equipamento, Terminal + Filtros Avancados.
- Regra de negocio TR aplicada no export:
  - sem terminal selecionado para TR, exportacao e bloqueada.
- Exports passam a incluir colunas-chave (`TIMESTAMP`, `SE`, `BAY`, `EQUIPAMENTO`, `TERMINAL`, `ponto_id`).
- Novos testes unitarios/integracao para normalizacao, parse de terminal, ponto_id e union de schemas CSV.

## 2026-03-02 - Refatoracao de selecao XLSX por equipamento
- Alterado modelo de selecao para formato canonico:
  - `selections := { "<equip_id>": ["var1","var2",...], ... }`
- Adicionadas funcoes:
  - `normalize_selections(raw)`
  - `migrate_legacy_pairs(raw_pairs)`
  - `expand_pairs(selections)`
  - `validate_selections(selections, required_equips)`
- UI atualizada:
  - equipamento selecionado uma vez;
  - variaveis selecionadas por equipamento (multi-select em lote).
- Exportacao XLSX atualizada:
  - pares expandidos automaticamente;
  - validacao fail-fast para equipamento sem variavel.
- Compatibilidade:
  - migracao de formato antigo (lista de pares repetidos) para mapa por equipamento.
- Testes adicionados para normalizacao/migracao/expansao/validacao.
