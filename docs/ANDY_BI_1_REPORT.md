# ANDY BI-1 Report - Identity Contract Mock

Data: 2026-07-07

## Resumo executivo

Foi criada uma camada local e ficticia de identidade para preparar o ANDY BI para RBAC/ABAC antes da chegada dos dados especificos da rede corporativa.

O resolvedor mock fica desligado por padrao e nao conecta em rede. Ele existe para testar contrato de claims, escopo por distribuidora/estado e decisoes de permissao sem tocar em login real, senha, IdP ou engine analitica.

## Criado

- `andy_bi/__init__.py`
- `andy_bi/identity.py`
- `andy_bi/policy.py`
- `config/andy_bi_mock_claims.example.json`
- `scripts/check_andy_bi_identity_mock.py`
- `tests/test_andy_bi_identity_mock.py`
- `docs/ANDY_BI_1_IDENTITY_CONTRACT_MOCK.md`

## Modificado

- `.gitignore`
- `config/andy_bi_tenant_policy.example.json`

## Decisoes

- Senha nunca entra no ANDY.
- Mock deve exigir habilitacao explicita.
- Claims ficticias devem usar dominio `example.invalid`.
- Policy deve ser `deny` por padrao.
- Toda decisao deve produzir razao auditavel.

## Residuo proposital

- Nenhum IdP real configurado.
- Nenhum grupo real configurado.
- Nenhuma distribuidora real configurada.
- Nenhum caminho corporativo real configurado.
- Nenhuma UI de login habilitada.

## Proxima fase recomendada

**ANDY BI-2 - Policy Enforcement Adapter**

Criar um adapter que conecte claims normalizadas ao query/export boundary em modo guardado por feature flag, ainda sem IdP real.
