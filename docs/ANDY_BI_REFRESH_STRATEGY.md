# ANDY BI Refresh Strategy

## Estrategia

1. Build local do dataset pelo ANDY.
2. Validacao de contrato.
3. Validacao de paridade.
4. Revisao de RLS/ABAC.
5. Publicacao manual em Dev.
6. Homologacao com engenharia.
7. Agendamento/incremental apenas apos aceite.

## Incremental

Chaves recomendadas:

- `lote_id`
- `source_id`
- `source_period_start`
- `source_period_end`

## Retencao

- Logs: minimo sugerido de 90 dias, sujeito a politica corporativa.
- Lotes de rollback: minimo sugerido de 2 lotes aprovados.
- Dataset antigo: conforme classificacao do dado.

## Residuos dependentes de TI/BI

- Gateway real.
- Frequencia de refresh.
- Politica de retencao oficial.
- Grupos corporativos.
- Workspace e owner.
