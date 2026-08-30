param(
    [string]$Repo    = "D:\Sanksrit Automatons\sanskrit-automatonv2",
    [string]$Message = "",
    [string]$MessageFile = "",
    [switch]$ClearLocks,
    [switch]$Apply
)

# release.ps1 - commit and push one repo, safely and repeatably. (2026-08-30)
#
# WHY THIS EXISTS
# ---------------
# Releasing by pasting git commands into a console failed three separate ways
# on 2026-08-30 and every failure was silent or misleading:
#
#   1. A stale .git/index.lock blocked `git add` and `git commit`. The lock was
#      left by a read-only `git status` run over a file bridge that cannot
#      delete files, so git could create the lock but never remove it.
#   2. `git push` then printed "Everything up-to-date" - which was TRUE and
#      useless: nothing had been committed, so there was nothing to push. A
#      success message for work that never happened is worse than an error.
#   3. A multi-line -m message full of $ and backticks is a PowerShell
#      interpolation minefield. Commit messages belong in a FILE.
#
# So this script: detects stale locks and only clears them when provably safe,
# refuses to stage anything large or ignored, commits from a file, pushes, and
# then VERIFIES that the remote actually moved. Dry-run unless -Apply.
#
#   powershell -ExecutionPolicy Bypass -File scripts\release.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\release.ps1 -ClearLocks
#   powershell -ExecutionPolicy Bypass -File scripts\release.ps1 -MessageFile COMMIT_MSG.txt -Apply

$ErrorActionPreference = "Stop"
$MaxFileMB = 5

function Say([string]$t, [string]$c = "Gray") { Write-Host $t -ForegroundColor $c }
function Fail([string]$t) { Say "FAIL: $t" "Red"; exit 1 }

if (-not (Test-Path (Join-Path $Repo ".git"))) { Fail "not a git repo: $Repo" }
Set-Location $Repo
Say "repo: $Repo" "Cyan"
Say ("mode: " + $(if ($Apply) { "APPLY" } else { "DRY-RUN (add -Apply to commit and push)" })) "Cyan"

# ---- 1. stale locks -------------------------------------------------------
$locks = @(".git\index.lock", ".git\HEAD.lock", ".git\config.lock")
$found = @()
foreach ($l in $locks) { if (Test-Path $l) { $found += Get-Item $l } }
if ($found.Count -gt 0) {
    Say "`n[locks] $($found.Count) lock file(s) present:" "Yellow"
    foreach ($f in $found) {
        $age = [int]((Get-Date) - $f.LastWriteTime).TotalMinutes
        Say ("  {0}  {1} bytes  {2} min old" -f $f.Name, $f.Length, $age) "Yellow"
    }
    $running = @(Get-Process git -ErrorAction SilentlyContinue).Count
    Say "  git processes running on this machine: $running"
    $safe = ($running -eq 0) -and (($found | Where-Object { $_.Length -gt 0 }).Count -eq 0)
    if (-not $safe) {
        Fail "a lock is non-empty or git is running - do NOT clear it. Close any git client (VS Code, GitHub Desktop, Fork) and re-run."
    }
    if (-not $ClearLocks) {
        Say "  All locks are zero-length and no git process is running, so they are stale." "Yellow"
        Say "  Re-run with -ClearLocks to remove them." "Yellow"
        exit 2
    }
    foreach ($f in $found) { Remove-Item $f.FullName -Force; Say "  removed $($f.Name)" "Green" }
}

# ---- 2. what would be committed -------------------------------------------
$status = @(git status --porcelain)
if ($status.Count -eq 0) { Say "`nnothing to commit - working tree clean." "Green"; }
else { Say "`n[changes] $($status.Count) path(s)" "Cyan" }

# ---- 3. refuse anything large or that should be ignored -------------------
Say "`n[safety] checking for large or excluded paths..."
$bad = @()
foreach ($line in $status) {
    $p = $line.Substring(3).Trim('"')
    if ($p -match '(^|/|\\)(backups|raw_vision|raw_merged|probe)(/|\\)') { $bad += "excluded dir: $p"; continue }
    if ($p -match 'context\.db') { $bad += "database: $p"; continue }
    if ($p.EndsWith("/") -or $p.EndsWith("\")) { continue }
    if (Test-Path $p) {
        $mb = (Get-Item $p).Length / 1MB
        if ($mb -gt $MaxFileMB) { $bad += ("large file ({0:N1} MB): {1}" -f $mb, $p) }
    }
}
if ($bad.Count -gt 0) {
    Say "  REFUSING - these must be added to .gitignore first:" "Red"
    $bad | ForEach-Object { Say "    $_" "Red" }
    Fail "nothing was staged"
}
Say "  clean - no database, backup, OCR working dir, or file over $MaxFileMB MB" "Green"

# ---- 4. commit message ----------------------------------------------------
if (-not $Apply) {
    Say "`n[dry-run] would stage $($status.Count) path(s) and commit." "Cyan"
    git status --short
    exit 0
}
if ($MessageFile -and (Test-Path $MessageFile)) { Say "`nmessage from: $MessageFile" }
elseif ($Message) { Say "`nmessage: inline" }
else { Fail "give -MessageFile <path> (preferred) or -Message '<text>'" }

# ---- 5. stage, commit, push ----------------------------------------------
$before = (git rev-parse HEAD).Trim()
git add -A
if ($LASTEXITCODE -ne 0) { Fail "git add failed" }

if ($MessageFile) { git commit -F $MessageFile } else { git commit -m $Message }
if ($LASTEXITCODE -ne 0) { Fail "git commit failed (nothing staged, or hook rejected)" }

$after = (git rev-parse HEAD).Trim()
if ($before -eq $after) { Fail "HEAD did not move - no commit was created" }
Say "`ncommitted: $($after.Substring(0,8))" "Green"

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
git push origin $branch
if ($LASTEXITCODE -ne 0) { Fail "git push failed" }

# ---- 6. VERIFY the remote actually moved ---------------------------------
# "Everything up-to-date" is printed when there is nothing to push, which is
# exactly what a failed commit looks like. Trust the refs, not the message.
git fetch origin $branch --quiet
$remote = (git rev-parse "origin/$branch").Trim()
if ($remote -ne $after) {
    Fail "remote is at $($remote.Substring(0,8)) but local HEAD is $($after.Substring(0,8)) - push did NOT land"
}
Say "verified: origin/$branch == local HEAD ($($after.Substring(0,8)))" "Green"
Say "`nRelease complete." "Green"
