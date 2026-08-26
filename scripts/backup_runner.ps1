$ErrorActionPreference = "Stop"
$root   = "D:\Sanksrit Automatons\sanskrit-automatonv2"
$src    = Join-Path $root "data\context.db"
$dstDir = "D:\backups"
$log    = Join-Path $dstDir "backup_log.txt"
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$dated = Join-Path $dstDir ("context_" + (Get-Date -Format "yyyyMMdd") + ".db")
$daily = Join-Path $dstDir "context_daily.db"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "python" }

Add-Content $log "[$stamp] START  src=$src  py=$py  dst=$dated"
try {
    & $py (Join-Path $root "scripts\db_backup.py") $src $dated 2>&1 | Add-Content $log
    if ($LASTEXITCODE -ne 0) { throw "db_backup.py exited $LASTEXITCODE (source likely LOCKED by dashboard/job)" }
    Copy-Item $dated $daily -Force
    # keep only the 14 most-recent dated backups
    Get-ChildItem $dstDir -Filter "context_2*.db" | Sort-Object LastWriteTime -Descending |
        Select-Object -Skip 14 | Remove-Item -Force -ErrorAction SilentlyContinue
    Add-Content $log "[$stamp] OK     wrote $dated  and  $daily"
    exit 0
} catch {
    Add-Content $log "[$stamp] FAIL   $_"
    exit 1
}
