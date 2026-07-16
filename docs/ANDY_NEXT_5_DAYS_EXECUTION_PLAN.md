# ANDY Next 5 Days Execution Plan

## Premissas

- Data-base: 2026-07-10.
- Jornada: 08:00-12:00 e 14:00-16:00.
- Capacidade: 6h/dia.
- Snowflake bloqueado.
- Prioridade operacional: Threads/Ocorrencias.
- Engine Python permanece fonte da verdade.
- Nenhum provider real sera ativado sem config privada e aceite humano.

## Objetivo dos 5 dias

Ao final dos 5 dias, o ANDY deve ter uma base local testavel para:

- ocorrencias tecnicas;
- encaminhamento auditavel sem envio real;
- feedback CAPTCHA;
- labels para IA;
- readiness Snowflake organizado;
- demo interna sintetica.

## Dia 1 - Estado, higiene e dominio de Ocorrencias

Meta:

- congelar estado real;
- proteger a arvore;
- implementar ou preparar dominio de Ocorrencias.

Entregaveis:

- `docs/ANDY_EXECUTION_STATE_2026_07_10.md`
- `docs/ANDY_THREADS_OCCURRENCES_ROADMAP.md`
- `andy_threads/occurrences.py`
- `tests/test_andy_threads_occurrences.py`

Criterios de pronto:

- staged continua controlado;
- ocorrencia exige referencia tecnica;
- status aberta/em andamento/finalizada/encaminhada existem;
- testes de dominio passam.

## Dia 2 - Store, audit e policy de Ocorrencias

Meta:

- persistir ocorrencias;
- auditar transicoes;
- buscar por status, setor e referencia.

Entregaveis:

- extensao segura de `andy_threads/store.py` ou novo `occurrence_store.py`;
- audit events de ocorrencia;
- policy deny-by-default para leitura/escrita;
- `scripts/check_andy_threads_occurrences.py`.

Criterios de pronto:

- cria/lista/fecha ocorrencia;
- registra transicao de status;
- nao salva dado bruto;
- usuario sem escopo e negado.

## Dia 3 - Encaminhamento sem provider real

Meta:

- transformar ocorrencia em encaminhamento tecnico para setor responsavel.

Entregaveis:

- `andy_threads/notification_intent.py`;
- templates redigidos para e-mail/setor;
- export Markdown/JSON;
- docs de seguranca de encaminhamento.

Criterios de pronto:

- gera assunto/corpo redigido;
- provider real permanece desligado;
- nao contem secret, path completo ou dado bruto;
- tests passam.

## Dia 4 - Feedback CAPTCHA e labels para IA

Meta:

- registrar validacao humana como base supervisionada futura.

Entregaveis:

- `andy_threads/feedback.py`;
- schema de labels;
- derivacao de `training_label`;
- `docs/ANDY_HUMAN_FEEDBACK_CAPTCHA_SCHEMA.md`;
- tests de falso positivo/inconclusivo.

Criterios de pronto:

- feedback fica ligado a `occurrence_id`, `thread_id` e `reference_key`;
- falso positivo nunca vira positivo;
- manobra sem SCADA fica como candidato ou humano-confirmado, nao operacional-confirmado;
- export supervisionado sintetico.

## Dia 5 - BI/Snowflake readiness, manobras e demo interna

Meta:

- consolidar bloqueios Snowflake;
- amarrar PDF/centroide com labels humanos;
- preparar demo sintetica.

Entregaveis:

- `docs/ANDY_BI_SNOWFLAKE_BLOCKER_CHECKLIST.md`;
- spec de detector candidato de manobras;
- demo local com ocorrencias e feedback;
- relatorio semanal;
- prompt da proxima semana.

Criterios de pronto:

- Snowflake segue NO-GO sem config real;
- detector de manobras nao promete precisao sem rotulos;
- demo gera ocorrencia, encaminhamento e feedback;
- gates Threads passam.

## Sequencia diaria sugerida

### Bloco 08:00-10:00

Implementacao de dominio/codigo.

### Bloco 10:00-12:00

Testes, gates e documentacao de contrato.

### Bloco 14:00-16:00

Integracao leve, relatorio, prompts e fechamento de residuos.

## Gates diarios minimos

- `git status --short`
- `py -3.12 -m pytest tests\test_andy_threads_*.py tests\test_desktop_thread_service.py -q`
- `py -3.12 scripts\check_andy_threads_readiness.py`
- `py -3.12 scripts\check_andy_git_safety.py`
- `py -3.12 scripts\check_andy_tracked_safety.py`

Se mexer em BI:

- `py -3.12 scripts\check_andy_bi_readiness.py`
- `py -3.12 scripts\check_andy_bi_corporate_config_review.py`

## Criterio de sucesso da semana

Status alvo:

- Threads/Ocorrencias: GO local MVP.
- Feedback CAPTCHA: GO com labels sinteticos.
- IA/Manobras: PARTIAL, com candidato e rotulos necessarios documentados.
- BI/Snowflake: PARTIAL, com blocker checklist pronto.
- Publicacao corporativa: NO-GO ate aceite.

## Riscos principais

- Escopo virar chat generico.
- Humano confirmar sem evidencia.
- Falso positivo contaminar base de treino.
- Manobra conceitual ser vendida como detector operacional.
- Tree hygiene quebrar commits futuros.
- Snowflake destravar sem policy/RLS definida.
