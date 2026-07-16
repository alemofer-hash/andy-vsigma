Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

$distExe = Join-Path $repoRoot "dist\ANDY\ANDY.exe"
if (!(Test-Path $distExe)) {
    throw "Packaged executable not found at $distExe. Run scripts/build_exe.ps1 first."
}

$metadataRaw = & $python -c "from andy_version import APP_NAME, APP_PUBLISHER, APP_URL, __version__; print(APP_NAME); print(APP_PUBLISHER); print(APP_URL); print(__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "Could not resolve update metadata from andy_version.py"
}
$metadataLines = @($metadataRaw | ForEach-Object { $_.ToString().Trim() })
if ($metadataLines.Count -lt 4) {
    throw "Incomplete update metadata returned from andy_version.py"
}
$appName = $metadataLines[0]
$appPublisher = $metadataLines[1]
$appUrl = $metadataLines[2]
$version = $metadataLines[3]
if ([string]::IsNullOrWhiteSpace($appName) -or [string]::IsNullOrWhiteSpace($appPublisher) -or [string]::IsNullOrWhiteSpace($version)) {
    throw "Invalid update metadata resolved from andy_version.py"
}

function Resolve-IsccPath {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
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

Write-Host "[build_update] Using ISCC: $iscc"
Write-Host "[build_update] Building update package version $version"

& $iscc $iss "/DMyAppName=$appName" "/DMyAppPublisher=$appPublisher" "/DMyAppURL=$appUrl" "/DMyAppVersion=$version" "/DUpdateMode=1"
if ($LASTEXITCODE -ne 0) {
    throw "ISCC failed while building update package (exit code $LASTEXITCODE)."
}

$outDir = Join-Path $repoRoot "artifacts\updates"
$expectedArtifact = Join-Path $outDir ("{0}-Update-{1}.exe" -f $appName, $version)
if (!(Test-Path $expectedArtifact)) {
    throw "Update build finished but artifact not found: $expectedArtifact"
}

$updateInfo = Join-Path $outDir "UPDATE_INFO.txt"
@(
    "name=$appName"
    "publisher=$appPublisher"
    "url=$appUrl"
    "version=$version"
    "artifact=$expectedArtifact"
) | Set-Content -Path $updateInfo -Encoding utf8

Write-Host "[build_update] Output directory: $outDir"
Write-Host "[build_update] Artifact: $expectedArtifact"
Write-Host "[build_update] Metadata: $updateInfo"
