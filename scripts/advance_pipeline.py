#!/usr/bin/env python3
"""
advance_pipeline.py — Move all already-OCR'd docs through Ingest → Translate → Export
in the user-confirmed priority order.

Priority (confirmed):
  nirukta → shiksha_* → markandeya_purana → upapurana_* → yajur_veda_* → bodhyana
  → Bodhicaryavatara → LalitaVistara (last — largest, lowest quality OCR)

Run from project root:
  python scripts/advance_pipeline.py

This script:
  1. Re-ingests each doc with the new segmenter (safe — never overwrites translations)
  2. Runs translate_passages.py for untranslated passages (new context-window engine)
  3. Exports HTML for translated docs

Each stage is logged. Ctrl+C cancels gracefully.
"""
import sys, subprocess, pathlib, time

ROOT = pathlib.Path('.')
DB   = str(ROOT / 'data' / 'context.db')
PY   = sys.executable

# Priority order — confirmed by user
PRIORITY = [
    # (doc_code,                               category,        pages_ocrd)
    ("nirukta",                               "vedanga",        17),
    ("shiksha_atreya_shiksha",                "vedanga",        1),
    ("shiksha_avasananirnaya_shiksha",        "vedanga",        4),
    ("shiksha_bharadvaja_shiksha",            "vedanga",        3),
    ("shiksha_lomashi_shiksha",               "vedanga",        8),
    ("shiksha_aranya_shiksha",                "vedanga",        12),
    ("shiksha_apishali_shiksha",              "vedanga",        9),
    ("shiksha_amoghanandini_shiksha",         "vedanga",        13),
    ("markandeya_purana",                     "purana",         23),
    ("upapurana_kapila_purana",               "purana",         12),
    ("upapurana_nilamata_purana",             "purana",         11),
    ("upapurana_parashara_purana",            "purana",         10),
    ("upapurana_samba_purana",                "purana",         11),
    ("upapurana_saura_purana",                "purana",         11),
    ("upapurana_narasimha_purana",            "purana",         12),
    ("yajur_veda_shukla_yajur_veda",          "veda",           10),
    ("yajur_veda_taittiriya_krishna_yajur_veda","veda",         12),
    ("vasishtha_dhanur_veda",                 "dhanur_veda",    32),
    ("shiva_dhanur_veda",                     "dhanur_veda",    19),
    ("bodhyana",                              "dharmasutra",    48),
    # Largest — last
    ("Bodhicaryavatara",                      "bauddha",        259),
    ("LalitaVistara",                         "bauddha",        644),
]


def run(cmd, label):
    print(f"\n  [{label}] Running: {' '.join(str(c) for c in cmd)}")
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=False, text=True)
    elapsed = round(time.time() - t0, 1)
    status = "OK" if result.returncode == 0 else "FAILED"
    print(f"  [{label}] {status} in {elapsed}s")
    return result.returncode == 0


def main():
    print("=" * 70)
    print("SANSKRIT AUTOMATON — ADVANCE PIPELINE")
    print("Priority: nirukta -> shiksha_* -> puranas -> vedas -> bauddha")
    print("=" * 70)

    for doc, category, pages in PRIORITY:
        glob_pat = str(ROOT / "data" / "raw" / f"{doc}_*.jsonl")

        print(f"\n{'='*70}")
        print(f"DOC: {doc}  ({pages} pages OCRd, category={category})")
        print(f"{'='*70}")

        # ── STEP 1: Ingest / Re-ingest with verse segmenter ──────────────────
        # Safe: never overwrites existing translations
        ingest_cmd = [
            PY, "scripts/ingest_jsonl_fast.py",
            "--doc", doc,
            "--glob", glob_pat,
            "--db", DB,
            "--category", category,
        ]
        ok = run(ingest_cmd, "INGEST")
        if not ok:
            print(f"  SKIP {doc} — ingest failed")
            continue

        # ── STEP 2: Translate untranslated passages ───────────────────────────
        translate_cmd = [
            PY, "scripts/translate_passages.py",
            "--doc", doc,
            "--db", DB,
            "--engine", "gemini:gemini-2.5-flash",
            "--context", "5",        # 5-verse context window
            "--sleep", "0.8",        # 0.8s between API calls
            "--min-quality", "0.25", # skip passages with bad OCR quality
        ]
        ok = run(translate_cmd, "TRANSLATE")
        if not ok:
            print(f"  WARNING: translation had errors for {doc}")

        # ── STEP 3: Export HTML ───────────────────────────────────────────────
        export_cmd = [
            PY, "scripts/export_html.py",
            "--doc", doc,
            "--db", DB,
        ]
        # Only export if export_html.py exists
        if pathlib.Path("scripts/export_html.py").exists():
            run(export_cmd, "EXPORT")

        print(f"\n  DONE: {doc}")
        # Brief pause between docs
        time.sleep(2)

    print("\n" + "=" * 70)
    print("ALL DOCS PROCESSED")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user — pipeline paused safely.")
        sys.exit(0)
