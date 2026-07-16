# ANDY Switching Detection Concept Boundaries

Data-base: 2026-07-10

## Objetivo

Definir a fronteira segura entre:

- candidato estatistico de manobra/inversao;
- confirmacao humana;
- confirmacao operacional por SCADA;
- conceitos ainda experimentais para treinamento futuro.

Esta fase nao implementa detector operacional de manobra. Ela cria apenas a
camada `proposal-only` em `andy_threads/event_candidates.py`, para registrar
candidatos e receber labels humanos do schema CAPTCHA.

## Lei operacional

Nenhum candidato de evento pode virar decisao operacional automatica.

O fluxo correto e:

```text
ANDY sinaliza candidate_event
-> humano revisa no recorte tecnico
-> SCADA/operacao/cadastro/medicao confirma ou rejeita
-> label supervisionado fica auditavel
-> modelo futuro pode ser treinado depois
```

## Base conceitual do PDF

O PDF do Teorema do Centroide descreve uma arquitetura com:

- deslocamento de centroide como sinal geometrico interpretavel;
- limiar estatistico para triagem de eventos;
- Actor-Critic para estimativa/decisao em cenarios futuros;
- ICM/multi-alimentador para correlacao entre alimentadores;
- necessidade de rotulos operacionais e validacao multi-fonte.

Para o ANDY Threads, a leitura segura e:

| Elemento | Status no ANDY agora | Uso permitido |
|---|---|---|
| Deslocamento de centroide | MVP-safe como sinal estatistico | Criar `CENTROID_DISPLACEMENT_ANOMALY` |
| Threshold estatistico | MVP-safe como triagem | Criar candidato, nunca confirmar sozinho |
| Inversao de fluxo ja analisada pela engine | Proposal-only | Criar `POWER_INVERSION_CANDIDATE` |
| Actor-Critic | Conceitual | Quarentena como `ACTOR_CRITIC_CONCEPT` |
| ICM multi-alimentador | Conceitual | Quarentena como `MULTI_FEEDER_CORRELATION_CONCEPT` |
| Classificacao global/local/ilhamento | Nao operacional | Exige rotulos SCADA e validacao futura |

## Estados do candidato

`EventCandidateStatus` separa revisao e confirmacao:

- `CANDIDATE`: sinal estatistico ou proposta da engine;
- `HUMAN_REVIEWED`: revisado, mas sem confirmacao suficiente;
- `HUMAN_CONFIRMED`: humano validou o recorte, sem SCADA;
- `SCADA_CONFIRMED`: SCADA/automacao confirmou o evento;
- `FALSE_POSITIVE`: humano/SCADA rejeitou como falso positivo;
- `INCONCLUSIVE`: evidencia insuficiente;
- `REJECTED`: descartado;
- `QUARANTINED`: conceito ou evidencia que nao pode operar.

## Niveis de validacao

`EventValidationLevel` define o quanto o candidato pode ser usado:

- `STATISTICAL_CANDIDATE`: pode entrar em fila de revisao;
- `HUMAN_CONFIRMED`: bom para aprendizagem supervisionada futura;
- `OPERATIONAL_SCADA_CONFIRMED`: unico estado operacionalmente confirmado;
- `CONCEPTUAL_ONLY`: nao usar em operacao;
- `REJECTED`: usar como negativo supervisionado.

## Evidencias por setor

| Setor | Papel esperado | Estado resultante |
|---|---|---|
| Engenharia | confirma coerencia eletrica do recorte | `HUMAN_CONFIRMED` |
| Operacao | confirma manobra observada ou planejada | `HUMAN_CONFIRMED` ou `SCADA_CONFIRMED` se houver SCADA |
| Protecao/Automacao/SCADA | fornece rotulo operacional | `SCADA_CONFIRMED` |
| Medicao/Dados | confirma qualidade, lacuna ou falha de medicao | `FALSE_POSITIVE`, `INCONCLUSIVE` ou `HUMAN_REVIEWED` |
| Cadastro/Ativos | confirma erro de mapeamento ou terminal | `FALSE_POSITIVE`, `INCONCLUSIVE` ou `HUMAN_REVIEWED` |

## Contrato implementado

Arquivo:

- `andy_threads/event_candidates.py`

Entidades:

- `EventCandidate`;
- `EventCandidateType`;
- `EventCandidateStatus`;
- `EventEvidenceSource`;
- `EventValidationLevel`.

Funcoes:

- `create_centroid_candidate(...)`;
- `create_power_inversion_candidate(...)`;
- `create_conceptual_actor_critic_candidate(...)`;
- `apply_feedback_to_candidate(...)`;
- `export_event_candidate_dataset(...)`.

Garantias:

- score deve ficar entre 0 e 1;
- `decision_applied=True` e rejeitado;
- candidato conceitual fica `QUARANTINED` e `CONCEPTUAL_ONLY`;
- `SCADA_CONFIRMED` exige `SCADA_LABEL`;
- `OPERATIONAL_SCADA_CONFIRMED` exige `SCADA_CONFIRMED`;
- feedback com falso positivo vira `REJECTED`;
- feedback inconclusivo nao vira positivo;
- feedback humano sem SCADA nao vira operacional.

## Relação com CAPTCHA humano

`andy_threads/feedback.py` continua sendo a fonte dos labels humanos:

- `positive_scada_confirmed`;
- `positive_human_confirmed`;
- `negative_false_positive`;
- `partial_incomplete`;
- `unknown_inconclusive`;
- `routed_needs_sector`;
- `unknown_no_evidence`.

Esses labels alimentam dataset futuro de treinamento, mas a fase atual nao
treina rede neural, nao ajusta pesos e nao publica modelo.

## O que ainda falta para detector operacional

Antes de qualquer uso operacional de manobras, ainda faltam:

- rotulos SCADA com timestamp;
- registros de disjuntor/religador;
- eventos manuais anotados por Operacao;
- medicoes sincronizadas multi-alimentador;
- validacao por Engenharia, Operacao, Medicao, Cadastro e SCADA;
- metricas precision, recall, F1, ROC/AUC por classe de evento;
- politica de falso positivo e falso negativo;
- runbook de revisao humana e rollback.

## Nao-objetivos desta fase

- nao alterar engine Python;
- nao alterar calculos de FP, MW, MVA, fluxo P/Q ou patamar;
- nao treinar rede final;
- nao criar decisao automatica;
- nao integrar SCADA real;
- nao publicar dados reais;
- nao criar painel operacional de manobra.

## Criterio de aceite

O Prompt 6 e aceito quando:

- candidatos estatisticos ficam separados de evento confirmado;
- SCADA, humano, medicao e cadastro produzem estados diferentes;
- Actor-Critic/ICM ficam conceituais e quarantined;
- labels CAPTCHA alimentam dataset futuro sem treinar rede final;
- testes e gate `scripts/check_andy_threads_event_candidates.py` passam.
