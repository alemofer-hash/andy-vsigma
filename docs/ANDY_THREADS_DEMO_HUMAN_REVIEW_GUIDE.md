# ANDY Threads Demo Human Review Guide

Data-base: 2026-07-10

## Objetivo

Guiar uma revisao humana da demo sintetica de Threads/Ocorrencias com
Engenharia e Operacao, usando o Markdown gerado pela demo como artefato de
discussao.

O objetivo nao e validar UI, store corporativo, envio real ou detector
operacional. O objetivo e validar se a comunicacao tecnica esta clara o
suficiente para reduzir atraso operacional.

Fluxo revisado:

```text
ocorrencia sintetica
-> notification intent
-> candidato de evento
-> feedback CAPTCHA
-> resumo redigido
```

## Artefato base da revisao

Usar o Markdown gerado localmente pela demo:

```text
.validation_tmp/andy_threads_occurrences_demo/andy_threads_occurrences_demo.md
```

Se o arquivo nao existir no workspace local, reexecutar a demo somente quando o
script estiver disponivel:

```powershell
py -3.12 scripts\run_andy_threads_occurrences_demo.py
```

Regras:

- usar apenas dados sinteticos;
- nao anexar dado real;
- nao enviar e-mail real;
- nao acionar Teams/provider real;
- nao copiar path corporativo sensivel;
- nao tratar candidato como evento confirmado.

## Participantes recomendados

Minimo:

- Engenharia;
- Operacao.

Ideal para a segunda rodada:

- Medicao/Dados;
- Cadastro/Ativos;
- Protecao/Automacao/SCADA;
- TI/BI;
- Gestao, apenas para leitura de indicadores e prioridade.

## Preparacao antes da sessao

Responsavel tecnico deve preparar:

1. Abrir o Markdown da demo.
2. Confirmar que o texto diz `synthetic`.
3. Confirmar que `Provider real` esta `disabled`.
4. Confirmar que `Candidate status` nao esta `SCADA_CONFIRMED`.
5. Confirmar que nao ha path real, segredo, e-mail real ou medicao bruta.
6. Separar uma copia visual ou leitura em tela para os participantes.

Checklist previo:

| Item | Esperado | OK |
|---|---|---|
| Demo usa dados sinteticos | Sim |  |
| Provider real desligado | Sim |  |
| Evento operacional automatico | Nao |  |
| Candidato separado de confirmado | Sim |  |
| Feedback CAPTCHA aparece | Sim |  |
| Texto redigido e claro | A revisar |  |

## Roteiro de sessao de 45 minutos

### 1. Abertura - 5 min

Explicar a premissa:

```text
ANDY nao esta decidindo uma manobra.
ANDY esta criando um recorte tecnico para comunicacao e revisao humana.
```

Alinhar que o objetivo da reuniao e avaliar linguagem, contexto e roteamento.

### 2. Leitura do Markdown - 10 min

Ler o resumo exatamente como esta gerado.

Perguntas:

- O titulo da ocorrencia deixa claro o problema?
- O status e compreensivel para Engenharia?
- O status e compreensivel para Operacao?
- O texto deixa claro que e candidato, nao confirmacao?
- Falta periodo, SE, alimentador, equipamento, terminal ou variavel?

### 3. Revisao do encaminhamento - 10 min

Avaliar o `NotificationIntent`.

Perguntas:

- O setor destino esta correto?
- O assunto seria entendido em e-mail/chamado?
- O corpo do texto tem contexto suficiente?
- Ha ruido demais?
- Ha informacao tecnica faltando?
- O texto evita expor dados sensiveis?

### 4. Revisao do CAPTCHA humano - 10 min

Avaliar se os vereditos cobrem a realidade operacional.

Vereditos atuais:

- `CORRECT`;
- `FALSE_POSITIVE`;
- `INCOMPLETE`;
- `INCONCLUSIVE`;
- `NEEDS_OTHER_SECTOR`;
- `NOT_ENOUGH_EVIDENCE`.

Perguntas:

