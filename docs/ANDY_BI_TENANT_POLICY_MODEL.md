# ANDY BI Tenant Policy Model

Data: 2026-07-07

## Objetivo

Definir como o ANDY BI deve separar acesso por distribuidora, estado, fonte e perfil sem depender de hardcode.

## Modelo

```text
Usuario autenticado
-> grupos corporativos
-> roles ANDY
-> escopo por distribuidora/estado
-> fontes autorizadas
-> filtros e exports permitidos
```

## Entidades

- Tenant: distribuidora ou unidade operacional.
- Estado: UF vinculada ao tenant.
- Fonte: raiz/catologo autorizado.
- Role: papel funcional do usuario.
- Permission: acao permitida.
- Scope: limite de dados permitido.

## Roles iniciais

- `admin`: administra fontes e policy.
- `engineer`: consulta, analisa e exporta.
- `viewer`: visualiza sem exportar.
- `support`: diagnostico sem acesso amplo a dados.

## Regra de decisao

O padrao e negar. Uma acao so deve ser permitida se:

- o usuario esta autenticado;
- os grupos foram resolvidos;
- a role permite a acao;
- o tenant esta no escopo;
- a fonte esta permitida;
- a operacao respeita a politica de exportacao.

## Arquivos

- Template versionavel: `config/andy_bi_tenant_policy.example.json`.
- Arquivo real privado: `config/andy_bi_tenant_policy.private.json`.
- O arquivo privado e ignorado pelo Git.

## Dados pendentes

- nomes reais das distribuidoras no padrao aprovado;
- grupos corporativos reais;
- raizes oficiais das fontes;
- owners tecnicos;
- excecoes por area;
- politica de retencao de export.
