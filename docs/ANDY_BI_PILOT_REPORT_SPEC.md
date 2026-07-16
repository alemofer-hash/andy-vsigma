# ANDY BI Pilot Report Spec

## Pagina 1 - Cockpit Executivo ANDY

- Cobertura temporal.
- Fontes carregadas.
- Subestacoes.
- Equipamentos.
- Terminais.
- Variaveis.
- Qualidade do lote.
- Ultima atualizacao.

## Pagina 2 - Catalogo de Medicoes

- Filtros cascatais: Ano -> Mes -> SE -> BAY/Alimentador -> Equipamento -> Terminal -> Dia -> Variavel.
- Contagem de medicoes.
- Disponibilidade.
- Lacunas.
- Cadencia detectada.

## Pagina 3 - Patamar e Carga

- Patamar por periodo.
- Perfis de carga.
- Estatisticas.
- Flags de qualidade.

## Pagina 4 - Fluxo P/Q e Inversao

- MW.
- MVA.
- FP assinado.
- Quadrante.
- Sentido de fluxo.
- Inversoes.
- Auditoria de fallback.

## Pagina 5 - Qualidade e Auditoria

- Lote.
- Hash.
- Fonte.
- Cadencia.
- Quality flags.
- Export/access audit.

## Pagina 6 - Paridade ANDY Desktop

- Comparacao com XLSX.
- Divergencias.
- Status de validacao.
- Data/hora do ultimo lote validado.

## Observacao para analista BI

Medidas criticas ja devem chegar prontas nas facts do ANDY. Use o BI para
apresentar, filtrar, agregar e navegar, nao para recriar a matematica eletrica.
