# ANDY BI Identity Options

Data: 2026-07-07

## Regra central

ANDY nao deve guardar senha de funcionario. O app deve delegar autenticacao ao provedor corporativo e receber identidade, grupos e permissoes.

## Opcoes

| Opcao | Uso recomendado | Vantagens | Riscos | Dados necessarios |
|---|---|---|---|---|
| OpenID Connect | Preferencial para app moderno | Token padronizado, claims, expiracao | Precisa registro de app | authority URL, tenant, client ID, redirect URI, scopes |
| SAML | Ambientes corporativos legados | Amplamente suportado | Mais pesado para desktop | IdP metadata, SP entity ID, certificado publico |
| Kerberos/Windows Integrated Auth | Maquinas no dominio | Experiencia sem senha manual | Depende de dominio e rede | realm/domain, SPN, politica de grupo |
| LDAP/AD bind | Somente se TI exigir | Simples para consultar grupos | Pode induzir captura de senha | servidor, base DN, bind seguro aprovado |

## Dados que podem ser versionados

- Templates sem valores reais.
- Nomes genericos de roles.
- Contratos de claims.
- Estrutura de policy.

## Dados que nao podem ser versionados

- Tenant real.
- Client secret.
- Certificados privados.
- Hostnames privados.
- LDAP bind account.
- Grupos reais sensiveis.
- Caminhos reais de fontes.

## Contrato minimo de claims

- `subject`: identificador unico.
- `display_name`: nome exibivel.
- `email_or_employee_id`: contato ou matricula.
- `groups`: grupos corporativos.
- `roles`: papeis resolvidos para ANDY.
- `distributor_scope`: distribuidoras autorizadas.
- `state_scope`: estados autorizados.

## Recomendacao

Comecar com contrato OIDC/SAML abstrato e mock local de claims para desenvolvimento. A integracao real deve aguardar os dados aprovados pela TI.
