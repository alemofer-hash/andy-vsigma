# ANDY Threads Demo Scenarios 001

Data-base: 2026-07-10

## Objetivo

Gerar cinco cenarios sinteticos setoriais para revisao humana antes de qualquer
evolucao para UI operacional ou store corporativo multiusuario.

Esta task expande a demo unica de Threads/Ocorrencias para pacotes Markdown
separados por tipo de problema.

## Comando

```powershell
py -3.12 scripts\run_andy_threads_demo_scenarios.py
```

## Saida local

Os arquivos sao gerados em:

```text
.validation_tmp/andy_threads_demo_scenarios/
```

Arquivos principais:

- `ANDY_THREADS_DEMO_SCENARIOS_001_INDEX.md`
- `ANDY_THREADS_DEMO_SCENARIOS_001_INDEX.json`
- `scenarios/scenario_01_power_inversion_pq.md`
- `scenarios/scenario_02_scada_switching.md`
- `scenarios/scenario_03_measurement_gap_cadence.md`
- `scenarios/scenario_04_cadastre_terminal_mismatch.md`
- `scenarios/scenario_05_export_bi_dataset.md`

Esses outputs sao gerados para revisao local e nao devem ser commitados.

## Cenários gerados

| Cenario | Setor dono | Setor destino | Objetivo |
|---|---|---|---|
| 01 - Inversao P/Q | Engenharia | Operacao | Validar candidato de inversao sem confirmacao automatica |
| 02 - Manobra SCADA | Operacao | Protecao/Automacao/SCADA | Validar promocao operacional somente com SCADA |
| 03 - Lacuna/cadencia | Medicao/Dados | Medicao/Dados | Separar problema de dado de problema eletrico |
| 04 - Cadastro/terminal | Cadastro/Ativos | Cadastro/Ativos | Separar erro de cadastro de evento de rede |
| 05 - Export/BI | TI/BI | TI/BI | Separar falha de ferramenta/dataset de campo |

## Estados esperados

| Cenario | Estado esperado |
|---|---|
| Inversao P/Q | `HUMAN_CONFIRMED`, nao operacional |
| Manobra SCADA | `SCADA_CONFIRMED`, operacionalmente confirmado |
| Lacuna/cadencia | `PARTIAL_INCOMPLETE` como diagnostico |
| Cadastro/terminal | `HUMAN_REVIEWED`, sem SCADA |
| Export/BI | `PARTIAL_INCOMPLETE` como diagnostico |

## Regras de seguranca

- Usar apenas dados sinteticos.
- Nao abrir fonte corporativa.
- Nao enviar e-mail/Teams real.
- Nao criar ticket real.
- Nao treinar rede neural.
- Nao aplicar decisao operacional.
- Nao versionar outputs de `.validation_tmp`.

## Como revisar

1. Abrir `ANDY_THREADS_DEMO_SCENARIOS_001_INDEX.md`.
2. Revisar cada Markdown em `scenarios/`.
3. Para cada cenario, preencher a tabela `Decisao da revisao`.
4. Classificar como `GO`, `PARTIAL` ou `NO-GO`.
5. Consolidar campos faltantes para a proxima fase.

## Criterio de pronto

Esta task e considerada pronta quando:

- os cinco pacotes Markdown existem;
- cada pacote tem ocorrencia, intent, candidato ou diagnostico, feedback e perguntas;
- provider real esta desligado;
- outputs ficam em `.validation_tmp`;
- testes passam;
- nenhum dado real e usado.

## Proximo passo

Executar revisao humana com Engenharia/Operacao e, se possivel, Medicao,
Cadastro, SCADA e TI/BI.

Somente depois da revisao:

```text
ANDY Threads UI/Store Readiness 001 - desenhar tela e persistencia corporativa com base nos campos aprovados.
```
