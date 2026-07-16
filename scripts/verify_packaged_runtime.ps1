Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$distRoot = Join-Path $repoRoot "dist\ANDY\_internal"
if (!(Test-Path $distRoot)) {
    throw "Packaged runtime not found: $distRoot. Run scripts/build_exe.ps1 first."
}

function Assert-PathExists {
    param(
        [Parameter(Mandatory = $true)][string]$PathToCheck,
        [Parameter(Mandatory = $true)][string]$Description
    )
    if (!(Test-Path $PathToCheck)) {
        throw "Missing $Description at $PathToCheck"
    }
    Write-Host "[verify_packaged_runtime] OK: $Description"
}

function Assert-DistInfoPresent {
    param([Parameter(Mandatory = $true)][string]$PackageName)
    $pattern = "{0}-*.dist-info" -f $PackageName
    $matches = Get-ChildItem -Path $distRoot -Directory -Filter $pattern -ErrorAction SilentlyContinue
    if (-not $matches) {
        throw "Missing package metadata in bundle: $pattern under $distRoot"
    }
    $names = ($matches | Select-Object -ExpandProperty Name) -join ", "
    Write-Host "[verify_packaged_runtime] OK: $PackageName metadata => $names"
}

Assert-PathExists -PathToCheck (Join-Path $repoRoot "dist\ANDY\ANDY.exe") -Description "launcher executable"
Assert-PathExists -PathToCheck (Join-Path $distRoot "streamlit") -Description "streamlit package"
Assert-PathExists -PathToCheck (Join-Path $distRoot "streamlit\static\index.html") -Description "streamlit static assets"

Assert-DistInfoPresent -PackageName "streamlit"
Assert-DistInfoPresent -PackageName "altair"
Assert-DistInfoPresent -PackageName "click"
Assert-DistInfoPresent -PackageName "tornado"

Write-Host "[verify_packaged_runtime] Packaged runtime checks passed."
