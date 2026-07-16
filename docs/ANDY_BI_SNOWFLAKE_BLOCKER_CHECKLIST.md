# ANDY BI/Snowflake Blocker Checklist

## Status

Status em 2026-07-10: BLOCKED para integracao real.

Enquanto o acesso Snowflake nao chega, a frente BI pode continuar em:

- contrato;
- mocks;
- dataset sintetico;
- semantic model;
- RLS/ABAC;
- pacote TI/BI;
- readiness scripts;
- paridade contra outputs locais.

## Bloqueios obrigatorios

| Item | Pergunta | Dono provavel | Status |
|---|---|---|---|
| Conta Snowflake | Qual account/locator oficial? | TI/BI | Pendente |
| Role | Qual role read-only para ANDY? | TI/BI | Pendente |
| Warehouse | Qual warehouse usar para leitura? | TI/BI | Pendente |
| Database | Qual database autorizado? | TI/BI | Pendente |
| Schema | Qual schema contem medicoes/publicacao? | TI/BI | Pendente |
| Network | Ha allowlist/VPN/proxy? | TI/Seguranca | Pendente |
| Auth | SSO, key pair, OAuth ou user/password corporativo? | TI/Seguranca | Pendente |
| Driver | Driver Python permitido e versao? | TI/BI | Pendente |
| Write policy | ANDY pode escrever staging/output ou so ler? | TI/BI | Pendente |
| Data owner | Quem aprova dados de medicao no BI? | Engenharia/TI | Pendente |
| Retencao | Politica de historico e logs? | Governanca | Pendente |
| RLS/ABAC | Quais grupos por estado/distribuidora/setor? | TI/BI/Seguranca | Pendente |
| Refresh | Quem opera refresh/gateway/schedule? | TI/BI | Pendente |
| Workspace | Dev/Homolog/Prod definidos? | TI/BI | Pendente |
| Sensibilidade | Classificacao de dados eletricos? | Seguranca | Pendente |

## Config privada minima futura

Nao versionar.

Exemplo de campos esperados:

```json
{
  "account": "<PRIVATE>",
  "role": "<PRIVATE_READ_ONLY_ROLE>",
  "warehouse": "<PRIVATE_WAREHOUSE>",
  "database": "<PRIVATE_DATABASE>",
  "schema": "<PRIVATE_SCHEMA>",
  "auth_mode": "sso_or_keypair_or_oauth",
  "network_policy": "<PRIVATE>",
  "allowed_operations": ["read"],
  "owner": "<PRIVATE_OWNER>"
}
```

## Gates antes de integrar

- Config privada revisada por humano.
- Nenhuma credencial em Git.
- Driver instalado em ambiente controlado.
- Query smoke read-only aprovada.
- Limites de custo/warehouse confirmados.
- Query timeout definido.
- Teste de redacao de logs.
- RLS/ABAC definido antes de publicacao.
- Dataset demo/sintetico continua disponivel para testes.

## Pode fazer agora

- Manter `andy_bi` com adapters mock.
- Criar contrato Snowflake abstrato.
- Criar checklist de config privada.
- Criar testes que falham de forma clara sem config.
- Validar dataset sintetico.
- Preparar prompts de integracao.

## Nao fazer agora

- Nao hardcodar account/warehouse/schema.
- Nao criar credencial propria.
- Nao conectar em provider real sem config privada.
- Nao publicar dataset corporativo.
- Nao mover matematica critica para SQL/Snowflake sem paridade.
- Nao assumir que todo usuario com dominio Equatorial pode ver todo dado.

## Perguntas para reuniao TI/BI

1. Snowflake sera fonte do BI ou staging intermediario?
2. ANDY deve ler tabelas existentes ou publicar tabelas derivadas?
3. Existe ambiente Dev/Homolog/Prod?
4. Quais grupos corporativos controlam acesso por distribuidora/estado?
5. Qual politica de mascaramento/redacao para logs?
6. Qual SLA de refresh?
7. Quem e owner funcional do dataset?
8. Quem e owner tecnico da operacao?
9. Qual procedimento de rollback?
10. Qual limite de custo/warehouse para consultas exploratorias?
