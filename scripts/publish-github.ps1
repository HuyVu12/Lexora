param(
    [string]$RepositoryName = 'Lexora'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed with exit code $LASTEXITCODE."
    }
}

if ($RepositoryName -notmatch '^[A-Za-z0-9_.-]+$') {
    throw 'Invalid repository name.'
}

# Check identity before publishing anything.
$githubLogin = & gh api user --jq .login
if ($LASTEXITCODE -ne 0) {
    throw 'GitHub authentication unavailable. Run gh auth login, select HuyVu12, then retry.'
}
if (($githubLogin | Out-String).Trim() -ne 'HuyVu12') {
    throw 'Active GitHub account must be HuyVu12. Run gh auth switch --user HuyVu12, then retry.'
}

if (-not (Test-Path -LiteralPath '.git')) {
    Invoke-Checked git @('init', '-b', 'main')
}
Invoke-Checked git @('config', 'user.name', 'HuyVu12')
Invoke-Checked git @('config', 'user.email', 'HuyVu12@users.noreply.github.com')

function Commit-Group {
    param([string]$Message, [string[]]$Paths)
    Invoke-Checked git (@('add', '--') + $Paths)
    & git diff --cached --quiet
    $diffExit = $LASTEXITCODE
    if ($diffExit -eq 1) {
        Invoke-Checked git @('commit', '-m', $Message)
    } elseif ($diffExit -ne 0) {
        throw 'Unable to inspect staged changes.'
    }
}

$staged = & git diff --cached --name-only
if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect staging area.' }
if ($staged) { throw 'Staging area is not empty. Review existing staged changes first.' }

Commit-Group 'docs: add project proposal and repository guidelines' @(
    'AGENTS.md', 'docs/De_cuong_DATN_Legal_AI.docx.pdf'
)
Commit-Group 'chore: establish project structure and implementation planning' @(
    '.gitignore', '.env.example', 'README.md', 'apps', 'configs', 'data',
    'experiments', 'infra', 'prompts', 'scripts', 'src', 'tests',
    'docs/architecture.md', 'docs/annotation-guidelines.md',
    'docs/data-contracts.md', 'docs/evaluation-protocol.md', 'docs/report',
    'docs/decisions.md', 'docs/planning/implementation-plan.md'
)
Commit-Group 'docs: detail architecture algorithms and demo delivery plan' @(
    'docs/planning/technical-design-plan.md'
)

$fullName = "HuyVu12/$RepositoryName"
$expectedRemote = "https://github.com/$fullName.git"
$remoteNames = & git remote
if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect remotes.' }
if ($remoteNames -contains 'origin') {
    $originUrl = & git remote get-url origin
    if ($LASTEXITCODE -ne 0) { throw 'Unable to read origin.' }
    if ($originUrl -notin @($expectedRemote, "https://github.com/$fullName", "git@github.com:$fullName.git")) {
        throw "Existing origin does not match $fullName. Review it before continuing."
    }
    $repositoryInfo = & gh repo view $fullName --json visibility --jq .visibility
    if ($LASTEXITCODE -ne 0 -or $repositoryInfo -ne 'PUBLIC') {
        throw 'Existing repository is unavailable or is not public. Review it before continuing.'
    }
    Invoke-Checked git @('push', '-u', 'origin', 'main')
} else {
    Invoke-Checked gh @('repo', 'create', $fullName, '--public', '--source', '.', '--remote', 'origin', '--push', '--description', 'Lexora - Vietnamese labor law RAG with structured knowledge and verifiable citations')
}

Invoke-Checked gh @('repo', 'view', $fullName, '--json', 'url,visibility,owner')
Invoke-Checked git @('status', '--short')
