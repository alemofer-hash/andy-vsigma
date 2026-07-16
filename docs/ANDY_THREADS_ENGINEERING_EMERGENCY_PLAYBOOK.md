# ANDY Threads Engineering Emergency Playbook

## Objetivo

Definir como usar ANDY Threads para reduzir atraso de comunicacao quando uma
analise, export, dashboard ou software depende de parametros eletricos que
podem estar incorretos, indisponiveis ou ambiguos.

## Severidade

| Severidade | Uso | Triagem | Primeira resposta | Decisao alvo |
|---|---|---:|---:|---:|
| S0_OBSERVATION | observacao sem bloqueio | 240 min | 480 min | sem alvo |
| S1_PRODUCTIVITY_BLOCKER | atrasa trabalho individual | 120 min | 240 min | 1440 min |
| S2_ENGINEERING_BLOCKER | bloqueia analise de engenharia | 60 min | 120 min | 480 min |
| S3_OPERATIONAL_RISK | pode afetar interpretacao operacional | 30 min | 60 min | 240 min |
| S4_CRITICAL_DECISION_RISK | pode afetar decisao critica | 15 min | 30 min | 120 min |

## Roteamento inicial

| Dominio | Tipo de thread | Dono | Consultados |
|---|---|---|---|
| Parametro eletrico | LOAD_FLOW_ANOMALY | Engenharia | Medicao/Dados, Cadastro, Operacao |
| Disponibilidade de medicao | MEASUREMENT_GAP | Medicao/Dados | Engenharia, TI/BI |
| Cadastro/mapeamento | TERMINAL_MAPPING | Cadastro/Ativos | Engenharia, Medicao/Dados |
| Divergencia analitica | PARITY_DESKTOP_BI | Engenharia | TI/BI |
| Export/dashboard | GENERAL_REVIEW | Engenharia | TI/BI |
| Acesso BI/RLS | ACCESS_RLS_ISSUE | TI/BI | Gestao |
| Evento operacional | SWITCHING_EVENT | Operacao | Engenharia, Protecao/Automacao |
| Runtime/ferramenta | BI_DATASET_ISSUE | TI/BI | Engenharia |

## Fluxo recomendado

1. Abrir thread a partir do recorte tecnico.
2. Confirmar severidade.
3. Conferir dono sugerido.
4. Registrar evidencia minima.
5. Consultar setores sugeridos.
6. Criar DecisionRecord para S1 ou superior.
7. Encerrar apenas com decisao, rejeicao ou pendencia explicita.

## Evidencia minima

- lote/dataset_version quando existir;
- SE/alimentador/equipamento/terminal;
- variavel;
- periodo;
- cadencia;
- filter_hash/query_signature;
- export_id ou pagina BI, se aplicavel;
- descricao curta do impacto.

## O que nao fazer

- abrir thread sem recorte;
- copiar medicoes brutas para a thread;
- colar path corporativo completo;
- registrar senha/token;
- decidir em Teams/Outlook sem voltar a decisao para o ANDY;
- tratar estimativa como medicao validada.