- Operacao conseguiria escolher um veredito sem ambiguidade?
- Engenharia conseguiria diferenciar falso positivo de inconclusivo?
- Falta motivo padrao para manobra programada?
- Falta motivo padrao para defeito de medicao?
- Falta motivo padrao para erro de cadastro?

### 5. Decisao da rodada - 10 min

Classificar a demo:

| Resultado | Significado |
|---|---|
| GO | Texto, contexto e roteamento bons para expandir cenarios sinteticos |
| PARTIAL | Fluxo bom, mas campos/microcopy precisam ajuste |
| NO-GO | Revisores nao entenderam ocorrencia ou risco de uso indevido |

## Criterios de aceite do texto

O texto de ocorrencia/encaminhamento e aceito se:

- deixa claro o que aconteceu;
- deixa claro onde aconteceu;
- deixa claro quando aconteceu;
- deixa claro quem deve revisar;
- separa candidato de evento confirmado;
- indica que provider real esta desligado;
- nao contem dado real;
- nao contem path sensivel;
- nao contem conclusao operacional automatica;
- permite feedback humano em menos de 1 minuto.

## Matriz de avaliacao

Pontuar cada item de 0 a 2:

| Criterio | 0 | 1 | 2 | Nota |
|---|---|---|---|---|
| Clareza do titulo | confuso | parcialmente claro | claro |  |
| Contexto tecnico | insuficiente | medio | suficiente |  |
| Setor destino | errado | discutivel | correto |  |
| Diferenca candidato/confirmado | ausente | parcial | clara |  |
| Microcopy | tecnica demais | aceitavel | humana e precisa |  |
| Seguranca/redacao | risco | revisar | seguro |  |
| CAPTCHA | ambiguo | parcial | acionavel |  |

Interpretacao:

- 12 a 14: GO;
- 8 a 11: PARTIAL;
- 0 a 7: NO-GO.

## Campos que devem ser validados por Engenharia/Operacao

Obrigatorios para seguir:

- `occurrence_id`;
- `thread_id`;
- `reference_key`;
- dominio do problema;
- severidade;
- setor dono;
- setor destino;
- periodo;
- SE;
- alimentador/BAY;
- equipamento;
- terminal;
- variavel;
- status do candidato;
- tipo de feedback;
- evidencia redigida.

Campos ainda candidatos:

- SLA por severidade;
- prioridade setorial;
- impacto operacional estimado;
- texto padrao por tipo de evento;
- nivel minimo de evidencia para fechar.

## Evolucao para 5 cenarios sinteticos setoriais

Antes de UI/store corporativo, a demo deve evoluir para cinco cenarios
sinteticos. Cada cenario precisa gerar:

- uma ocorrencia;
- um notification intent;
- um candidato ou diagnostico;
- um feedback CAPTCHA;
- um resumo Markdown redigido;
- um resultado GO/PARTIAL/NO-GO.

### Cenario 1 - Inversao de fluxo P/Q

Setores:

- Engenharia;
- Operacao.

Objetivo:

Validar se uma inversao detectada pela engine aparece como candidato tecnico,
sem virar confirmacao operacional.

Feedbacks esperados:

- `CORRECT` com `OPERATIONAL_SWITCHING` vira confirmacao humana;
- `SCADA_CONFIRMS` vira confirmacao operacional;
- `SCADA_DOES_NOT_CONFIRM` vira falso positivo.

Pronto quando:

- Engenharia entende FP/MW/MVA/fluxo;
- Operacao entende que precisa confirmar manobra/evento.

### Cenario 2 - Manobra com evidência SCADA

Setores:

- Operacao;
- Protecao/Automacao/SCADA.

Objetivo:

Validar o caminho em que um candidato estatistico e promovido somente quando ha
evidencia SCADA.

Feedbacks esperados:

- `SCADA_CONFIRMS`;
- `OPERATIONAL_SWITCHING`;
- `NOT_ENOUGH_EVIDENCE`.

Pronto quando:

