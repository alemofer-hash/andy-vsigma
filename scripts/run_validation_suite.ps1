param(
    [switch]$Bootstrap,
    [string]$ReportPath = "artifacts/validation_report.log"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- NEW: executa suite de validacao isolada com relatorio ---
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".venv-validation"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$bootstrapScript = Join-Path $PSScriptRoot "bootstrap_validation_env.ps1"
$artifactsDir = Join-Path $repoRoot "artifacts"
$validationTmp = Join-Path $repoRoot ".validation_tmp"
$reportFile = Join-Path $repoRoot $ReportPath
$junitFile = Join-Path $artifactsDir "validation_junit.xml"

if ($Bootstrap -or -not (Test-Path $venvPython)) {
    & $bootstrapScript
}

if (-not (Test-Path $venvPython)) {
    throw "Ambiente de validacao ausente. Rode .\scripts\bootstrap_validation_env.ps1"
}

& $venvPython -m pytest --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    & $bootstrapScript
}

New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null
New-Item -ItemType Directory -Path $validationTmp -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $reportFile) -Force | Out-Null

$env:ANDYS_ENV = "dev"
$env:ANDYS_ALLOWED_ROOT = $validationTmp
$env:ANDYS_WORK_ROOT = (Join-Path $validationTmp "work_root")
$env:ANDYS_SOURCE_ROOT = (Join-Path $validationTmp "source_root")
$env:ANDYS_EXPORT_DIR = (Join-Path $validationTmp "exports")
$env:ANDYS_AUDIT_LOG_PATH = (Join-Path $validationTmp "audit\audit.jsonl")
$env:PYTHONDONTWRITEBYTECODE = "1"

$targets = @(
    "tests/validation",
    "tests/test_point_id_limit_fix.py"
)

$pytestArgs = @(
    "-m", "pytest",
    "-ra",
    "-q",
    "--tb=short",
    "--maxfail=1",
    "--disable-warnings",
    "-p", "no:cacheprovider",
    "--junitxml", $junitFile
) + $targets

Write-Host "Running ANDY validation suite..."
Write-Host "Report: $reportFile"
Write-Host ""
$exitCode = 1
Start-Transcript -Path $reportFile -Force | Out-Null
try {
    & $venvPython @pytestArgs
    $exitCode = $LASTEXITCODE
}
finally {
    Stop-Transcript | Out-Null
}

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "VALIDATION PASSED"
} else {
    Write-Host "VALIDATION FAILED (exit code $exitCode)"
}

$testsTotal = 0
$failTotal = 0
$skipTotal = 0
if (Test-Path $junitFile) {
    [xml]$jx = Get-Content $junitFile
    if ($jx.testsuites -and $jx.testsuites.testsuite) {
        foreach ($suite in @($jx.testsuites.testsuite)) {
            $testsTotal += [int]($suite.tests)
            $failTotal += [int]($suite.failures) + [int]($suite.errors)
            $skipTotal += [int]($suite.skipped)
        }
    } elseif ($jx.testsuite) {
        $testsTotal = [int]($jx.testsuite.tests)
        $failTotal = [int]($jx.testsuite.failures) + [int]($jx.testsuite.errors)
        $skipTotal = [int]($jx.testsuite.skipped)
    }
}

$featureFamilies = (Get-ChildItem (Join-Path $repoRoot "tests\\validation") -Filter "test_*combinatorial*.py" -File -ErrorAction SilentlyContinue).Count
if ($featureFamilies -lt 1) { $featureFamilies = 1 }

Write-Host "Combinatorial cases executed: $testsTotal"
Write-Host "Feature families covered:    $featureFamilies"
Write-Host "Failed combinations:         $failTotal"
Write-Host "Skipped combinations:        $skipTotal"

Write-Host "Artifacts:"
Write-Host "  - $reportFile"
Write-Host "  - $junitFile"
Write-Host "  - $validationTmp"

exit $exitCode
