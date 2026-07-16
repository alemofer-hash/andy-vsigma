# ANDY Threads Sector Acceptance Gate

## Objetivo

Mitigar o risco de usar a matriz setorial inicial sem validacao humana de
Engenharia, Operacao, Medicao/Dados, Cadastro/Ativos, SCADA/Automacao,
Obras/Manutencao, TI/BI e Gestao.

## Regra

A matriz setorial versionada e apenas uma proposta inicial. Ela nao esta
aprovada para uso operacional corporativo ate que cada setor registre aceite em
arquivo privado revisado.

## Arquivo publico

- `config/andy_threads_sector_acceptance.example.json`

Esse arquivo e um template publicavel. Ele fica com `accepted=false` e
`accepted_for_operational_use=false`.

## Arquivo privado esperado

Nome sugerido, nao versionado:

```text
config/andy_threads_sector_acceptance.private.json
```

O arquivo privado deve conter os setores obrigatorios, status `accepted`,
responsavel, data, evidencia redigida e decisao.

## Validador

Modo local/template:

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_threads_sector_acceptance.py --allow-pending
```

Modo corporativo estrito:

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_threads_sector_acceptance.py --file config\andy_threads_sector_acceptance.private.json
```

## Criterio de promocao

Sem aceite setorial completo:

- nao ativar UI operacional;
- nao ativar store corporativo;
- nao integrar notificacoes;
- nao tratar a matriz como policy final.
