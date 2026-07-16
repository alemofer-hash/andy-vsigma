# ANDY Human Feedback CAPTCHA Schema

## Objetivo

Definir um contrato testavel para feedback humano sobre analises do ANDY.

Esse feedback funciona como CAPTCHA tecnico: um humano qualificado confirma se
a deteccao/diagnostico do ANDY estava correto, incorreto, incompleto,
inconclusivo ou se precisa de outro setor.

## Lei do schema

Feedback humano nao altera a matematica da engine.

Ele registra:

- validacao;
- motivo;
- setor;
- evidencia;
- label supervisionado futuro.

## Entidade: HumanFeedbackCaptcha

Campos obrigatorios:

| Campo | Tipo | Obrigatorio | Descricao |
|---|---|---|---|
| `feedback_id` | string | Sim | UUID/hash do feedback |
| `analysis_id` | string | Sim | ID da analise/ocorrencia |
| `occurrence_id` | string | Sim | Ocorrencia vinculada |
| `thread_id` | string | Sim | Thread vinculada |
| `reference_key` | string | Sim | Referencia tecnica do recorte |
| `event_type` | enum | Sim | Tipo detectado/candidato |
| `human_verdict` | enum | Sim | Veredito humano |
| `confidence_human` | float | Sim | Confianca do humano, 0.0 a 1.0 |
| `reason_code` | enum | Sim | Motivo principal |
| `target_sector` | enum | Sim | Setor dono ou proximo setor |
| `evidence_ref` | string | Sim | Hash/ID de evidencia redigida |
| `reviewer_subject` | string | Sim | Usuario/ator redigido ou mock |
| `reviewer_sector` | enum | Sim | Setor do avaliador |
| `created_at` | datetime | Sim | Timestamp UTC |
| `model_version` | string | Nao | Versao do detector, se houver |
| `engine_version` | string | Nao | Versao da engine ANDY |
| `notes_redacted` | string | Nao | Comentario sem dado sensivel |

## EventType

- `POWER_INVERSION`
- `SWITCHING_EVENT`
- `LOAD_FLOW_ANOMALY`
- `MEASUREMENT_GAP`
- `MEASUREMENT_SUSPECT`
- `CADASTRE_MAPPING`
- `EXPORT_DASHBOARD`
- `BI_DATASET`
- `TOOL_RUNTIME`
- `INCONCLUSIVE`

## HumanVerdict

- `CORRECT`
- `FALSE_POSITIVE`
- `INCOMPLETE`
- `INCONCLUSIVE`
- `NEEDS_OTHER_SECTOR`
- `NOT_ENOUGH_EVIDENCE`

## ReasonCode

- `SCADA_CONFIRMS`
- `SCADA_DOES_NOT_CONFIRM`
- `MEASUREMENT_BAD_QUALITY`
- `MISSING_MEASUREMENT`
- `CADASTRE_MISMATCH`
- `PLANNED_WORK`
- `OPERATIONAL_SWITCHING`
- `LOAD_BEHAVIOR_EXPECTED`
- `EXPORT_OR_QUERY_ERROR`
- `NO_EVIDENCE`
- `OTHER`

## TargetSector

- `ENGINEERING`
- `OPERATION`
- `MEASUREMENT_DATA`
- `CADASTRE_ASSETS`
- `PROTECTION_AUTOMATION`
- `WORKS_MAINTENANCE`
- `IT_BI_DATA`
- `MANAGEMENT`

## TrainingLabel derivado

O label para IA deve ser derivado, nunca digitado livremente.

| Condicao | `training_label` |
|---|---|
| `human_verdict=CORRECT` e `reason_code=SCADA_CONFIRMS` | `positive_scada_confirmed` |
| `human_verdict=CORRECT` sem SCADA | `positive_human_confirmed` |
| `human_verdict=FALSE_POSITIVE` | `negative_false_positive` |
| `human_verdict=INCOMPLETE` | `partial_incomplete` |
| `human_verdict=INCONCLUSIVE` | `unknown_inconclusive` |
| `human_verdict=NEEDS_OTHER_SECTOR` | `routed_needs_sector` |
| `human_verdict=NOT_ENOUGH_EVIDENCE` | `unknown_no_evidence` |

## Uso para inversao de fluxo

Para `POWER_INVERSION`, campos recomendados em `evidence_ref`:

- hash do recorte;
- periodo;
- SE;
- alimentador/BAY;
- equipamento;
- terminal;
- variavel;
- FP assinado;
- MW/MVA;
- status de inversao;
- export/dashboard de origem;
- versao da engine.

Regra:

- Inversao confirmada por engenharia sem SCADA vira `positive_human_confirmed`.
- Inversao confirmada por Operacao/SCADA vira `positive_scada_confirmed`.
- Falso positivo nunca entra como positivo.

## Uso para manobras

Para `SWITCHING_EVENT`, o schema deve respeitar o PDF do Teorema do Centroide:

Validado/confiavel para MVP:

- deslocamento de centroide como candidato/anomalia estatistica;
- limiar estatistico como triagem;
- interpretabilidade geometrica.

Conceitual/nao operacional ainda:

- Actor-Critic treinado em topologia real;
- ICM multi-alimentador com validacao real;
- classificacao global/local/ilhamento;
- sensibilidade FV operacional.

Obrigatorio para promover para detector operacional:

- rotulos SCADA com timestamp;
- registros de disjuntor/religador;
- eventos manuais anotados por Operacao;
- medicoes sincronizadas multi-alimentador;
- validacao com metricas de precisao, revocacao e F1.

## Regras de seguranca

- Nao salvar medicao bruta.
- Nao salvar path corporativo completo.
- Nao salvar segredo/token.
- Nao converter missing para zero.
- Nao tratar confidence neural como verdade.
- Nao usar label inconclusivo como positivo.
- Nao treinar com dado real versionado no Git.

## Exemplo JSON

```json
{
  "feedback_id": "fb_SYN_001",
  "analysis_id": "analysis_SYN_001",
  "occurrence_id": "occ_SYN_001",
  "thread_id": "thread_SYN_001",
  "reference_key": "VARIABLE:synthetic",
  "event_type": "POWER_INVERSION",
  "human_verdict": "FALSE_POSITIVE",
  "confidence_human": 0.9,
  "reason_code": "MEASUREMENT_BAD_QUALITY",
  "target_sector": "MEASUREMENT_DATA",
  "evidence_ref": "evidence_hash_SYN",
  "reviewer_subject": "mock.engineer",
  "reviewer_sector": "ENGINEERING",
  "created_at": "2026-07-10T12:00:00Z",
  "training_label": "negative_false_positive",
  "notes_redacted": "Recorte sintetico; medicao suspeita antes de confirmar evento."
}
```

## Testes esperados

- rejeita feedback sem `reference_key`;
- rejeita `confidence_human` fora de 0.0-1.0;
- rejeita `CORRECT` sem setor/reviewer;
- deriva label corretamente;
- `FALSE_POSITIVE` nunca vira positivo;
- `INCONCLUSIVE` nunca vira positivo;
- manobra sem evidencia SCADA fica no maximo como candidato humano, nao confirmado operacional.
