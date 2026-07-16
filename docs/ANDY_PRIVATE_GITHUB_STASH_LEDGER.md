# ANDY Private GitHub Stash Ledger

Data-base: 2026-07-10

## Objetivo

Registrar trabalho preservado fora da working tree antes da estruturacao para
repositorio privado GitHub.

Stash nao e descarte. Stash e fila de revisao.

## Stashes atuais

### ANDY Threads subset preserve before private repo core 2026-07-10

Conteudo esperado:

- nucleo `andy_threads/`;
- configs example de Threads;
- scripts/checks de Threads;
- scripts de demo Threads;
- testes de Threads;
- docs de Threads;
- guia de revisao humana;
- cenarios sinteticos setoriais.

Uso recomendado:

```powershell
git stash show --stat 'stash@{0}'
git stash apply 'stash@{0}'
```

Depois de aplicar:

```powershell
py -3.12 -m pytest tests\test_andy_threads_*.py -q
py -3.12 scripts\check_andy_threads_readiness.py
py -3.12 scripts\check_andy_git_safety.py
py -3.12 scripts\check_andy_tracked_safety.py
```

### ANDY tree cleanup preserve dirty work 2026-07-10

Conteudo esperado:

- trabalho amplo de fases anteriores;
- BI Web;
- WPF/native;
- docs extensos;
- scripts e testes de varias frentes;
- possiveis outputs/relatorios restauraveis.

Uso recomendado:

- nao aplicar inteiro sem revisao;
- preferir `git checkout 'stash@{N}^3' -- <path>` para restaurar subconjuntos;
- classificar antes de commitar.

## Politica de descarte

Nao dropar stash ate que:

- os commits correspondentes tenham sido revisados;
- os testes tenham passado;
- o repositorio privado tenha recebido o conteudo aprovado;
- nao exista risco de perda de trabalho.

Comando de descarte somente apos aprovacao humana:

```powershell
git stash drop 'stash@{N}'
```

## Ordem de revisao

1. Aplicar e commitar nucleo industrial privado.
2. Aplicar seletivamente Threads.
3. Aplicar seletivamente BI/Snowflake readiness quando acesso chegar.
4. Aplicar seletivamente WPF/release apenas com aceite humano.
