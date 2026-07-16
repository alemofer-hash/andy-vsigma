# Git Prep Report

Status: GO para baseline local, com revisão humana antes do primeiro commit.

## Escopo

Esta preparação foi feita sobre a árvore restaurada em `C:\Users\G05835236\Downloads\ANDY_RESTORED`.

O objetivo é transformar a árvore restaurada em um repositório Git local seguro, sem carregar ambiente local, build, dist, runtime, logs, reports, dados operacionais, instaladores gerados ou credenciais.

## Estado Inicial

- `.git` não existia.
- `.gitignore` não existia.
- A árvore continha código-fonte, docs, testes, scripts, ambiente `.venv`, caches, `build/`, `dist/`, `reports/` e `.validation_tmp/`.
- O diretório `installer/` continha somente fonte de instalador (`ANDY.iss`) e README, portanto foi tratado como versionável.
- O diretório `Sentinela/` contém README de contexto do produto e foi tratado como documentação versionável.

## Ações Executadas

- Criado `.gitignore` conservador.
- Inicializado Git local com `git init`.
- Confirmado que `.venv/`, `dist/`, `build/`, `reports/`, `.validation_tmp/`, caches e artefatos são ignorados.
- Corrigida regra ampla de credenciais para não ignorar `desktop_app/layout_tokens.py`.
- Rodados gates de segurança disponíveis.

## Gates Executados

```powershell
git init
git check-ignore -v dist\Sentinela\_internal\base_library.zip
git check-ignore -v build\andy_launcher\base_library.zip
git check-ignore -v .venv\Scripts\python.exe
git check-ignore -v reports\ANDY_GIT_SAFETY_REPORT.md
git check-ignore -v .validation_tmp\probe.txt
git check-ignore -v desktop_app\layout_tokens.py
.\.venv\Scripts\python.exe scripts\check_andy_git_safety.py
.\.venv\Scripts\python.exe scripts\check_andy_tracked_safety.py
```

Resultados:

- `check_andy_git_safety.py`: passed.
- `check_andy_tracked_safety.py`: passed, com 0 arquivos tracked antes do baseline.
- `desktop_app/layout_tokens.py`: não está ignorado, como esperado.

## Fora Do Baseline

Por política, permanecem fora do Git:

- `.venv/`
- `.pytest_cache/`
- `.recovery_backups/`
- `.validation_tmp/`
- `__pycache__/`
- `build/`
- `dist/`
- `reports/`
- `artifacts/`
- `exports/`
- `logs/`
- arquivos `.duckdb`, `.parquet`, `.xlsx`, `.xlsm`, `.csv`, `.db`, `.sqlite`
- credenciais e configs privadas.

## Próximo Passo

Seguir `docs/GIT_BASELINE_COMMIT_PLAN.md` e revisar o staging antes do primeiro commit.
