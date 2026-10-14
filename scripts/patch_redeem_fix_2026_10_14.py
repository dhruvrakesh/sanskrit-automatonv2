#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_redeem_fix_2026_10_14.py  (2026-10-14)  REDEEM_FIX_2026_10_14

A follow-up to REDEEM_2026_10_14 (released 5cf03b0). On 14 Oct, `python scripts\\redeem.py --doc Mallapurana`
printed "and $30.33 was spent on texts no longer in the database": with --doc the count holds one text, and
every other text's spend was taken for gone. Now:
  - "no longer in the database" is a text missing from the docs table (or retired), whatever is counted;
  - with --doc that corpus line is not printed (the text's own spend is, as before).
The full count is unchanged (on the backup of 14 Oct: $1.03, the same texts).

scripts/redeem.py only. Anchored, all-or-nothing, marker-idempotent; keeps line endings; compiled before it
replaces the original; backup .bak_redeemfix_<date>.
  python scripts\\patch_redeem_fix_2026_10_14.py --check
  python scripts\\patch_redeem_fix_2026_10_14.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "REDEEM_FIX_2026_10_14"
NEEDS = "REDEEM_2026_10_14"
FILE = Path("scripts/redeem.py")
E = []


def edit(n, old, new):
    E.append((n, old, new))


edit(1,
     r'''        classes = classify(con, a.only)
        spent, flash, pro = spend_by_doc(con)
    finally:
        con.close()
''',
     r'''        classes = classify(con, a.only)
        spent, flash, pro = spend_by_doc(con)
        # REDEEM_FIX_2026_10_14: "no longer in the database" is a text missing from docs, not from this count
        # (with --doc the count holds one text: every other text's spend was called gone, $30.33 on 14 Oct)
        in_db = {c for (c,) in con.execute("SELECT code FROM docs WHERE code NOT LIKE '%-RETIRED'")}
    finally:
        con.close()
''')
edit(2,
     r'''               spent_replaced=round(sum(t["spent"] for t in texts if not t["english"]), 4),
               replaced=sum(1 for t in texts if not t["english"]),
               spent_gone=round(sum(v for k, v in spent.items() if k not in classes), 4))
    by = {}
    for t in texts:
''',
     r'''               spent_replaced=round(sum(t["spent"] for t in texts if not t["english"]), 4),
               replaced=sum(1 for t in texts if not t["english"]),
               spent_gone=round(sum(v for k, v in spent.items() if k not in in_db), 4))
    by = {}
    for t in texts:
''')
edit(3,
     r'''             (", %s on English a better reading replaced (%d text(s), no English here now)" % (usd(rep), t["replaced"]))
             if t.get("replaced") else "", usd(t["redo_cost"])))
    if t.get("spent_gone"):
        print("  and %s was spent on texts no longer in the database (retired or re-segmented)" % usd(t["spent_gone"]))

''',
     r'''             (", %s on English a better reading replaced (%d text(s), no English here now)" % (usd(rep), t["replaced"]))
             if t.get("replaced") else "", usd(t["redo_cost"])))
    if t.get("spent_gone") and not one:   # REDEEM_FIX_2026_10_14: a corpus fact, not one text's
        print("  and %s was spent on texts no longer in the database (retired or re-segmented)" % usd(t["spent_gone"]))

''')


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not FILE.exists():
        print("FAIL: %s not found: run from the automaton repo root." % FILE); return 2
    src, nl = load(FILE)
    if MARK in src:
        print("Nothing to do: %s is in place." % MARK); return 0
    if NEEDS not in src:
        print("REFUSE: %s does not carry %s: apply that release first. Nothing written." % (FILE, NEEDS)); return 1
    out = src
    for n, old, new in E:
        c = out.count(old)
        if c != 1:
            print("REFUSE: %s: anchor %d found %d times (want 1): this is not the file released. Nothing written."
                  % (FILE, n, c)); return 1
        out = out.replace(old, new, 1)
    data = out.replace("\n", nl).encode("utf-8")
    fd, tmp = tempfile.mkstemp(suffix=".py"); os.close(fd)
    Path(tmp).write_bytes(data)
    try:
        py_compile.compile(tmp, doraise=True)
    except py_compile.PyCompileError as e:
        print("REFUSE: %s would not compile: %s. Nothing written." % (FILE, e)); return 1
    finally:
        os.unlink(tmp)
    if a.check:
        print("CHECK OK: 1 file to write: %s. Nothing written." % FILE); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    shutil.copy2(FILE, FILE.with_name(FILE.name + ".bak_redeemfix_" + stamp))
    t = FILE.with_name(FILE.name + ".tmp_redeemfix"); t.write_bytes(data); os.replace(t, FILE)
    print("wrote %s" % FILE)
    print("Free and read-only: python scripts\\redeem.py --doc Mallapurana   (no corpus line now)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
