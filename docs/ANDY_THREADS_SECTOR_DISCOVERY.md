# ANDY Threads Sector Discovery

## Objetivo

Este documento organiza perguntas para entender como cada setor enxerga uma
medicao, quando deve entrar em uma thread e que contexto minimo precisa para
agir.

## Perguntas universais

1. Quando voce olha uma medicao, o que esta tentando descobrir?
2. Que variaveis importam para sua rotina?
3. Que problema voce consegue resolver sozinho?
4. Que problema precisa repassar?
5. Que informacao minima precisa para agir?
6. Quais filtros do ANDY usa?
7. Quais erros ve com frequencia?
8. Quando uma analise termina?
9. Quem deveria ser consultado?
10. O que seria ruido em uma thread?

## Engenharia

- Como identifica fluxo de carga anomalo?
- Como avalia inversao de fluxo?
- Que contexto precisa para validar patamar?
- Como diferencia evento real de erro de cadastro/medicao?
- Quais campos minimos: SE, bay/alimentador, equipamento, terminal, variavel,
  periodo, lote, cadencia?

## Operacao

- Que evidencias confirmam manobra ou chaveamento?
- Que evento operacional deve virar decisao?
- Quando Engenharia deve ser consultada?
- Quando uma thread pode ser encerrada por Operacao?

## Medicao / Telemetria / Qualidade de Dados

- Como identifica lacuna de medicao?
- Como valida cadencia 15 em 15 ou hora em hora?
- Que variavel/ponto e confiavel?
- Quando a falha e da fonte e nao do ANDY?

## Cadastro / Ativos / GIS

- Como confirmar vinculo terminal/equipamento/alimentador?
- Quais aliases ou codigos geram ambiguidade?
- Quando uma thread indica erro de cadastro?
- Que evidencia permite encerrar uma duvida de mapeamento?

## Protecao / Automacao / SCADA

- Que sinais de SCADA precisam entrar como contexto?
- Quando uma falha de supervisao afeta interpretacao de medicao?
- Como relacionar rele, evento e leitura?

## Obras / Manutencao

- Que intervencao pode explicar mudanca de perfil?
- Como registrar impacto pos-obra?
- Quem confirma termino de intervencao?

## TI / Dados / BI

- Que problema e de dataset, refresh, workspace ou RLS?
- Que dado de auditoria precisa aparecer no BI?
- Como testar acesso por perfil?
- Que divergencia entre Desktop e BI bloqueia publicacao?

## Gestao

- Que resumo e necessario para acompanhar risco?
- Que indicadores precisam ser confiaveis antes de decisao?
- Que detalhe tecnico deve ficar disponivel sob demanda?
