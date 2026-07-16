# ANDY BI RLS/ABAC Policy

## Principio

A politica e deny-by-default. Nenhum usuario ve tudo por padrao. A plataforma
corporativa autentica; o ANDY fornece o contrato de escopo, perfis e validacao.

## Perfis

| Perfil | Uso esperado |
|---|---|
| `viewer` | Visualizacao sem export amplo |
| `engineer` | Analise e exportacao autorizada |
| `auditor` | Leitura de qualidade e auditoria |
| `admin_dataset` | Administracao tecnica do dataset, sem visao total automatica |
| `bi_owner` | Dono do modelo/relatorio no workspace |

## Escopos ABAC

- Distribuidora.
- Estado.
- Area.
- Fonte.
- Subestacao.
- Perfil.
- Workspace.

## Limites

- Provider real fica desligado em exemplos.
- Mock claims servem apenas para teste local.
- Grupos corporativos reais devem entrar por arquivo privado revisado.
- Excecao de acesso deve gerar finding de auditoria.

## Gate local

Rodar:

```powershell
.\.venv\Scripts\python.exe scripts\check_andy_bi_rls_policy.py
```
