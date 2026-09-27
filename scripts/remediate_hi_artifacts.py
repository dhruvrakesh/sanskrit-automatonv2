#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""remediate_hi_artifacts.py - two measured Hindi defects, superseded not destroyed.
(TRANSLATION_FILTERS_2026_09_27)

  A  bare token   a translations_l10n 'hi' row that is NOTHING BUT the
                  hard-fail token [asphuta] (and punctuation). It is a
                  non-translation that the Library and both editions print as
                  Hindi. Its English twin, [ILLEGIBLE], was always stored empty.
                  -> archived to translation_history, then the row is removed,
                     so the passage is honestly untranslated and the next
                     translate_hi run tries it again (hi-v2 prompt, cache miss).
  B  invented     a Hindi row that opens "Vaisampayana said -" when the
     speaker      Sanskrit names no Vaisampayana: the Hindi prompt's rule 7
                  used him as its example (fixed in hi-v2-2026-09-27).
                  -> archived to translation_history, then ONLY that opening
                     phrase is removed; the rest of the translation is kept
                     byte for byte. If nothing would be left, it is treated
                     as A.

Nothing else is touched: no English, no mt_cache (the hi-v2 prompt version
already changes every Hindi cache key), no passages row.

  python scripts/remediate_hi_artifacts.py --db data/context.db              # report
  python scripts/remediate_hi_artifacts.py --db data/context.db --apply --backup D:\\backups\\x.db

--apply needs --backup naming a file that exists (take it first), refuses
while a Hindi translate job on an affected doc is live in
data/translation_progress.json (pass --force only if it is not), runs in ONE
transaction, checks every count, and prints the SQL that reverses it.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TOKEN = "[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]"
VAIS = "\u0935\u0948\u0936\u092e\u094d\u092a\u093e\u092f\u0928"
SPEAKER = re.compile(r"^\s*" + VAIS + r"\s+\u0928\u0947\s+\u0915\u0939\u093e\s*[\u2014\u2013\-:,]*\s*")
PUNCT = re.compile(r"^[\W_\u0964\u0965]+$")
R_TOKEN = "bare-illegible-token-2026-09-27"
R_SPKR = "invented-speaker-strip-2026-09-27"


