# ANDY BI-2 Policy Enforcement Adapter

Data: 2026-07-07

## Objetivo

Conectar as decisoes RBAC/ABAC da fase BI-1 ao boundary de query/export do ANDY, mantendo enforcement desligado por padrao.

## Limites

- Nao integra IdP real.
- Nao usa login real.
- Nao acessa rede corporativa.
- Nao altera calculos eletricos.
- Nao altera filtros ou exportacao quando a feature flag esta desligada.
- Nao cria usuario/senha local.

## Como funciona

O adapter `andy_bi.enforcement` avalia operacoes do boundary antes da execucao:

- `query.overview`
- `query.options`
- `query.page`
- `load_profile.analyze`
- `export.audit`
- `export.csv_long`
- `export.csv_wide`
- `export.xlsx_dashboard`

Quando desabilitado, retorna `status=disabled` e o boundary continua o fluxo antigo.

Quando habilitado, exige:

- `bi_policy.enabled=true`
- `bi_policy.identity_key`
- `bi_policy.mock_claims_file`
- `bi_policy.tenant_policy_file`
- `bi_scope.tenant_id`
- `bi_scope.state`
- `bi_scope.source_root`

## Payload exemplo

```json
{
  "bi_policy": {
    "enabled": true,
    "identity_key": "mock_engineer_rs",
    "mock_claims_file": "config/andy_bi_mock_claims.private.json",
    "tenant_policy_file": "config/andy_bi_tenant_policy.example.json"
  },
  "bi_scope": {
    "tenant_id": "DISTRIBUTOR_RS_PLACEHOLDER",
    "state": "RS",
    "source_root": "${ANDY_BI_RS_SOURCE_ROOT}"
  }
}
```

## Resultado esperado

- Engenheiro RS consulta/exporta RS.
- Engenheiro RS nao consulta PA.
- Viewer PA consulta PA, mas nao exporta.
- Requisicao sem `bi_scope` e bloqueada quando enforcement esta ligado.
- Operacoes nao BI continuam fora do enforcement.

## Proxima integracao futura

Quando houver IdP real, trocar o resolvedor mock por claims normalizadas vindas de OIDC/SAML/Kerberos/LDAP, mantendo o mesmo contrato de policy.
