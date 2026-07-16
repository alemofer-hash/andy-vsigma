Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "[build_exe] Using Python: $python"

& $python -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('PyInstaller') else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[build_exe] Installing PyInstaller..."
    & $python -m pip install "pyinstaller>=6.0,<7.0"
}

$version = & $python -c "from andy_version import __version__; print(__version__)"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($version)) {
    throw "Could not resolve version from andy_version.py"
}

Write-Host "[build_exe] Building Sentinela $version"
& $python -m PyInstaller --noconfirm --clean .\andy_launcher.spec

$distExe = Join-Path $repoRoot "dist\Sentinela\Sentinela.exe"
if (!(Test-Path $distExe)) {
    throw "Build finished but executable not found: $distExe"
}

$versionFile = Join-Path $repoRoot "dist\Sentinela\VERSION.txt"
"$version" | Set-Content -Path $versionFile -Encoding utf8

Write-Host "[build_exe] OK: $distExe"
