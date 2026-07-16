# ANDY Threads Session 04 - Event Candidates

Data-base: 2026-07-10

## Status

GO tecnico para camada experimental/proposal-only.

## Objetivo

Executar o Prompt 6: criar uma camada segura para candidatos de
manobra/inversao baseada em sinais estatisticos, Teorema do Centroide e feedback
humano CAPTCHA, sem treinar rede final e sem tomar decisao operacional.

## Arquivos criados

- `andy_threads/event_candidates.py`
- `scripts/check_andy_threads_event_candidates.py`
- `tests/test_andy_threads_event_candidates.py`
- `docs/ANDY_SWITCHING_DETECTION_CONCEPT_BOUNDARIES.md`
- `docs/ANDY_THREADS_SESSION_04_EVENT_CANDIDATES_REPORT.md`

## Arquivos modificados

- `andy_threads/__init__.py`
- `scripts/check_andy_threads_readiness.py`
- `docs/ANDY_THREADS_DATA_CONTRACT.md`
- `docs/ANDY_THREADS_OCCURRENCES_ROADMAP.md`
- `docs/ANDY_HUMAN_FEEDBACK_CAPTCHA_SCHEMA.md`

## Garantias implementadas

- candidato estatistico fica `STATISTICAL_CANDIDATE`;
- humano sem SCADA fica `HUMAN_CONFIRMED`, nao operacional;
- SCADA confirmada fica `OPERATIONAL_SCADA_CONFIRMED`;
- falso positivo fica `FALSE_POSITIVE` e `REJECTED`;
- cadastro/roteamento setorial fica `HUMAN_REVIEWED`;
- Actor-Critic/ICM ficam `CONCEPTUAL_ONLY` e `QUARANTINED`;
- `decision_applied=true` e rejeitado;
- score fora de 0..1 e rejeitado;
- candidato SCADA confirmado exige `SCADA_LABEL`.

## Comandos executados

```powershell
py -3.12 -m py_compile andy_threads\event_candidates.py andy_threads\__init__.py scripts\check_andy_threads_event_candidates.py tests\test_andy_threads_event_candidates.py
py -3.12 -m pytest tests\test_andy_threads_event_candidates.py -q
py -3.12 scripts\check_andy_threads_event_candidates.py
py -3.12 scripts\check_andy_threads_readiness.py
py -3.12 -m pytest tests\test_andy_threads_models.py tests\test_andy_threads_references.py tests\test_andy_threads_responsibility.py tests\test_andy_threads_policy.py tests\test_andy_threads_store.py tests\test_andy_threads_audit.py tests\test_andy_threads_context.py tests\test_andy_threads_emergency.py tests\test_andy_threads_sector_lens.py tests\test_andy_threads_sector_acceptance.py tests\test_andy_threads_future_boundaries.py tests\test_andy_threads_occurrences.py tests\test_andy_threads_occurrence_store.py tests\test_andy_threads_occurrence_policy.py tests\test_andy_threads_notification_intent.py tests\test_andy_threads_feedback.py tests\test_andy_threads_event_candidates.py -q
git diff --check -- andy_threads\event_candidates.py andy_threads\__init__.py scripts\check_andy_threads_event_candidates.py scripts\check_andy_threads_readiness.py tests\test_andy_threads_event_candidates.py docs\ANDY_SWITCHING_DETECTION_CONCEPT_BOUNDARIES.md docs\ANDY_THREADS_DATA_CONTRACT.md docs\ANDY_THREADS_OCCURRENCES_ROADMAP.md docs\ANDY_HUMAN_FEEDBACK_CAPTCHA_SCHEMA.md
py -3.12 scripts\check_andy_git_safety.py
py -3.12 scripts\check_andy_tracked_safety.py
py -3.12 scripts\check_reports_hygiene.py
```

## Resultados

- teste focado: `11 passed`;
- suite Threads: `73 passed`;
- `check_andy_threads_event_candidates.py`: passed;
- `check_andy_threads_readiness.py`: passed;
- `check_andy_git_safety.py`: passed, `Staged files: 0`;
- `check_andy_tracked_safety.py`: passed;
- `check_reports_hygiene.py`: passed;
- `git diff --check` no escopo do Prompt 6: sem falhas.

## Residuos

- A arvore geral continua suja por fases anteriores.
- Os arquivos de Threads ainda estao unstaged para revisao humana.
- Reports em `reports/` foram atualizados pelos gates e continuam como outputs.
- Detector operacional real continua bloqueado por falta de rotulos SCADA,
  registros operacionais e validacao multi-setorial.

## Proximo passo recomendado

Executar o Prompt 7: demo interna + relatorio semanal, usando candidatos e
feedbacks sinteticos para demonstrar o ciclo ocorrencia -> candidato ->
CAPTCHA -> estado auditavel.
