# Validation Workspace (ANDY)

Este workspace executa validacao **combinatoria exaustiva** em um dominio canonico finito, isolado da operacao normal do projeto.

## 1) Bootstrap do ambiente de validacao

```powershell
.\scripts\bootstrap_validation_env.ps1
```

Isso cria `.venv-validation` e instala `requirements-validation.txt`.
Se o ambiente bloquear install via indice externo, o bootstrap aplica fallback local copiando pacotes da `.venv` principal.

## 2) Rodar a suite completa de validacao

```powershell
.\scripts\run_validation_suite.ps1
```

Atalho `.bat`:

```bat
.\scripts\run_validation_suite.bat
```

## 3) Dominio canonico combinatorio

Dentro da fixture de validacao, o dominio e explicitamente limitado e totalmente enumerado:

- Periodos: `(2025,1)`, `(2025,2)`, `(2026,1)`
- `SE`: `SE1`, `SE2`
- `BAY`: `BAY_A`, `BAY_B` (mais casos com `BAY` vazio no dataset)
- `EQUIPAMENTO`: `TR-1`, `AL-1`
- `TERMINAL`: `Terminal1`, `Terminal2` (mais casos com terminal vazio no dataset)
- Variaveis padrao: `IA`, `IB`, `VAB`
- Variavel custom: `CUSTOM_X`

Matriz principal de filtros: `3 x 2^2 x 2^2 x 2^2 x 2^2 = 768` combinacoes.

## 4) Familias cobertas

- ingestao combinatoria (CSV/XLSX, vars padrao/custom, contexto completo/incompleto)
- filtros hierarquicos e resolucao interna de pontos (cartesiano exaustivo)
- query builder seguro em combinacoes de clausulas
- caminho principal de consulta/paginacao (`query_page`)
- export combinatorio (CSV long + wide + XLSX)
- dashboard combinatorio (series por BAY/terminal/variavel)
- compatibilidade `ponto_id -> {"EQUIPAMENTO":[vars...]}` para XLSX

## 5) Isolamento e artefatos

O runner seta variaveis de ambiente para caminhos locais temporarios em `.validation_tmp/`:

- `ANDYS_ALLOWED_ROOT`
- `ANDYS_WORK_ROOT`
- `ANDYS_SOURCE_ROOT`
- `ANDYS_EXPORT_DIR`
- `ANDYS_AUDIT_LOG_PATH`

Relatorio:

- `artifacts/validation_report.log`
- `artifacts/validation_junit.xml`

## 6) Executar apenas a suite de validacao

```powershell
.\.venv-validation\Scripts\python.exe -m pytest -q -ra tests/validation
```

## 7) Suites combinatorias

- `tests/validation/test_ingestion_combinatorial.py`
- `tests/validation/test_filters_combinatorial.py`
- `tests/validation/test_exports_combinatorial.py`
- `tests/validation/test_dashboard_combinatorial.py`
- `tests/validation/test_combinatorial_validation.py`
