# ANDY BI Web Corporate Product Brief

## Problema

O ANDY Desktop concentra uma engine Python madura para indexacao, normalizacao,
analise eletrica, patamar, fluxo P/Q, exportacao XLSX/CSV e auditoria. O ganho
tecnico e alto, mas o uso atual exige instalacao local, runtime por maquina e
execucao orientada por operador tecnico.

## Oportunidade

A empresa ja possui plataforma corporativa de BI, identidade corporativa,
workspaces, governanca de publicacao e acesso por login/SSO. O ANDY deve
aproveitar esse trilho em vez de criar autenticacao propria ou um BI paralelo.

## Solucao

Publicar resultados governados do ANDY como dataset/semantic model para BI Web:

- ANDY calcula e valida.
- BI apresenta, filtra e agrega valores ja publicados.
- A plataforma corporativa autentica.
- RLS/ABAC restringe acesso.
- Auditoria registra lote, hash, versao, periodo, qualidade e operacao.

## Fronteira de responsabilidade

| Camada | Responsabilidade |
|---|---|
| ANDY Python Engine | Fonte da verdade analitica e eletrica |
| ANDY BI Dataset Builder | Pacote governado, manifest, schema e validacao |
| BI corporativo | Workspace, relatorio, app interno, refresh e acesso |
| Identity/RLS | Plataforma corporativa e politicas aprovadas |
| Auditoria | Lote, hash, qualidade, acesso e rastreabilidade |

## Nao-objetivos

- Nao criar login proprio.
- Nao substituir a engine Python.
- Nao expor dados sem RLS/ABAC.
- Nao reimplementar matematica critica no BI.
- Nao publicar dados reais sem owner, aprovador e configuracao privada revisada.

## Usuarios

- Engenharia.
- Operacao.
- Gestao.
- Auditoria.
- Suporte tecnico.
- Outros setores autorizados por politica.

## Valor

- Acesso web sem instalacao local.
- Cockpit governado com a mesma semantica do ANDY.
- Escalabilidade via plataforma corporativa.
- Reducao de retrabalho.
- Padronizacao da leitura eletrica.
- Trilha de validacao e auditoria.
