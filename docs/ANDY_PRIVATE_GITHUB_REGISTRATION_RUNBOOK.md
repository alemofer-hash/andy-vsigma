# ANDY Private GitHub Registration Runbook

Data-base: 2026-07-10

## Objetivo

Registrar o ANDY em um repositorio privado GitHub com seguranca, sem publicar
dado real, segredo, runtime, artifacts ou reports.

Este runbook contem comandos sugeridos. Nao executar automaticamente sem URL e
aprovacao humana.

## Pre-requisitos

- Repositorio privado criado no GitHub.
- Owner confirmado: usuario ou organizacao.
- Nome confirmado.
- Visibilidade `private`.
- Branch policy definida.
- Nenhum remote configurado automaticamente por Codex.
- `git status --short` limpo.
- `check_andy_git_safety.py` passou.
- `check_andy_tracked_safety.py` passou.

## Comandos de verificacao local

```powershell
git status --short
git log --oneline -5
git remote -v
git branch --show-current
py -3.12 scripts\check_andy_git_safety.py
py -3.12 scripts\check_andy_tracked_safety.py
git diff --check
```

## Criacao do repositorio privado

Criar manualmente no GitHub:

```text
Visibility: Private
Repository name: andy-vsigma
Initialize with README: no
Add .gitignore: no
Add license: conforme decisao corporativa
```

## Configurar remote

Substituir a URL abaixo pela URL privada real revisada:

```powershell
git remote add origin <PRIVATE_GITHUB_REPO_URL>
```

Conferir:

```powershell
git remote -v
```

## Branch principal

Se a politica exigir `main`:

```powershell
git branch -M main
```

Se a politica permitir manter `master`, documentar a decisao antes do push.

## Push inicial

Somente depois dos gates e revisao humana:

```powershell
git push -u origin main
```

ou, se mantiver `master`:

```powershell
git push -u origin master
```

## Protecao de branch recomendada

Ativar no GitHub:

- Require pull request before merging.
- Require approvals.
- Require status checks.
- Require branches to be up to date.
- Block force push.
- Block deletion.
- Restrict who can push to protected branches.

## Secrets e variaveis

Nao criar secrets no primeiro push.

Secrets futuros devem ser cadastrados apenas se houver:

- owner tecnico;
- finalidade documentada;
- rotacao definida;
- permissao corporativa;
- ambiente separado (`dev`, `homolog`, `prod`).

## O que nunca deve ser enviado

- `.env`;
- `*.private.json`;
- `*.duckdb`;
- `*.parquet`;
- `*.xlsx` real;
- `*.csv` real;
- `reports/`;
- `artifacts/`;
- `.validation_tmp/`;
- logs;
- installer gerado;
- credenciais;
- certificados;
- tokens.

## Primeiro pacote de PRs recomendado

1. Nucleo industrial privado.
2. Threads/Ocorrencias core.
3. BI/Snowflake readiness, quando acesso existir.
4. Release/installer readiness, quando aceite existir.

## Rollback

Se algo indevido for detectado antes do push:

```powershell
git remote remove origin
```

Se algo indevido for detectado depois do push:

- parar publicacao;
- tornar repo inacessivel se necessario;
- abrir incidente;
- rotacionar credenciais se houver;
- remover dado com procedimento de historia Git revisado por seguranca.
