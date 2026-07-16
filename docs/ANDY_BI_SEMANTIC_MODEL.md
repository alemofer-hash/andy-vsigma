# ANDY BI Semantic Model

## Objetivo

Definir relacoes, medidas permitidas e limites para o modelo semantico do BI.

## Relacoes principais

As tabelas fato se relacionam com `dim_lote`, `dim_source`, `dim_quality_flag`
e dimensoes eletricas/temporais quando as chaves existem. O modelo recomendado
usa cardinalidade many-to-one de fato para dimensao.

```mermaid
flowchart LR
    F1["fact_medicoes_long"] --> D1["dim_date"]
    F1 --> D2["dim_time"]
    F1 --> D3["dim_source"]
    F1 --> D4["dim_subestacao"]
    F1 --> D5["dim_bay_alimentador"]
    F1 --> D6["dim_equipamento"]
    F1 --> D7["dim_terminal"]
    F1 --> D8["dim_variavel"]
    F1 --> D9["dim_cadencia"]
    F2["fact_power_flow"] --> P["dim_patamar"]
    F3["fact_load_profile"] --> P
    F1 --> L["dim_lote"]
    F2 --> L
    F3 --> L
```

## Medidas permitidas no BI

- Contagem de medicoes.
- Distinct count de pontos.
- Disponibilidade publicada pelo ANDY.
- Media simples de valores ja normalizados.
- Indicadores de qualidade.
- Status de lote.

## Medidas que devem vir da engine Python

- MVA.
- FP assinado.
- MW derivado.
- Fluxo P/Q.
- Inversao.
- Patamar.
- Tensao nominal resolvida.
- Fallbacks auditaveis.

## Regra de paridade

Qualquer calculo critico que seja proposto na camada BI precisa de teste de
paridade contra a engine Python antes de ir para homologacao.
