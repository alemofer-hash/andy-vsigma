Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

$distExe = Join-Path $repoRoot "dist\Sentinela\Sentinela.exe"
if (!(Test-Path $distExe)) {
    throw "Packaged executable not found at $distExe. Run scripts/build_exe.ps1 first."
}

$version = & $python -c "from andy_version import __version__; print(__version__)"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($version)) {
    throw "Could not resolve version from andy_version.py"
}

function Resolve-IsccPath {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    $cmd = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    throw "ISCC.exe not found. Install Inno Setup 6 and retry."
}

$iscc = Resolve-IsccPath
$iss = Join-Path $repoRoot "installer\ANDY.iss"

Write-Host "[build_installer] Using ISCC: $iscc"
Write-Host "[build_installer] Building Sentinela installer version $version"

& $iscc $iss "/DMyAppVersion=$version"

$outDir = Join-Path $repoRoot "artifacts\installer"
Write-Host "[build_installer] Output directory: $outDir"
