# ANDY Threads/Ocorrencias Roadmap

## Objetivo

Transformar ANDY Threads em uma camada de ocorrencias tecnicas contextual,
auditavel e util para engenharia emergencial.

Uma ocorrencia nao e chat generico. Ela nasce de um recorte tecnico do ANDY:

- lote;
- filtro;
- SE;
- alimentador/BAY;
- equipamento;
- terminal;
- variavel;
- periodo;
- anomalia;
- export;
- pagina BI futura;
- diagnostico do ANDY.

## Principio operacional

```text
ANDY detecta ou o engenheiro observa.
Ocorrencia nasce com referencia tecnica.
Setor responsavel recebe encaminhamento auditavel.
Humano valida como CAPTCHA.
Decisao fecha ou redireciona.
Labels alimentam base futura de IA.
```

## Escopo MVP local

Inclui:

- entidade `Occurrence`;
- status operacional;
- severidade;
- dono setorial;
- setor consultado;
- referencia tecnica obrigatoria;
- store local;
- audit trail;
- feedback CAPTCHA;
- notification intent sem envio real;
- export JSON/Markdown.

Nao inclui:

- provider real de e-mail;
- Teams/Outlook real;
- login proprio;
- store multiusuario corporativo;
- anexos livres;
- IA operacional automatica;
- escrita em fonte corporativa.

## Modelo de dominio proposto

### Occurrence

Campos minimos:

- `occurrence_id`
- `thread_id`
- `title`
- `summary`
- `status`
- `severity`
- `problem_domain`
- `reference`
- `owner_sector`
- `target_sector`
- `created_by`
- `created_at`
- `updated_at`
- `closed_at`
- `closure_reason`
- `feedback_status`

### OccurrenceStatus

- `OPEN`
- `IN_PROGRESS`
- `FORWARDED`
- `WAITING_HUMAN_FEEDBACK`
- `WAITING_OTHER_SECTOR`
- `FINALIZED`
- `REJECTED`
- `ARCHIVED`

### OccurrenceSeverity

- `S0_OBSERVATION`
- `S1_PRODUCTIVITY_BLOCKER`
- `S2_ENGINEERING_BLOCKER`
- `S3_OPERATIONAL_RISK`
- `S4_CRITICAL_DECISION_RISK`

### OccurrenceDomain

- `ELECTRICAL_PARAMETER`
- `POWER_INVERSION`
- `SWITCHING_EVENT`
- `MEASUREMENT_AVAILABILITY`
- `CADASTRE_MAPPING`
- `ANALYTIC_DIVERGENCE`
- `EXPORT_DASHBOARD`
- `BI_ACCESS`
- `TOOL_RUNTIME`

## Encaminhamento

O MVP deve criar `NotificationIntent`, nao enviar e-mail real.

Campos:

- `intent_id`
- `occurrence_id`
- `target_sector`
- `target_channel`
- `subject`
- `body_redacted`
- `reference_key`
- `created_at`
- `created_by`
- `status`

Status:

- `DRAFT`
- `READY_FOR_HUMAN_SEND`
- `SENT_EXTERNALLY_BY_HUMAN`
- `CANCELLED`

Regra:

Enquanto provider real nao estiver aprovado, o ANDY apenas gera assunto/corpo
redigido para copia humana.

## Feedback humano tipo CAPTCHA

Cada ocorrencia ligada a analise automatica deve poder receber feedback:

- correto;
- falso positivo;
- incompleto;
- inconclusivo;
- precisa outro setor.

Esse feedback nao recalcula a engine. Ele registra label supervisionado para
avaliacao futura.

## Roadmap de implementacao

### O1 - Domain core de Ocorrencias

Entregas:

- `andy_threads/occurrences.py`
- dataclasses/enums;
- validadores;
- testes unitarios.

Pronto quando:

- ocorrencia sem referencia tecnica e rejeitada;
- S3/S4 exigem contexto e decisao posterior;
- status de ciclo de vida sao validos.

### O2 - Store/audit/policy

Entregas:

- tabelas SQLite para ocorrencias;
- eventos de auditoria;
- busca por referencia/status/setor;
- policy deny-by-default.

Pronto quando:

- cria/lista/fecha ocorrencia;
- audita cada transicao;
- nao armazena dados brutos.

### O3 - Encaminhamento

Entregas:

- `NotificationIntent`;
- template de e-mail redigido;
- export Markdown/JSON;
- check de nao envio real.

Pronto quando:

- uma ocorrencia gera encaminhamento para setor responsavel;
- provider real permanece desativado;
- texto nao contem secrets/path completo/dado bruto.

### O4 - Feedback CAPTCHA

Entregas:

- schema de feedback;
- labels de treino;
- validacao de campos;
- export supervisionado.

Pronto quando:

- feedback humano fecha ou redireciona ocorrencia;
- label fica conectado a `analysis_id`, `reference_key` e `evidence_hash`;
- falso positivo e inconclusivo nao viram positivo.

### O5 - Painel Desktop

Entregas:

- aba/painel `Ocorrencias`;
- listas: abertas, em andamento, finalizadas, encaminhadas;
- criar a partir do recorte;
- ver historico;
- registrar feedback.

Pronto quando:

- operador cria ocorrencia em menos de 20s;
- historico reaparece no mesmo recorte;
- status e dono ficam claros.

### O6 - Demo e tabletop

Entregas:

- cenarios sinteticos;
- runbook;
- relatorio semanal;
- checklist de aceite setorial.

Pronto quando:

- pelo menos 5 cenarios geram ocorrencia e feedback;
- as lacunas para Operacao/SCADA/TI ficam explicitadas.

## Perguntas bloqueadoras

### TI/BI

- Qual canal oficial para encaminhamento: e-mail, Teams, sistema de chamados ou nenhum?
- Ha permissao para gerar e-mail automatico no futuro?
- Qual store corporativo aprovado para multiusuario?
- Qual politica de retencao de ocorrencias tecnicas?

### Operacao/SCADA

- Existem registros com timestamp de manobras, disjuntores ou religadores?
- Quem pode confirmar evento operacional?
- O que deve ser considerado evidencia minima de manobra?

### Engenharia

- Quais diagnosticos do ANDY exigem validacao humana antes de uso em BI?
- Quais casos podem ser fechados pela engenharia?
- Quais campos sao obrigatorios para analisar inversao/fluxo?

### Medicao/Cadastro

- Quem valida lacuna/cadencia/ponto errado?
- Quem valida equipamento/terminal/alimentador incorreto?
- Quais nomenclaturas oficiais devem entrar no contrato?
