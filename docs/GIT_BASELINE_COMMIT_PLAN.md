# Git Baseline Commit Plan

Este plano prepara o baseline local restaurado do ANDY/Sentinela sem usar `git add .`.

## Commit Recomendado

```powershell
git commit -m "Restore ANDY Sentinela baseline"
```

Use o commit apenas depois de revisar:

```powershell
git status --short
git diff --cached --stat
git diff --cached --check
git diff --cached --name-only
.\.venv\Scripts\python.exe scripts\check_andy_git_safety.py
```

## Categorias Que Devem Entrar

- Código Python da engine e desktop.
- Núcleo Threads e neighbor detection.
- Preparação BI governada.
- Scripts de validação, release e empacotamento fonte.
- Testes.
- Config examples.
- Documentação permanente.
- Fonte do instalador (`installer/ANDY.iss`).
- Metadados de produto em `Sentinela/README.md`.

## Categorias Que Não Devem Entrar

- `.venv/`
- `build/`
- `dist/`
- `reports/`
- `.validation_tmp/`
- `.recovery_backups/`
- caches
- installers gerados
- logs
- exports
- runtime
- DuckDB/Parquet/SQLite
- CSV/XLSX reais ou gerados
- secrets/configs privadas.

## Staging Seguro

Staging explícito recomendado:

```powershell
git add .gitignore
git add README.md CHANGELOG.md README_logs.md RUN_SECURITY_CHECKS.md SECURITY_REQUIREMENTS_PROD.md
git add Sentinela/README.md
git add andy_bi/ andy_boundary/ andy_core/ andy_threads/ audit/ config/ db/ desktop_app/ docs/ installer/ scripts/ security/ tests/ utils/
git add andy_launcher.spec andy_version.py andys_indexer.py andys_report_runner.py andys_table_app.py andys_viewer.py
git add config.py launch_andy.py measurement_value.py pytest.ini
git add requirements.txt requirements-dev.txt requirements-validation.txt
git add runtime_bootstrap.py runtime_metadata.py runtime_paths.py structural_gate.py xlsx_selection.py
```

Nunca use `git add .` neste baseline.

## Validação Pós-Staging

```powershell
git diff --cached --stat
git diff --cached --check
git status --short
.\.venv\Scripts\python.exe scripts\check_andy_git_safety.py
.\.venv\Scripts\python.exe scripts\check_andy_threads_readiness.py
```

Se qualquer arquivo proibido aparecer no staged, remover com:

```powershell
git restore --staged <arquivo>
```