- todos concordam que sem SCADA o estado maximo e humano, nao operacional.

### Cenario 3 - Lacuna ou cadencia de medicao

Setores:

- Medicao/Dados;
- Engenharia.

Objetivo:

Validar ocorrencia em que o problema nao e eletrico, mas disponibilidade ou
cadencia do dado.

Feedbacks esperados:

- `MISSING_MEASUREMENT`;
- `MEASUREMENT_BAD_QUALITY`;
- `NEEDS_OTHER_SECTOR`.

Pronto quando:

- o texto nao culpa Operacao indevidamente;
- o destino correto e Medicao/Dados.

### Cenario 4 - Erro de cadastro/terminal/equipamento

Setores:

- Cadastro/Ativos;
- Engenharia;
- Operacao, se houver impacto.

Objetivo:

Validar se inconsistencias de terminal, equipamento ou alimentador sao
encaminhadas para Cadastro sem serem tratadas como evento de rede.

Feedbacks esperados:

- `CADASTRE_MISMATCH`;
- `NEEDS_OTHER_SECTOR`;
- `INCOMPLETE`.

Pronto quando:

- o estado fica `HUMAN_REVIEWED` ou equivalente;
- nao vira `SCADA_CONFIRMED`.

### Cenario 5 - Falha de export/dashboard ou dataset BI

Setores:

- TI/BI;
- Engenharia;
- Gestao como leitora.

Objetivo:

Validar ocorrencia de produtividade: exportacao, filtro, dashboard ou dataset
nao representam o recorte esperado.

Feedbacks esperados:

- `EXPORT_OR_QUERY_ERROR`;
- `INCOMPLETE`;
- `NEEDS_OTHER_SECTOR`.

Pronto quando:

- o texto separa erro de ferramenta de erro eletrico;
- o encaminhamento vai para TI/BI ou Engenharia conforme causa.

## Tabela de saida esperada dos 5 cenarios

| Cenario | Setor dono | Setor consultado | Label esperado | Risco principal | Status |
|---|---|---|---|---|---|
| Inversao P/Q | Engenharia | Operacao | humano ou SCADA | falso positivo operacional |  |
| Manobra SCADA | Operacao | SCADA | SCADA confirmado | confirmar sem evidencia |  |
| Lacuna/cadencia | Medicao/Dados | Engenharia | incompleto/falso positivo | diagnostico eletrico com dado ruim |  |
| Cadastro/terminal | Cadastro/Ativos | Engenharia | outro setor/incompleto | mapear ativo errado |  |
| Export/BI | TI/BI | Engenharia | erro de query/export | confundir ferramenta com campo |  |

## Saida da revisao humana

Ao final da reuniao, registrar:

- data;
- participantes;
- artefato revisado;
- resultado GO/PARTIAL/NO-GO;
- campos obrigatorios adicionados;
- frases que devem mudar;
- setores que precisam entrar;
- cenarios aprovados;
- riscos antes de UI/store corporativo.

Modelo curto:

```markdown
# Revisao humana ANDY Threads Demo

Data:
Participantes:
Artefato revisado:
Resultado: GO/PARTIAL/NO-GO

## Decisoes

-

## Ajustes obrigatorios

-

## Campos faltantes

-

## Cenarios sinteticos aprovados

-

## Bloqueios antes de UI/store corporativo

-
```

## Gate antes de UI/store corporativo

Nao iniciar UI/store corporativo enquanto:

- Engenharia e Operacao nao aprovarem o texto base;
- pelo menos 5 cenarios sinteticos nao forem revisados;
- os estados `candidate`, `human_confirmed`, `scada_confirmed`,
  `false_positive`, `inconclusive` e `needs_other_sector` nao estiverem claros;
- o provider real nao tiver politica aprovada;
- o store corporativo nao tiver owner, retencao e seguranca definidos.

## Proximo passo recomendado

Criar a task:

```text
ANDY Threads Demo Scenarios 001 - Gerar 5 cenarios sinteticos setoriais e pacotes Markdown para revisao humana.
```
