# ANDY Threads Data Contract

## Entidades

### Thread

Representa uma discussao tecnica governada. Campos minimos:

- `thread_id`
- `title`
- `kind`
- `status`
- `priority`
- `reference`
- `created_by`
- `owner_sector`
- `created_at`

### Message

Mensagem contextual dentro de uma thread. Campos minimos:

- `message_id`
- `thread_id`
- `author`
- `body`
- `message_kind`
- `created_at`

### Reference

Referencia tecnica que prende a conversa ao dado. Pode conter:

- `entity_type`
- `lote_id`
- `dataset_version`
- `source_fingerprint`
- `se`
- `bay`
- `alimentador`
- `bay_or_feeder`
- `equipamento`
- `terminal`
- `variavel`
- `ponto_id`
- `period_start`
- `period_end`
- `source_cadence`
- `filter_hash`
- `query_signature`
- `report_page`
- `visual_id`
- `export_id`
- `quality_flag`
- `anomaly_id`

### DecisionRecord

Decisao operacional ou tecnica associada a evidencias:

- `decision_id`
- `thread_id`
- `decision_type`
- `summary`
- `decided_by`
- `evidence_refs`
- `created_at`

### AuditEvent

Evento de auditoria local:

- `event_id`
- `thread_id`
- `event_type`
- `actor`
- `timestamp`
- `payload`

### SectorLens

Lente setorial que define dono, consultados e contexto minimo.

## Tipos de problema

O MVP cobre qualidade de dados, lacuna, cadencia, mapeamento de terminal,
mapeamento de variavel, fluxo de carga, inversao, transicao AT/BT, manobra,
impacto de obra/manutencao, sinal de protecao/automacao, issue de dataset BI,
issue de acesso/RLS, paridade Desktop/BI e revisao geral.

## Estados

`OPEN`, `TRIAGED`, `WAITING_DATA_OWNER`, `WAITING_ENGINEERING`,
`WAITING_OPERATION`, `WAITING_CADASTRE`, `WAITING_MAINTENANCE`, `VALIDATED`,
`REJECTED`, `RESOLVED`, `ARCHIVED`.

## O que nao armazenar

- raw DataFrame;
- medicoes brutas;
- Parquet;
- DuckDB;
- XLSX real;
- path real completo;
- segredo;
- credencial;
- token;
- senha;
- anexo livre no MVP.

## Como herda contexto do ANDY

O contrato herda filtros e metadados do ANDY por adaptadores:

- filtros;
- lote;
- dataset_version;
- source_fingerprint;
- ponto_id;
- source_cadence;
- variavel;
- periodo;
- filter_hash;
- query_signature.

Nenhum adaptador altera query builder, engine, export ou matematica eletrica.
