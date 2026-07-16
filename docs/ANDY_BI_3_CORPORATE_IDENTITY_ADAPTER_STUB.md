# ANDY BI-3 Corporate Identity Adapter Stub

Data: 2026-07-07

## Objetivo

Preparar a interface para providers corporativos reais sem autenticar de verdade ainda.

## Providers previstos

- `mock_claims`: provider local ficticio para testes.
- `oidc`: stub para OpenID Connect.
- `saml`: stub para SAML.
- `kerberos`: stub para Windows/Kerberos.
- `ldap`: stub para LDAP/AD.

## Regra de seguranca

Providers corporativos sao stubs bloqueantes nesta fase. Eles nao fazem chamada de rede, nao pedem senha, nao validam token e nao produzem claims reais.

Se `identity_provider=oidc` ou outro provider corporativo for usado agora, o resultado esperado e bloqueio auditavel:

```text
identity_resolution_blocked:oidc_corporate_identity_provider_stub_not_implemented
```

## Arquivos

- `andy_bi/providers.py`
- `config/andy_bi_identity_provider.example.json`
- `scripts/check_andy_bi_identity_provider_stub.py`
- `tests/test_andy_bi_identity_provider_stub.py`

## Contrato futuro

Um provider real devera receber configuracao privada revisada e retornar `IdentityClaims` normalizado:

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

## Dados ainda necessarios da TI

- provider escolhido;
- authority/metadata/realm/base DN;
- client ID publico ou SP entity ID;
- redirect URI aprovado;
- estrategia de grupos;
- estrategia de token cache;
- regras de expiracao/logout;
- destino de auditoria.

## Limite

Nenhuma integracao real deve ser ativada antes da revisao humana e corporativa.
