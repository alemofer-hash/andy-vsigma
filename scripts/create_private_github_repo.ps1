param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_.-]+$')]
    [string]$Owner,

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_.-]+$')]
    [string]$Repo = "andy-vsigma",

    [Parameter(Mandatory = $false)]
    [ValidateSet("private", "internal")]
    [string]$Visibility = "private",

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9._/-]+$')]
    [string]$Branch = "main",

    [Parameter(Mandatory = $false)]
    [string]$Description = "ANDY vSigma - governed Python analytics engine, desktop runtime and corporate BI readiness.",

    [switch]$Execute,
    [switch]$NoPush,
    [switch]$AllowExistingOrigin,
    [switch]$SkipSafetyChecks
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[ANDY GitHub] $Message"
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $false)]
        [string[]]$Arguments = @()
    )
    Write-Step ("run: {0} {1}" -f $FilePath, ($Arguments -join " "))
    if ($Execute) {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $FilePath $($Arguments -join ' ')"
        }
    }
}

function Assert-CleanWorktree {
    $dirty = git status --porcelain=v1
    if ($dirty.Count -gt 0) {
        $preview = ($dirty | Select-Object -First 20) -join [Environment]::NewLine
        throw "Working tree is not clean. Refusing to create/push private repo. First entries:$([Environment]::NewLine)$preview"
    }
}

function Assert-NoOriginRemote {
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $origin = git remote get-url origin 2>$null
        $originExitCode = $LASTEXITCODE
    }
    catch {
        $origin = $null
        $originExitCode = 1
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($originExitCode -eq 0 -and -not $AllowExistingOrigin) {
        throw "Remote 'origin' already exists. Use -AllowExistingOrigin only after human review."
    }
    $global:LASTEXITCODE = 0
}

function Assert-ToolAvailable {
    param([string]$Name)
    $tool = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $tool) {
        throw "Required tool not found in PATH: $Name"
    }
}

function Invoke-SafetyChecks {
    if ($SkipSafetyChecks) {
        Write-Step "safety checks skipped by explicit flag"
        return
    }
    if (-not (Test-Path "scripts\check_andy_git_safety.py")) {
        throw "Missing scripts\check_andy_git_safety.py"
    }
    if (-not (Test-Path "scripts\check_andy_tracked_safety.py")) {
        throw "Missing scripts\check_andy_tracked_safety.py"
    }
    Invoke-Checked "py" @("-3.12", "scripts\check_andy_git_safety.py")
    Invoke-Checked "py" @("-3.12", "scripts\check_andy_tracked_safety.py")
}

function Invoke-GitHubAuthCheck {
    Write-Step "run: gh auth status"
    if ($Execute) {
        gh auth status
        if ($LASTEXITCODE -ne 0) {
            throw "GitHub CLI is not authenticated. Run: gh auth login"
        }
    }
}

function Assert-RemoteRepoDoesNotExist {
    $fullName = "$Owner/$Repo"
    Write-Step "check remote repo availability: $fullName"
    if ($Execute) {
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            gh repo view $fullName *> $null
            $repoViewExitCode = $LASTEXITCODE
        }
        catch {
            $repoViewExitCode = 1
        }
        finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }

        if ($repoViewExitCode -eq 0) {
            throw "GitHub repository already exists: $fullName"
        }
        Write-Step "remote repo not found; creation can proceed"
        $global:LASTEXITCODE = 0
    }
}

function Invoke-BranchRename {
    $currentBranch = git branch --show-current
    if ($currentBranch -ne $Branch) {
        Invoke-Checked "git" @("branch", "-M", $Branch)
    }
    else {
        Write-Step "branch already '$Branch'"
    }
}

function Invoke-RepoCreate {
    $fullName = "$Owner/$Repo"
    $args = @("repo", "create", $fullName, "--$Visibility", "--source=.", "--remote=origin", "--description", $Description)
    if (-not $NoPush) {
        $args += "--push"
    }
    Invoke-Checked "gh" $args
}

Push-Location (Resolve-Path ".")
try {
    if (-not (Test-Path ".git")) {
        throw "This command must be run from the ANDY Git repository root."
    }

    Write-Step "mode: $(@('DRY-RUN', 'EXECUTE')[[int]$Execute.IsPresent])"
    Write-Step "target: $Owner/$Repo"
    Write-Step "visibility: $Visibility"
    Write-Step "branch: $Branch"
    Write-Step "push: $(-not $NoPush)"

    Assert-ToolAvailable "git"
    if ($Execute) {
        Assert-ToolAvailable "gh"
    }

    Assert-CleanWorktree
    Assert-NoOriginRemote
    Invoke-SafetyChecks
    Invoke-GitHubAuthCheck
    Assert-RemoteRepoDoesNotExist
    Invoke-BranchRename
    Invoke-RepoCreate

    if ($Execute) {
        Write-Step "remote status"
        git remote -v
        Write-Step "final git status"
        git status --short
        Write-Step "private repository ready: $Owner/$Repo"
    }
    else {
        Write-Step "dry-run complete. Re-run with -Execute to create the private GitHub repo."
    }
}
finally {
    Pop-Location
}
