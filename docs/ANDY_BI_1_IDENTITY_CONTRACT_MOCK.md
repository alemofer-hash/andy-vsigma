# ANDY BI-1 Identity Contract Mock

Data: 2026-07-07

## Objetivo

Criar um resolvedor local de claims ficticias para testar RBAC/ABAC antes da integracao com o provedor corporativo real.

## Limites

- Nao autentica funcionario real.
- Nao conecta em AD, Entra ID, LDAP, SAML ou OIDC.
- Nao armazena senha.
- Nao armazena client secret.
- Nao habilita login no app operacional.
- Nao altera engine analitica, filtros, exportacao ou ingestao.

## Arquivos

- `andy_bi/identity.py`: contrato `IdentityClaims` e resolvedor `MockIdentityResolver`.
- `andy_bi/policy.py`: avaliador `TenantPolicyResolver` para RBAC/ABAC.
- `config/andy_bi_mock_claims.example.json`: claims ficticias, `mock_enabled=false`.
- `scripts/check_andy_bi_identity_mock.py`: gate de validacao.
- `tests/test_andy_bi_identity_mock.py`: testes focados.

## Contrato de claims

Campos minimos:

- `subject`
- `display_name`
- `email_or_employee_id`
- `groups`
- `roles`
- `distributor_scope`
- `state_scope`
- `source_scope`
- `claims_source`
- `auth_method`

## Como habilitar somente em desenvolvimento controlado

O exemplo versionado fica desligado por padrao:

```json
"mock_enabled": false
```

Para um teste local, copiar para arquivo privado ignorado:

```powershell
Copy-Item config\andy_bi_mock_claims.example.json config\andy_bi_mock_claims.private.json
```

Depois editar o privado e usar:

```powershell
$env:ANDY_BI_IDENTITY_MOCK_ENABLED="1"
$env:ANDY_BI_MOCK_CLAIMS_FILE="config\andy_bi_mock_claims.private.json"
```

Esse caminho ainda e apenas desenvolvimento; nao deve ser usado como login real.

## Politica testada

- Engenheiro RS pode consultar e exportar no escopo RS.
- Engenheiro RS nao pode consultar PA.
- Viewer PA pode consultar PA, mas nao pode exportar.
- Suporte pode consultar auditoria/suporte conforme policy, mas nao consulta dados por padrao.

## Proxima integracao futura

Trocar o resolvedor mock por um adapter real de IdP mantendo o mesmo contrato `IdentityClaims`. O app operacional deve chamar policy sobre claims normalizadas, independentemente de virem de OIDC, SAML, Kerberos ou LDAP.