def bare_token(t):
    rest = (t or "").replace(TOKEN, " ").strip()
    return rest != (t or "").strip() and (not rest or bool(PUNCT.match(rest)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backup", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--show", type=int, default=6)
    a = ap.parse_args()

    con = sqlite3.connect(a.db, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    if not a.apply:
        con.execute("PRAGMA query_only=ON")
    cols = {r[1] for r in con.execute("PRAGMA table_info(translation_history)")}
    if "lang" not in cols:
        print("translation_history has no lang column - run the app once (migrate_schema) first.")
        return 2

    sql = ("SELECT l.id, l.passage_id, d.code, p.page_no, p.idx, p.text, l.translation, "
           "l.engine, l.mt_prompt_version, l.translation_score, l.translation_qa, "
           "l.translated_at, COALESCE(p.text_type,'mula') "
           "FROM translations_l10n l JOIN passages p ON p.id=l.passage_id "
           "JOIN docs d ON d.id=p.doc_id WHERE l.lang='hi' "
           "AND TRIM(COALESCE(l.translation,''))<>''")
    params = []
    if a.doc:
        sql += " AND d.code=?"; params.append(a.doc)
    A, B = [], []
    for row in con.execute(sql, params):
        lid, pid, code, page, idx, src, hi = row[:7]
        if bare_token(hi):
            A.append(row)
        elif SPEAKER.search(hi) and VAIS not in (src or ""):
            rest = SPEAKER.sub("", hi, count=1).strip()
            (B if rest and not bare_token(rest) else A).append(row)

    def per_doc(rows):
        c = {}
        for r in rows:
            c[r[2]] = c.get(r[2], 0) + 1
        return c

    print("remediate_hi_artifacts  db=%s  mode=%s" % (a.db, "APPLY" if a.apply else "report"))
    for label, rows in (("A  bare [asphuta] token rows", A), ("B  invented-speaker rows", B)):
        print("\n%s: %d" % (label, len(rows)))
        for code, n in sorted(per_doc(rows).items(), key=lambda kv: -kv[1]):
            print("   %-50s %5d" % (code[:50], n))
        for r in rows[:a.show]:
            print("   e.g. %s p%s.%s [%s]  hi=%r" % (r[2], r[3], r[4], r[12], r[6][:70]))
    if not a.apply:
        print("\nreport only - nothing written. --apply --backup <file> to supersede them.")
        return 0

    if not a.backup or not Path(a.backup).exists():
        print("REFUSED: --backup must name a backup file that exists. Take one first.")
        return 3
    prog = Path(a.db).resolve().parent / "translation_progress.json"
    affected = set(per_doc(A)) | set(per_doc(B))
    try:
        pj = json.loads(prog.read_text(encoding="utf-8"))
        upd = datetime.fromisoformat(pj.get("updated_at"))
        fresh = (datetime.now(timezone.utc) - upd).total_seconds() < 600
        if pj.get("status") == "running" and fresh and pj.get("doc") in affected and not a.force:
            print("REFUSED: a translate job on %s is live (progress updated %ds ago). "
                  "Wait, or --force if it is an English job." % (
                      pj.get("doc"), (datetime.now(timezone.utc) - upd).total_seconds()))
            return 4
    except Exception:
        pass
    if not (A or B):
        print("nothing to do.")
        return 0

    con.execute("BEGIN IMMEDIATE")
    try:
        ins = ("INSERT INTO translation_history(passage_id, translation, engine, "
               "mt_prompt_version, translation_score, translation_qa, translated_at, "
               "reason, lang) VALUES(?,?,?,?,?,?,?,?, 'hi')")
        na = nb = 0
        for r in A:
            con.execute(ins, (r[1], r[6], r[7], r[8], r[9], r[10], r[11], R_TOKEN))
            na += con.execute("DELETE FROM translations_l10n WHERE id=? AND translation=?",
                              (r[0], r[6])).rowcount
        for r in B:
            con.execute(ins, (r[1], r[6], r[7], r[8], r[9], r[10], r[11], R_SPKR))
            nb += con.execute("UPDATE translations_l10n SET translation=? WHERE id=? AND translation=?",
                              (SPEAKER.sub("", r[6], count=1).strip(), r[0], r[6])).rowcount
        if na != len(A) or nb != len(B):
            raise RuntimeError("changed A=%d/%d B=%d/%d - a row moved underneath" % (na, len(A), nb, len(B)))
        con.commit()
    except Exception as e:
        con.rollback()
        print("ROLLED BACK: %s" % e)
        return 5
    print("\nAPPLIED in one transaction: A removed %d (archived), B stripped %d (archived)." % (na, nb))
    print("backup taken before: %s" % a.backup)
    print("\nTO REVERSE (sqlite3 against context.db):")
    print("  INSERT INTO translations_l10n(passage_id, lang, translation, engine, mt_prompt_version,")
    print("         translation_score, translation_qa, translated_at)")
    print("  SELECT passage_id, 'hi', translation, engine, mt_prompt_version, translation_score,")
    print("         translation_qa, translated_at FROM translation_history")
    print("   WHERE reason='%s' AND lang='hi'" % R_TOKEN)
    print("  ON CONFLICT(passage_id, lang) DO UPDATE SET translation=excluded.translation;")
    print("  UPDATE translations_l10n SET translation=(SELECT h.translation FROM translation_history h")
    print("         WHERE h.passage_id=translations_l10n.passage_id AND h.lang='hi'")
    print("           AND h.reason='%s' ORDER BY h.id DESC LIMIT 1)" % R_SPKR)
    print("   WHERE lang='hi' AND passage_id IN (SELECT passage_id FROM translation_history")
    print("         WHERE reason='%s');" % R_SPKR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
