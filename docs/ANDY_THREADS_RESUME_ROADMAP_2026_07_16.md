# ANDY/Sentinela Threads - Roadmap de Retomada

Data-base: 2026-07-16

## 1. Situacao atual verificada nesta sessao

### 1.1 Fonte de desenvolvimento Threads

Nao foi localizada nesta maquina, nesta sessao, uma arvore contendo:

- `andy_threads/`
- `andy_threads_ui/`
- checkout Git em `C:\Users\G05835236\Downloads\ANDY`

Buscas realizadas:

- `C:\Users\G05835236\Downloads`
- `C:\Users\G05835236\Documents`
- perfil do usuario para diretorios `andy_threads` e `andy_threads_ui`

Resultado: a fonte de desenvolvimento do Threads nao esta disponivel no caminho usado nas sessoes anteriores.

### 1.2 Artefato de usuario disponivel

Foi encontrado:

```text
C:\Users\G05835236\Downloads\Sentinela.zip
```

Conteudo do ZIP:

```text
Sentinela.exe
```

Nao foram encontrados, nos caminhos esperados:

```text
C:\Users\G05835236\AppData\Local\Programs\Sentinela\Sentinela.exe
C:\Users\G05835236\AppData\Local\Programs\Andy 4.0\Sentinela.exe
C:\Users\G05835236\Downloads\ANDY\artifacts\installer\Sentinela-Setup-1.0.0.exe
```

### 1.3 Conclusao operacional

Hoje, o que pode ser testado imediatamente como usuario e o executavel portatil dentro de `Sentinela.zip`.

Para retomar desenvolvimento real do Threads, e necessario restaurar/localizar a arvore fonte que contem `andy_threads/` e `andy_threads_ui/`, ou recuperar o repositorio privado/local onde essa etapa foi versionada.

## 2. Como testar hoje como usuario

### 2.1 Abrir versao portatil disponivel

Executar no PowerShell:

```powershell
$zip = "$env:USERPROFILE\Downloads\Sentinela.zip"
$dest = Join-Path $env:TEMP ("SentinelaUserTest_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force
Start-Process -FilePath (Join-Path $dest "Sentinela.exe")
```

O usuario deve validar:

1. o aplicativo abre sem terminal/popup indevido;
2. a tela inicial identifica Sentinela;
3. a fonte de dados pode ser selecionada;
4. os filtros carregam;
5. a analise/exportacao principal funciona;
6. a aba Manobras aparece no XLSX quando houver candidatos;
7. o dashboard final contem Patamar completo.

### 2.2 Coletar log apos teste

Depois de fechar o app, procurar logs em:

```powershell
Get-ChildItem "$env:LOCALAPPDATA\ANDY" -Recurse -Filter "*.log" -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 10 FullName,LastWriteTime,Length
```

Observacao: o runtime legado pode continuar em `%LOCALAPPDATA%\ANDY` por compatibilidade, mesmo com o produto visualmente renomeado para Sentinela.

## 3. Como testar Threads quando a fonte for restaurada

Quando o checkout com `andy_threads/` e `andy_threads_ui/` estiver disponivel:

```powershell
cd <CAMINHO_DO_REPOSITORIO_SENTINELA>

py -3.12 -m compileall -q andy_threads
py -3.12 -m pytest -q tests\test_andy_threads*.py
py -3.12 scripts\check_andy_threads_readiness.py
```

Para abrir a interface web mock do Threads:

```powershell
cd <CAMINHO_DO_REPOSITORIO_SENTINELA>\andy_threads_ui
npm install
npm run dev
Start-Process "http://localhost:3000"
```

Se existir script `package.json` especifico:

```powershell
npm run lint
npm run test
npm run build
npx playwright test
```

## 4. Roadmap de retomada

### Fase T0 - Recuperar fonte canonica

Objetivo: garantir que a arvore de desenvolvimento certa esta aberta.

Pronto quando:

- existe `.git`;
- existem `andy_threads/` e `andy_threads_ui/`;
- `git status --short` foi registrado;
- nenhum dado real/runtime/artifact entra no versionamento.

### Fase T1 - Readiness do core Threads

Objetivo: confirmar que o nucleo Python ainda passa.

Escopo:

- models;
- ocorrencias;
- referencias tecnicas;
- policy/responsibility;
- feedback humano;
- NotificationIntent desligado;
- store local;
- audit.

Pronto quando:

- testes `test_andy_threads*.py` passam;
- readiness passa;
- providers reais continuam desligados.

### Fase T2 - Abrir UX como usuario

Objetivo: testar a experiencia clicavel.

Escopo:

- fila de ocorrencias;
- evidencia;
- thread contextual;
- validacao humana;
- status/auditoria mock;
- estados de loading/erro.

Pronto quando:

- `npm run dev` abre no navegador;
- usuario consegue abrir ocorrencia, comentar, validar e ver auditoria mock;
- `training_use=false` por padrao.

### Fase T3 - Conectar UX a API local segura

Objetivo: sair do mock puro para API local sem providers reais.

Escopo:

- endpoints locais;
- SQLite local ou store controlado;
- policy deny-by-default;
- notificacao apenas como intent, sem envio real.

Pronto quando:

- UI consome API local;
- logs/auditoria sao gerados;
- nenhum e-mail/Teams/provider real dispara.

### Fase T4 - Integrar eventos do dashboard/manobras

Objetivo: transformar deteccoes em ocorrencias revisaveis.

Escopo:

- inversao de fluxo;
- candidatos de manobra;
- patamar/qualidade;
- contexto tecnico do recorte;
- validacao humana obrigatoria.

Pronto quando:

- evento candidato vira ocorrencia;
- nenhuma ocorrencia e confirmada automaticamente;
- labels humanos ficam prontos para dataset futuro.

### Fase T5 - Demo operacional de engenharia

Objetivo: preparar fluxo para revisao com Engenharia/Operacao.

Pronto quando:

- 5 cenarios sinteticos setoriais existem;
- roteiro de revisao humana existe;
- coleta de feedback esta padronizada;
- decisoes futuras para API/store corporativo ficam claras.

## 5. Bloqueadores atuais

1. A fonte `andy_threads/` e `andy_threads_ui/` nao foi localizada nesta sessao.
2. O instalador `Sentinela-Setup-1.0.0.exe` nao esta no caminho antigo.
3. Ha apenas um ZIP portatil com `Sentinela.exe` disponivel para teste imediato.
4. Para desenvolvimento Threads real, e preciso recuperar o repo canonico ou apontar o novo caminho.

## 6. Proximo comando recomendado

Se o objetivo agora e testar como usuario:

```powershell
$zip = "$env:USERPROFILE\Downloads\Sentinela.zip"
$dest = Join-Path $env:TEMP ("SentinelaUserTest_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force
Start-Process -FilePath (Join-Path $dest "Sentinela.exe")
```

Se o objetivo e continuar desenvolvimento Threads:

```powershell
Get-ChildItem "$env:USERPROFILE" -Directory -Recurse -ErrorAction SilentlyContinue |
  Where-Object { Test-Path (Join-Path $_.FullName "andy_threads") -or Test-Path (Join-Path $_.FullName "andy_threads_ui") } |
  Select-Object FullName
```
