# ANDY BI-2 Report - Policy Enforcement Adapter

Data: 2026-07-07

## Resumo executivo

Foi criado um adapter de enforcement RBAC/ABAC para o boundary de query/export do ANDY. A integracao fica desligada por padrao e so atua quando a requisicao ou ambiente habilita explicitamente a policy.

O objetivo foi preparar o caminho para o BI corporativo sem ligar identidade real, sem rede Equatorial, sem alterar a engine analitica e sem mudar o comportamento operacional atual.

## Criado

- `andy_bi/enforcement.py`
- `config/andy_bi_policy_enforcement.example.json`
- `scripts/check_andy_bi_policy_enforcement.py`
- `tests/test_andy_bi_policy_enforcement.py`
- `docs/ANDY_BI_2_POLICY_ENFORCEMENT_ADAPTER.md`

## Modificado

- `.gitignore`
- `andy_bi/__init__.py`
- `andy_boundary/operations.py`

## Comportamento preservado

Sem feature flag/payload de policy, `execute_boundary_request()` continua executando as operacoes antigas.

## Comportamento novo

Com enforcement ligado:

- consulta/export exige identidade mock resolvida;
- consulta/export exige `bi_scope`;
- usuario fora do tenant/estado/fonte e bloqueado;
- usuario sem role de export e bloqueado antes de exportar;
- erro de policy recebe classificacao `PolicyDenied`.

## Residuo proposital

- Sem IdP real.
- Sem grupos reais.
- Sem source roots reais.
- Sem UI de login.
- Sem enforcement ativado por padrao.

## Proxima fase recomendada

**ANDY BI-3 - Corporate Identity Adapter Stub**

Criar interface abstrata para providers reais, mantendo o mock como implementacao de teste e aguardando dados oficiais da TI.
