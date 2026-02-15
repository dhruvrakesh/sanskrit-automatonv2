for %F in (inbox\*.pdf) do (
  echo === Ingesting %~nxF ===
  python scripts\ingest_pdf.py --pdf "%F" --doc "MBh-01" --resume --run-id "mbh01-%~nF"
)
