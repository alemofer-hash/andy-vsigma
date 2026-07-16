# ANDY Threads Access Policy

## Principio

ANDY Threads usa deny-by-default. Acesso so e permitido quando identidade,
escopo e setor sao compativeis com a referencia tecnica.

## Acoes

- `CREATE_THREAD`
- `READ_THREAD`
- `COMMENT`
- `CHANGE_STATUS`
- `CREATE_DECISION`
- `EXPORT_THREAD`
- `ARCHIVE_THREAD`

## Regras do MVP

- Usuario anonimo e negado.
- Usuario sem referencia tecnica e negado.
- Usuario fora do escopo da referencia e negado.
- Setor dono pode criar e alterar status quando escopo bate.
- Setor consultado pode comentar.
- Apenas setor autorizado pode criar decisao ou arquivar.
- Export exige permissao explicita.
- Mock user existe apenas para teste local.
- Provider real fica desligado.

## Limites

O MVP nao implementa SSO, AD, Entra ID, SAML, LDAP, notificacao, DM ou store
corporativo. Esses pontos exigem revisao institucional.

## Auditoria

Avaliacoes de policy e negacoes devem gerar evento auditavel quando o fluxo
operacional usar o store.
