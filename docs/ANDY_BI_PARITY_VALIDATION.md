# ANDY BI Parity Validation

## Objetivo

Validar se o dataset publicado para BI preserva os resultados do ANDY Desktop,
incluindo XLSX, CSV e saidas canonicas.

## Validacoes minimas

- Contagens por periodo/fonte.
- Min/max timestamp.
- Quantidade de SE/BAY/equipamento/terminal/variavel.
- Somas/agregacoes basicas.
- MVA/FP/MW derivados.
- Patamar.
- Inversao/fluxo.
- Quality flags.
- Hash/lote.
- Linhas exportadas.

## Regra de bloqueio

Divergencia em medida critica bloqueia publicacao ate analise humana.

## Comando local

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_parity.py --dataset artifacts\andy_bi_dataset --out artifacts\andy_bi_parity_report.md
```

## Tolerancia

Comparacoes float devem usar tolerancia configuravel. Arredondamento visual do
BI nao pode mascarar divergencia de engine.
