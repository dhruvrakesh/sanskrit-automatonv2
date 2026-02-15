param([string]$pdf, [string]$doc, [string]$db, [switch]$no_backup)
$base = "G:\My Drive\DALLE\sanskrit-automatonv2\ingest_pdf.py"
$cmd = @("python", $base, "--pdf", $pdf, "--doc", $doc)
if ($db) { $cmd += @("--db", $db) }
if ($no_backup) { $cmd += "--no-backup" }
& $cmd
