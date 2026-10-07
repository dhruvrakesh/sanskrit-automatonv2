#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
story_fix.py  STORY_FIX_2026_10_07

Applies reviewed corrections to written stories (doc_stories) from a JSON file, the way the
dashboard's Edit does it: the new text is checked with stories.verify() against the same passages
the dashboard gives (window pad=2, cap=60); the check and the citations are stored; the story goes
back to 'draft' and approved_at is cleared, so an approved story has to be approved again.

The file is a list of fixes:
  {"id": 3, "doc": "markandeya_purana", "marker": "STORY_FIX_2026_10_07",
   "replace": [{"field": "story_en", "old": "...", "new": "..."}],      old must occur exactly once
   "set": {"story_en": "..."}, "md5": {"story_en": "<md5 of the current text>"},
                                     a whole field is replaced only if it is still the text reviewed
   "append_notes": "... STORY_FIX_2026_10_07 ...",                     must carry the marker
   "allow_fail": false}                        the new text must pass the check unless this is true
Fields that can change: title, title_hi, why, story_en, story_hi, quote_sa, quote_ref, notes.
('why' is the one-line summary the illustration prompt reads; the dashboard's Edit cannot change it.)

All or nothing: if any fix cannot be applied (unknown or retired story, wrong document, an anchor
that is missing or not unique, a changed text, a failing check), nothing is written. A story whose
notes already carry the fix's marker is skipped, so a second run changes nothing. The rows are
updated in one transaction, each only if updated_at is still what was read (a dashboard edit in
between makes the whole run refuse).

  python scripts\\db_backup.py data\\context.db D:\\backups\\context_pre_storyfix_<date>.db
  python scripts\\story_fix.py --file docs\\stories\\fix_markandeya_2026-10-07.json --check
  python scripts\\story_fix.py --file docs\\stories\\fix_markandeya_2026-10-07.json
  python scripts\\stories.py show --id 3      (read it, then:)  python scripts\\stories.py approve --id 3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stories as st  # noqa: E402

MARK = "STORY_FIX_2026_10_07"
FIELDS = ("title", "title_hi", "why", "story_en", "story_hi", "quote_sa", "quote_ref", "notes")
LIMITS = {"title": 300, "title_hi": 300, "why": 1000, "story_en": 6000, "story_hi": 8000, "quote_sa": 400,
          "quote_ref": 20, "notes": 4000}


def md5(s: str) -> str:
    return hashlib.md5((s or "").encode("utf-8")).hexdigest()


def _row(con, sid: int) -> dict | None:
    cols = [r[1] for r in con.execute("PRAGMA table_info(doc_stories)")]
    r = con.execute("SELECT * FROM doc_stories WHERE id=?", (sid,)).fetchone()
    return dict(zip(cols, r)) if r else None


def plan(con, fixes: list) -> tuple:
    """(changes, skipped, errors). Reads only."""
    changes, skipped, errors = [], [], []
    seen = set()
    for n, f in enumerate(fixes, 1):
        where = "fix %d (story %s)" % (n, f.get("id"))
        sid, marker = f.get("id"), f.get("marker") or ""
        if not isinstance(sid, int) or not marker:
            errors.append("%s: needs an integer id and a marker" % where); continue
        if sid in seen:
            errors.append("%s: the same story twice in one file" % where); continue
        seen.add(sid)
        s = _row(con, sid)
        if not s:
            errors.append("%s: no such story" % where); continue
        code = con.execute("SELECT code FROM docs WHERE id=?", (s["doc_id"],)).fetchone()
        code = code[0] if code else None
        if f.get("doc") and f["doc"] != code:
            errors.append("%s: belongs to %s, not %s" % (where, code, f["doc"])); continue
        if s["status"] == "retired":
            errors.append("%s: the story is retired" % where); continue
        if marker in (s.get("notes") or ""):
            skipped.append(sid); continue
        new = {k: s.get(k) or "" for k in FIELDS}
        bad, removed = False, []
        for k, h in (f.get("md5") or {}).items():
            if k not in FIELDS or md5(new[k]) != h:
                errors.append("%s: %s is not the text that was reviewed (md5 %s, expected %s)"
                              % (where, k, md5(new.get(k, "")), h)); bad = True
        for k, v in (f.get("set") or {}).items():
            if k not in FIELDS:
                errors.append("%s: %s cannot be changed" % (where, k)); bad = True; continue
            if k in ("story_en", "story_hi") and k not in (f.get("md5") or {}):
                errors.append("%s: replacing %s whole needs its md5" % (where, k)); bad = True; continue
            new[k] = v
        for r in f.get("replace") or []:
            k = r.get("field")
            if "from" in r:   # a span: from the unique text "from" through the first "to" after it
                a_, b_ = r.get("from") or "", r.get("to") or ""
                c = new.get(k, "").count(a_) if a_ else 0
                i = new[k].find(a_) if c == 1 else -1
                j = new[k].find(b_, i) if i >= 0 and b_ else -1
                if k not in FIELDS or c != 1 or j < 0:
                    errors.append("%s: in %s the span %r ... %r is not found once (start occurs %d times)"
                                  % (where, k, a_[:40], b_[-30:], c)); bad = True; continue
                old = new[k][i:j + len(b_)]
            else:
                old = r.get("old") or ""
                if k not in FIELDS or not old:
                    errors.append("%s: bad replace entry" % where); bad = True; continue
                c = new[k].count(old)
                if c != 1:
                    errors.append("%s: in %s the text to replace occurs %d times (want 1): %r"
                                  % (where, k, c, old[:60])); bad = True; continue
            removed.append((k, old))
            new[k] = new[k].replace(old, r.get("new") or "", 1)
        add = f.get("append_notes") or ""
        if marker not in add:
            errors.append("%s: append_notes must carry the marker %s" % (where, marker)); bad = True
        new["notes"] = ((new["notes"].rstrip() + "\n") if new["notes"].strip() else "") + add
        for k, v in new.items():
            if len(v) > LIMITS[k]:
                errors.append("%s: %s is %d characters (limit %d)" % (where, k, len(v), LIMITS[k])); bad = True
        if bad:
            continue
        rows = st.window(st.passages(con, code), (s["from_page"], s["from_idx"]), (s["to_page"], s["to_idx"]),
                         pad=2, cap=60)
        v = st.verify(dict(s, **new), rows)
        if not v["ok"] and not f.get("allow_fail"):
            errors.append("%s: the corrected story fails the check: %s" % (where, "; ".join(v["problems"])))
            continue
        changed = [k for k in FIELDS if (s.get(k) or "") != new[k]]
        changes.append({"id": sid, "doc": code, "was": s["status"], "updated_at": s["updated_at"],
                        "fields": {k: new[k] for k in changed}, "removed": removed, "verify": v})
    return changes, skipped, errors


def apply(con, changes: list) -> None:
    con.execute("BEGIN IMMEDIATE")
    try:
        for c in changes:
            sets = ", ".join("%s=?" % k for k in c["fields"])
            cur = con.execute(
                "UPDATE doc_stories SET %s, verify=?, cites=?, status=CASE WHEN status='candidate' THEN "
                "'candidate' ELSE 'draft' END, approved_at=NULL, updated_at=? WHERE id=? AND "
                "COALESCE(updated_at,'')=COALESCE(?,'')" % sets,
                list(c["fields"].values()) + [json.dumps(c["verify"]), json.dumps(c["verify"]["cited"]), st.now(),
                                              c["id"], c["updated_at"]])
            if cur.rowcount != 1:
                raise RuntimeError("story %d changed while this ran; nothing written" % c["id"])
        con.commit()
    except Exception:
        con.rollback()
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply reviewed story corrections (%s)." % MARK)
    ap.add_argument("--db", default="data/context.db")
    ap.add_argument("--file", required=True)
    ap.add_argument("--check", action="store_true", help="show what would change; write nothing")
    a = ap.parse_args()
    try:   # a console that cannot show Devanagari prints \\u escapes instead of failing
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    if not Path(a.db).is_file():
        print("FAIL: %s not found. Run from the repo root." % a.db); return 2
    try:
        fixes = json.loads(Path(a.file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("FAIL: cannot read %s: %s" % (a.file, e)); return 2
    if not isinstance(fixes, list):
        print("FAIL: %s must hold a list of fixes" % a.file); return 2
    con = st.im._connect(a.db)
    try:
        changes, skipped, errors = plan(con, fixes)
        for sid in skipped:
            print("skip #%d (already carries its marker)" % sid)
        for c in changes:
            v = c["verify"]
            print("#%d %s (%s -> draft): %s; check %s, %d words, %d citations%s"
                  % (c["id"], c["doc"], c["was"], ", ".join(c["fields"]), "PASS" if v["ok"] else "FAIL",
                     v["words"], len(v["cited"]), "" if v["ok"] else " - " + "; ".join(v["problems"])))
            for k, old in c["removed"]:
                print("    %s: replaces %d characters: %s" % (k, len(old), old if len(old) <= 160 else
                                                             old[:100] + " ... " + old[-50:]))
        if errors:
            for e in errors:
                print("REFUSE: " + e)
            print("Nothing written."); return 1
        if a.check:
            print("CHECK OK: %d stor%s to change, %d skipped. Nothing written."
                  % (len(changes), "y" if len(changes) == 1 else "ies", len(skipped)))
            return 0
        if not changes:
            print("Nothing to change."); return 0
        apply(con, changes)
        print("written: %s. Each is a draft again: read it (stories.py show --id N), then approve it."
              % ", ".join("#%d" % c["id"] for c in changes))
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
