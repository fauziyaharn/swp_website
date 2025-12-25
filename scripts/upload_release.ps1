<#
PowerShell helper to upload a file as a GitHub Release asset using `gh`.
Usage:
  .\upload_release.ps1 -FilePath "C:\path\to\model.pt" -Tag "model-v1" -Repo "owner/repo" -Title "Model v1" -Notes "Release of model"

If `-Repo` is omitted the script will try to read the `remote.origin.url` from git and derive owner/repo.
Requires: GitHub CLI `gh` installed and authenticated (`gh auth login`).
#>
param(
    [Parameter(Mandatory=$true)][string]$FilePath,
    [string]$Tag = $("model-" + (Get-Date -Format yyyyMMdd-HHmmss)),
    [string]$Repo = $null,
    [string]$Title = $null,
    [string]$Notes = "Uploaded by upload_release.ps1",
    [switch]$Prerelease
)

function Fail([string]$msg){ Write-Error $msg; exit 1 }

if (-not (Get-Command gh -ErrorAction SilentlyContinue)){
    Fail "GitHub CLI 'gh' not found. Install from https://cli.github.com/ and run 'gh auth login'."
}

if (-not (Test-Path $FilePath)){
    Fail "File not found: $FilePath"
}

if (-not $Repo){
    $origin = (& git config --get remote.origin.url) 2>$null
    if (-not $origin){
        Fail "Could not determine repo from git remote. Pass -Repo 'owner/repo' explicitly."
    }
    # parse origin to owner/repo
    if ($origin -match "github.com[:/](.+?)(?:\.git)?$"){
        $Repo = $matches[1]
    }
}

if (-not $Title){ $Title = $Tag }

Write-Host "Uploading '$FilePath' to release '$Tag' in repo '$Repo'..."

$createArgs = @($Tag, $FilePath, "--repo", $Repo, "--title", $Title, "--notes", $Notes)
if ($Prerelease){ $createArgs += "--prerelease" }

$proc = Start-Process -FilePath gh -ArgumentList ( $createArgs ) -NoNewWindow -PassThru -Wait -RedirectStandardOutput -RedirectStandardError
$stdout = $proc.StandardOutput.ReadToEnd()
$stderr = $proc.StandardError.ReadToEnd()

if ($proc.ExitCode -ne 0){
    Write-Error "gh returned exit code $($proc.ExitCode)"
    Write-Error $stderr
    exit $proc.ExitCode
}

Write-Host "Release created/updated successfully. Output:"
Write-Host $stdout

# try to extract upload url
if ($stdout -match "https:\/\/github.com\/.+?/releases\/tag\/.+" ){
    $url = ($stdout -split "\r?\n" | Where-Object { $_ -match "https:\/\/github.com\/.+?/releases\/tag\/.+" })[-1]
    Write-Host "Release page: $url"
}

Write-Host "Done."