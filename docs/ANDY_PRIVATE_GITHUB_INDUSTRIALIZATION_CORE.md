# ANDY Private GitHub Industrialization Core

Data-base: 2026-07-10

## Status

Nucleo definido para registro em repositorio privado GitHub.

Este documento nao publica codigo, nao configura remote e nao executa push.
Ele define o nucleo que deve orientar a industrializacao do ANDY em um
repositorio privado.

## Premissa central

O ANDY industrial deve ser tratado como produto corporativo governado:

```text
engine Python analitica
-> runtime local seguro
-> desktop/exportacao
-> Threads/Ocorrencias
-> BI/Snowflake quando liberado
-> release/installer governado
```

A engine Python continua a fonte da verdade analitica. UI, BI, GitHub,
installer e automacoes sao camadas de distribuicao, operacao e governanca.

## Nucleo industrial versionavel

Entram no repositorio privado:

- codigo-fonte Python;
- testes automatizados;
- scripts de validacao;
- documentacao tecnica permanente;
- exemplos de configuracao `*.example.*`;
- contratos de dados e boundary;
- runbooks de release, seguranca e operacao;
- fixtures sinteticas pequenas, se revisadas e necessarias.

Nao entram:

- dados reais;
- `DuckDB`, `Parquet`, `CSV`, `XLSX` reais;
- exports;
- logs;
- reports runtime;
- artifacts;
- installers gerados;
- `.venv`;
- `.validation_tmp`;
- configs privadas;
- tokens, senhas, certificados ou chaves;
- paths corporativos sensiveis em arquivo versionado.

## Nucleo funcional inicial

O repositorio privado deve nascer com este nucleo controlado:

| Frente | Status de entrada | Observacao |
|---|---|---|
| Engine Python atual | baseline versionado existente | manter como fonte analitica |
| Runtime/source hygiene | baseline versionado existente | manter AppData/runtime fora do Git |
| Desktop PySide/exports | baseline existente | preservar comportamento funcional |
| Threads/Ocorrencias | preservado em stash | revisar e commitar em fase propria |
| BI Web/Snowflake | preparar, nao ativar | depende de acesso Snowflake e TI/BI |
| WPF/native | candidato futuro | depende de aceite visual/operacional |
| Installer/signing/update | readiness/dry-run | nao publicar sem aceite humano |

## Stashes preservados

Ha trabalho preservado fora da working tree:

- `ANDY Threads subset preserve before private repo core 2026-07-10`
- `ANDY tree cleanup preserve dirty work 2026-07-10`

Esses stashes devem ser tratados como filas de revisao, nao como lixo.

## Ordem de industrializacao recomendada

### Commit A - Private GitHub industrialization core

Conteudo:

- estes documentos de nucleo;
- runbook de registro privado;
- ledger de stashes.

Objetivo:

- criar marco limpo e auditavel antes de registrar/pushar.

### Commit B - Threads/Ocorrencias core

Conteudo:

- `andy_threads/`;
- configs `config/andy_threads_*.example.json`;
- scripts `scripts/check_andy_threads_*.py`;
- scripts `scripts/run_andy_threads_*.py`;
- testes `tests/test_andy_threads_*.py`;
- docs `docs/ANDY_THREADS_*.md`;
- docs `docs/ANDY_HUMAN_FEEDBACK_CAPTCHA_SCHEMA.md`;
- docs `docs/ANDY_SWITCHING_DETECTION_CONCEPT_BOUNDARIES.md`.

Regra:

- restaurar seletivamente do stash;
- rodar `pytest` Threads;
- rodar safety;
- commitar apenas se tudo passar.

### Commit C - BI/Snowflake readiness

Somente quando houver:

- conta/role/warehouse/database/schema;
- owner tecnico;
- owner funcional;
- politica RLS/ABAC;
- aprovacao de TI/BI.

### Commit D - Release/installer industrial

Somente quando houver:

- build reproduzivel;
- assinatura ou politica de assinatura;
- rollback;
- update strategy;
- aceite humano operacional.

## Politica de branches

Recomendado:

- `main`: protegido, sempre release-candidate ou baseline estavel;
- `develop`: integracao controlada;
- `feature/threads-*`: evolucao Threads;
- `feature/bi-*`: BI/Snowflake;
- `release/*`: preparo de instalador.

Regras:

- pull request obrigatorio para `main`;
- checks obrigatorios antes de merge;
- revisao humana para qualquer mudanca em engine/export/installer;
- nenhum dado real em branch.

## Gates minimos antes de push inicial

Antes do primeiro push privado:

```powershell
git status --short
py -3.12 scripts\check_andy_git_safety.py
py -3.12 scripts\check_andy_tracked_safety.py
git diff --check
```

Se a frente Threads for restaurada:

```powershell
py -3.12 -m pytest tests\test_andy_threads_*.py -q
py -3.12 scripts\check_andy_threads_readiness.py
```

## Criterio GO para repositorio privado

GO somente quando:

- working tree limpa;
- commit local do nucleo existe;
- remote ainda nao foi configurado automaticamente;
- URL privada foi revisada por humano;
- `git safety` e `tracked safety` passaram;
- nenhum artifact/dado real esta versionado;
- stashes importantes foram registrados em documento.

## Proxima decisao humana

Escolher nome e owner do repositorio privado:

```text
<GITHUB_ORG_OR_USER>/<PRIVATE_REPO_NAME>
```

Sugestao de nome:

```text
andy-vsigma
```

Visibilidade:

```text
private
```
