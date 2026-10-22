param(
    [string]$Repo    = "D:\Sanksrit Automatons\sanskrit-automatonv2",
    [string]$Pattern = "test_*.py",
    [string]$Python  = "python",
    [switch]$Show
)

# run_tests.ps1 - the whole test suite, one module at a time, as the dashboard runs its jobs. (TEST_ENV_2026_10_22)
#
# WHY THIS EXISTS
# ---------------
# Python on Windows writes to a pipe in the console's code page (cp1252), not UTF-8. A test whose script prints
# Devanagari or IAST passes in the console but fails with UnicodeEncodeError the moment its output is piped
# ("2>&1 | ..."): on 22 Oct eight modules failed so (test_mbh_prose, the bench tests, test_ocr_consensus, and
# test_docs76's patcher, whose child printed a title in IAST), for no fault of their own. The dashboard runs every
# job with PYTHONUTF8=1 and PYTHONIOENCODING=utf-8 (scripts\dashboard.py); this runs the tests the same way, for
# this window only: nothing is set for the machine or the account.
#
#   powershell -ExecutionPolicy Bypass -File scripts\run_tests.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\run_tests.ps1 -Pattern "test_etext_*.py" -Show
#
# Prints each failing module's verdict (with -Show, its output too), the modules that hold no unittest tests, and
# the totals; exits 1 if a module fails, else 0.

$ErrorActionPreference = "Continue"
if (-not (Test-Path (Join-Path $Repo "tests"))) { Write-Host "FAIL: no tests folder in $Repo" -ForegroundColor Red; exit 2 }
Set-Location $Repo
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"

$mods = @(Get-ChildItem (Join-Path $Repo "tests") -Filter $Pattern | Where-Object { $_.Extension -eq ".py" } | Sort-Object Name)
$fail = @(); $none = @(); $ran = 0; $skipped = 0
foreach ($f in $mods) {
    $m = "tests." + $f.BaseName
    $o = (& $Python -m unittest $m 2>&1 | Out-String)
    $r = [regex]::Match($o, "Ran (\d+) tests? in")
    if ($r.Success) { $ran += [int]$r.Groups[1].Value }
    $k = [regex]::Match($o, "skipped=(\d+)")
    if ($k.Success) { $skipped += [int]$k.Groups[1].Value }
    $v = [regex]::Match($o, "(?m)^FAILED \([^)]*\)")
    if ($v.Success) {
        $fail += ("{0} : {1}" -f $m, $v.Value)
        if ($Show) { Write-Host $o }
    } elseif ($o -match "NO TESTS RAN") {
        $none += $m
    }
}

Write-Host ("modules: {0}   tests: {1}   skipped: {2}" -f $mods.Count, $ran, $skipped)
foreach ($x in $none) { Write-Host "no tests: $x" -ForegroundColor Yellow }
foreach ($x in $fail) { Write-Host "FAILED: $x" -ForegroundColor Red }
if ($fail.Count -gt 0) { Write-Host ("modules failing: {0}" -f $fail.Count) -ForegroundColor Red; exit 1 }
Write-Host "every module passes" -ForegroundColor Green
exit 0
