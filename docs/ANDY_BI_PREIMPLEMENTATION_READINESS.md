# ANDY BI Preimplementation Readiness

Data: 2026-07-07

## Estado preparado

Esta fase deixa o ambiente pronto para receber dados especificos da rede corporativa sem misturar segredo, path real ou regra de acesso dentro do codigo.

## Criado nesta preparacao

- contrato de produto;
- opcoes de identidade;
- modelo de seguranca;
- modelo de tenant/policy;
- templates JSON sem segredo;
- padroes de `.gitignore` para arquivos privados;
- gate de readiness.

## Arquivos privados esperados no futuro

Quando a TI/seguranca fornecer os dados, eles devem ir para arquivos nao versionados:

- `config/andy_bi_identity.private.json`
- `config/andy_bi_tenant_policy.private.json`
- `config/andy_bi_environment.private.json`
- `config/andy_corporate_source_policy.json`

## Informacoes que ainda faltam

- provedor de identidade escolhido;
- authority/metadata do IdP;
- client ID ou SP entity ID;
- modelo de grupos corporativos;
- distribuidoras/estados oficiais no escopo;
- raizes de fonte autorizadas;
- destino de auditoria;
- politica de token;
- politica de exportacao.

## Como validar

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_readiness.py
.\.venv\Scripts\python.exe -m pytest tests\test_andy_bi_readiness.py -q
```

## Limite de seguranca

Este preparo nao habilita login real, nao acessa rede, nao sincroniza fontes novas e nao altera a engine analitica.
