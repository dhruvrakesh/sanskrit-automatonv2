#!/usr/bin/env python3
import argparse, re, sqlite3, csv, sys, os
from pathlib import Path

DB_DEFAULT = "data/context.db"

ZERO_WIDTH = r"[\u200B\u200C\u200D\u200E\u200F\u202A-\u202E\u2060]"

# case-preserving replace
def _casey(sub: str, repl: str, s: str):
    def f(m):
        g = m.group(0)
        if g.isupper(): return repl.upper()
        if g[0].isupper(): return repl.capitalize()
        return repl
    return re.sub(sub, f, s, flags=re.IGNORECASE)

def debroy_style(en: str, mode: str = "common"):
    if not en: return en, []

    rules = []
    s = en

    # 0) clean invisibles & wrap
    s2 = re.sub(ZERO_WIDTH, "", s)
    s2 = re.sub(r"\s*\n+\s*", " ", s2)
    s2 = re.sub(r"\s{2,}", " ", s2).strip()
    if s2 != s: rules.append("whitespace/zw"); s = s2

    # 1) strip anthology-style labels at start
    s2 = re.sub(r"^\s*Stories from Panchatantra\s*[:\-–—]?\s*", "", s, flags=re.IGNORECASE)
    if s2 != s: rules.append("strip:SfP"); s = s2
    s2 = re.sub(r"^\s*Tale of the\s+", "", s, flags=re.IGNORECASE)
    if s2 != s: rules.append("strip:TaleOf"); s = s2

    # 2) diction softeners
    s2 = re.sub(r"\bThere\s+used\s+to\s+be\b", "There was", s, flags=re.IGNORECASE)
    if s2 != s: rules.append("diction:used_to_be"); s = s2
    s2 = re.sub(r"\bThere\s+once\s+was\b", "There was", s, flags=re.IGNORECASE)
    if s2 != s: rules.append("diction:once_was"); s = s2

    # 3) terminology
    if mode == "common":
        before = s
        s = _casey(r"\bbargad\b", "banyan", s)
        s = _casey(r"\bnyagrodha\b", "banyan", s)
        s = _casey(r"\bśṛgāla\b", "jackal", s)
        s = _casey(r"\bshrigala\b", "jackal", s)
        if s != before: rules.append("terms:common")
    elif mode == "iast":
        before = s
        s = _casey(r"\bbanyan\b", "nyagrodha", s)
        s = _casey(r"\bbargad\b", "nyagrodha", s)
        s = _casey(r"\bjackal\b", "śṛgāla", s)
        if s != before: rules.append("terms:iast")

    return s, rules

def main():
    ap = argparse.ArgumentParser(description="Post-style fix (Debroy-ish) for English translations")
    ap.add_argument("--db", default=DB_DEFAULT, help="SQLite path (default data/context.db)")
    ap.add_argument("--doc", required=True, help="Document code, e.g., panchatantra")
    ap.add_argument("--mode", choices=["common","iast"], default="common", help="Terminology style")
    ap.add_argument("--apply", action="store_true", help="Apply updates to DB (otherwise dry-run)")
    ap.add_argument("--limit", type=int, default=0, help="Limit rows to process (debug)")
    ap.add_argument("--out", default="debroy_style_diff.csv", help="Diff CSV when dry-run")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()

    q = "SELECT id, page, en FROM passages WHERE doc=? AND en IS NOT NULL AND TRIM(en)<>''"
    if args.limit: q += " LIMIT ?"
    rows = cur.execute(q, (args.doc,) if not args.limit else (args.doc, args.limit)).fetchall()

    changed = []
    for _id, page, en in rows:
        new, marks = debroy_style(en, mode=args.mode)
        if new != en and marks:
            changed.append((_id, page, en, new, ";".join(marks)))

    if not args.apply:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id","page","rule_hits","old_en","new_en"])
            for _id, page, en, new, marks in changed:
                w.writerow([_id, page, marks, en, new])
        print(f"[dry-run] changed={len(changed)}  wrote={args.out}")
        return

    # apply
    for _id, page, en, new, marks in changed:
        cur.execute("UPDATE passages SET en=? WHERE id=?", (new, _id))
    con.commit()
    print(f"[applied] updated rows={len(changed)}")

if __name__ == "__main__":
    main()
