# ANDY Threads/Ocorrencias Demo Runbook

Data-base: 2026-07-10

## Objetivo

Executar uma demo local, sintetica e auditavel do ciclo:

```text
ocorrencia -> notification intent -> event candidate -> feedback CAPTCHA -> resumo redigido
```

Essa demo existe para validar o fluxo de comunicacao tecnica emergencial sem
usar dado real, provider real, e-mail real, Teams real, SCADA real ou rede
corporativa.

## Comando

```powershell
py -3.12 scripts\run_andy_threads_occurrences_demo.py
```

Saida padrao:

```text
ANDY Threads occurrences demo: passed
status=GO
data_class=synthetic
real_provider_enabled=false
occurrence_id=occ-demo-threads-001
notification_intent_status=READY_FOR_HUMAN_SEND
candidate_status=HUMAN_CONFIRMED
feedback_label=positive_human_confirmed
```

## Outputs locais

A demo escreve apenas em:

```text
.validation_tmp/andy_threads_occurrences_demo/
```

Arquivos esperados:

- `threads_occurrences_demo.sqlite`
- `andy_threads_occurrences_demo.json`
- `andy_threads_occurrences_demo.md`

Esses arquivos sao outputs de validacao local. Nao devem ser commitados.

## O que a demo prova

- cria uma `Occurrence` sintetica vinculada a recorte tecnico;
- encaminha via `NotificationIntent` sem envio real;
- cria `EventCandidate` por sinal de centroide;
- registra `HumanFeedbackCaptcha`;
- transforma feedback em label supervisionado futuro;
- exporta resumo redigido;
- mantem a confirmacao operacional desligada porque nao ha SCADA.

## O que a demo nao prova

- nao prova detector operacional de manobra;
- nao prova acesso SCADA;
- nao prova integracao e-mail/Teams;
- nao prova store multiusuario;
- nao prova BI/Snowflake;
- nao treina rede neural;
- nao altera engine Python.

## Checklist de aceite humano

| Item | Esperado |
|---|---|
| Ocorrencia criada | `occ-demo-threads-001` |
| Intent criado | `READY_FOR_HUMAN_SEND` |
| Provider real | `false` |
| Candidato | `HUMAN_CONFIRMED` |
| Validacao operacional | `false` |
| Feedback | `positive_human_confirmed` |
| Dados reais | nenhum |
| Escrita corporativa | nenhuma |

## Proxima demonstracao ideal

Executar uma sessao guiada com Engenharia/Operacao usando apenas recortes
sinteticos e perguntas:

- a ocorrencia tem contexto suficiente?
- o setor destino esta correto?
- o texto de encaminhamento e claro?
- o feedback CAPTCHA cobre as respostas reais do operador?
- quais campos faltam para aceitar um caso real?
