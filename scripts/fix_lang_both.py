#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_lang_both.py - recover English mis-filed into translations_l10n(lang='both').

A routing bug passed 'both' as a language to translate_passages, which stored the
ENGLISH translation in translations_l10n under the bogus code 'both' and left
passages.translation empty (so the Library showed 0). This MOVES those English rows
back into passages.translation and removes the stray 'both' rows. No re-translation,
no API cost - the work is recovered in place.

SAFE: dry-run by default. Only moves a row when (a) the target passages.translation is
empty AND (b) the stored text is actually English (Latin-dominant), so a stray Hindi row
can never land in the English column. Writes via db_utils.connect (WAL + busy_timeout).
Take a fresh backup first (db_backup.py) and run with the dashboard idle.

  python scripts/fix_lang_both.py            # preview
  python scripts/fix_lang_both.py --apply     # move + clean up + rebuild FTS
"""
from __future__ import annotations
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_utils import connect as _connect
try:
    from db_utils import rebuild_fts
except Exception:
    rebuild_fts = None


def looks_english(s: str) -> bool:
    lat = dev = 0
    for ch in s or "":
        o = ord(ch)
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            lat += 1
        elif 0x0900 <= o <= 0x097F:
            dev += 1
    tot = lat + dev
    return tot > 0 and lat / tot >= 0.5


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = _connect(args.db)
    pcols = {r[1] for r in con.execute("PRAGMA table_info(passages)")}

    rows = con.execute("""SELECT d.code, COUNT(*) FROM translations_l10n x
        JOIN passages p ON p.id=x.passage_id JOIN docs d ON d.id=p.doc_id
        WHERE x.lang='both' GROUP BY d.code ORDER BY 2 DESC""").fetchall()
    total = sum(n for _, n in rows)
    print("Docs with translations_l10n lang='both' (mis-filed English):")
    for code, n in rows:
        print(f"  {code}: {n}")
    print(f"Total 'both' rows: {total}")
    if not total:
        print("Nothing to recover."); con.close(); return

    cand = con.execute("""SELECT x.passage_id, x.translation, x.engine, x.mt_prompt_version,
        x.translation_qa, x.translated_at
        FROM translations_l10n x JOIN passages p ON p.id=x.passage_id
        WHERE x.lang='both' AND TRIM(COALESCE(p.translation,''))=''""").fetchall()
    movable = [r for r in cand if looks_english(r[1])]
    not_english = len(cand) - len(movable)
    target_filled = total - len(cand)
    print(f"\nmovable (target empty + English): {len(movable)}")
    print(f"skipped (target already has English): {target_filled}")
    print(f"skipped (row is not English - left as-is): {not_english}")

    if not args.apply:
        print("\nDRY-RUN. Take a backup, then re-run with --apply.")
        con.close(); return

    moved_ids = []
    for pid, tr, eng, pv, qa, tat in movable:
        parts = ["translation=?", "translation_qa=?"]
        vals  = [tr, qa]
        if "mt_prompt_version" in pcols: parts.append("mt_prompt_version=?"); vals.append(pv or "recovered-from-both")
        if "translated_at" in pcols:     parts.append("translated_at=?");     vals.append(tat)
        if "engine" in pcols:            parts.append("engine=?");            vals.append(eng)
        vals.append(pid)
        con.execute(f"UPDATE passages SET {', '.join(parts)} WHERE id=?", vals)
        moved_ids.append(pid)
    # delete only the rows we successfully moved; leave any non-English/target-filled ones
    con.executemany("DELETE FROM translations_l10n WHERE lang='both' AND passage_id=?",
                    [(i,) for i in moved_ids])
    con.commit()
    print(f"\nMoved {len(moved_ids)} English translations into passages.translation; "
          f"deleted their stray 'both' rows.")
    remaining = con.execute("SELECT COUNT(*) FROM translations_l10n WHERE lang='both'").fetchone()[0]
    print(f"'both' rows remaining (non-English or target-filled): {remaining}")
    if rebuild_fts:
        try:
            rebuild_fts(con); con.commit(); print("Rebuilt passages_fts (moved English now searchable).")
        except Exception as e:
            print("FTS rebuild skipped:", e)
    con.close()
    print("Done. Reload the Library; run qa_scan to score the recovered rows.")


if __name__ == "__main__":
    main()
