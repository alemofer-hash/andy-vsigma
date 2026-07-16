Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- NEW: cria ambiente virtual isolado para validacao ---
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".venv-validation"
$reqFile = Join-Path $repoRoot "requirements-validation.txt"

if (-not (Test-Path $reqFile)) {
    throw "Arquivo de dependencias nao encontrado: $reqFile"
}

if (-not (Test-Path $venvDir)) {
    $pythonBase = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
    if ($pythonBase -eq "py") {
        & py -3 -m venv --upgrade-deps $venvDir
    } else {
        & python -m venv --upgrade-deps $venvDir
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar .venv-validation."
    }
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Python do ambiente de validacao nao encontrado: $venvPython"
}

$pipCmd = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$pipBaseArgs = if ($pipCmd -eq "py") { @("-3", "-m", "pip") } else { @("-m", "pip") }

& $pipCmd @pipBaseArgs "--version" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel executar pip no Python base."
}

& $pipCmd @pipBaseArgs "--python" $venvPython "install" "-r" $reqFile
if ($LASTEXITCODE -ne 0) {
    $mainSitePackages = Join-Path $repoRoot ".venv\Lib\site-packages"
    $valSitePackages = Join-Path $venvDir "Lib\site-packages"
    if (Test-Path $mainSitePackages) {
        Write-Host "Falha ao instalar por pip. Aplicando fallback por copia de pacotes da .venv principal..."
        New-Item -ItemType Directory -Path $valSitePackages -Force | Out-Null
        Copy-Item -Path (Join-Path $mainSitePackages "*") -Destination $valSitePackages -Recurse -Force
    } else {
        throw "Falha ao instalar dependencias de validacao e fallback indisponivel."
    }
}

& $venvPython -m pytest --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Ambiente de validacao criado, mas pytest nao esta disponivel."
}

Write-Host ""
Write-Host "Validation environment ready:"
Write-Host "  venv:   $venvDir"
Write-Host "  python: $venvPython"
Write-Host ""
Write-Host "Proximo passo:"
Write-Host "  .\scripts\run_validation_suite.ps1"
