#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_docs98_2026_10_28.py  (2026-10-28)  DOCS98_2026_10_28

B2 and X1c recorded: docs\\STATE_2026-10-18.md gains section 33 (28 Oct), RUNBOOK.md the steps in order, README.md the
site's genealogies with the historian's view and the scholarly search; the full account is
docs\\B2_AND_X1C_2026-10-28.md (a new file, beside them), the map of all the documentation docs\\DOCS_MAP.md (made by
scripts\\docs_map.py --write).

Needs DOCS97_2026_10_25 in all three, and docs\\B2_AND_X1C_2026-10-28.md, scripts\\docs_map.py and the B2 index_sync.py.
Anchored, all-or-nothing, marker-idempotent; line endings kept; .bak_docs98_<date> copies.

  python scripts\\patch_docs98_2026_10_28.py --check
  python scripts\\patch_docs98_2026_10_28.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS98_2026_10_28'
TAG = 'docs98'
FILES = ['docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'README.md']
NEEDS = {'docs/STATE_2026-10-18.md': 'DOCS97_2026_10_25', 'RUNBOOK.md': 'DOCS97_2026_10_25', 'README.md': 'DOCS97_2026_10_25'}
REQUIRES = {'docs/B2_AND_X1C_2026-10-28.md': 'DOCS98_2026_10_28', 'scripts/docs_map.py': 'DOCS98_2026_10_28', 'scripts/index_sync.py': 'B2_SITE_2026_10_28'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/STATE_2026-10-18.md', 1, '| To do | paste C21; Srangam\'s patcher, push; deploy corpus-index; python scripts\\index_sync.py --apply; then /corpus/genealogies |\n| Next | B2 (Raychaudhuri\'s claims, the "R" of a step); X1c (search over the scholarly English) |\n',
     '| To do | paste C21; Srangam\'s patcher, push; deploy corpus-index; python scripts\\index_sync.py --apply; then /corpus/genealogies |\n| Next | B2 (Raychaudhuri\'s claims, the "R" of a step); X1c (search over the scholarly English) |\n## 33. 28 Oct: the historian\'s view and the scholarly search on the site; two mends (DOCS98_2026_10_28)\n\n| What | State |\n|---|---|\n| Release | `8cbf904f` pushed (INDEX_SITE); Srangam `fdd80b5` pushed; C21 pasted, corpus-index deployed, 53,628 rows sent and verified (the mirror\'s log) |\n| Found | each tick of the mirror sent 80 to 150 persons again (vamsa_view chose between two tied parents by a set\'s order); test_edition_refs failed on the PC (its replay compared with a later export_html.py) |\n| Built | HEAL (both mended); B2: index_sync.py scheme i2, C23, corpus-index i2, the Srangam kit (the historian\'s chip and words, a strip over the line, "In our corpus", "What the historians say"); X1c: C24 and the search on /corpus and /corpus/scholarly; docs_map.py and docs\\DOCS_MAP.md; docs\\B2_AND_X1C_2026-10-28.md |\n| On real data | 1,904 claims of 2,010 (exact 1,675, close 229); 253 statements with a view (agrees 184, differs 68, reversed 1); 62 steps (agrees 51, differs 11); two hash seeds give 0 different rows |\n| Verified | a copy of this repository with the patches: 213 modules, 1,603 tests, none failed; PostgreSQL 16: C23 and C24 twice, 16 + 6 + 24 tests; Deno 8 + 7; Srangam: tsc clean, Vitest 49 files (415 passed, 2 skipped), vite build |\n| To do | the three patchers, docs_map.py --write, run_tests; C23 and C24 with their checks; Srangam\'s patcher, push; deploy corpus-index again, Publish; index_sync.py --apply |\n| Decisions | the Hayasirsa: its English and Hindi translated first (about $16) or released now; the Karanagama stays withdrawn |\n| Next | G3c (a graph of a line), one person across the three indexes; G2 and G4 priced first; E2 |\n')

edit('RUNBOOK.md', 1, '   checks; open /corpus/genealogies signed in.\n5. The mirror task sends what changes after that, last in each tick; it is quiet until steps 2 and 3 are done.\n',
     '   checks; open /corpus/genealogies signed in.\n5. The mirror task sends what changes after that, last in each tick; it is quiet until steps 2 and 3 are done.\n## 28 Oct: the historian\'s view and the scholarly search on the site (DOCS98_2026_10_28)\n\ndocs\\B2_AND_X1C_2026-10-28.md. From the repository root:\n\n1. `python scripts\\patch_heal_2026_10_28.py --check`, then without --check; the same for\n   `patch_b2_site_2026_10_28.py` and `patch_docs98_2026_10_28.py`. Then `python scripts\\docs_map.py --write` and\n   `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`.\n2. In the Lovable Cloud SQL editor: P1 of docs\\cloud\\C23_checks_2026-10-28.sql; the whole of\n   docs\\cloud\\C23_index_claims_2026-10-28.sql in one paste; the whole of docs\\cloud\\C24_scholar_search_2026-10-28.sql\n   in one paste; V1, V2, V3 and S1. Never paste C21 again after C23 (it would take the claims out of the readers).\n3. In D:\\srangam-42267: `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_b2_site_2026_10_28.py"`\n   (--check first), the typecheck, the tests and the build, commit and push; ask Lovable to deploy\n   supabase/functions/corpus-index as it is, then Publish.\n4. `python scripts\\index_sync.py` (the plan: the claims, the work, the statements and steps that now carry a verdict,\n   and once the persons whose tie HEAL settles), then `python scripts\\index_sync.py --apply`; E1 to E3 of the checks.\n   Signed in: /corpus/genealogies (the historians\' view), a line (its strip, its chips, "In our corpus"), a name\'s page\n   ("What the historians say"), /corpus/scholarly (its search).\n5. Until C23 is pasted and corpus-index deployed again, the mirror task\'s tick sends everything but the claims and\n   says that they wait.\n')

edit('README.md', 1, '  On the site (INDEX_SITE_2026_10_25, DOCS97_2026_10_25): **/corpus/genealogies**, the same lines for signed-in\n  readers, from the mirror (scripts/index_sync.py, docs/cloud/C21), with "In the indexes" on a name\'s page; the\n  Mahabharata e-text counted, never quoted; Raychaudhuri\'s view not yet (B2).\n- **\U0001f4be Database** \u2014 snapshots the DB and opens it in **Datasette** for read-only SQL.\n',
     '  On the site (INDEX_SITE_2026_10_25, DOCS97_2026_10_25): **/corpus/genealogies**, the same lines for signed-in\n  readers, from the mirror (scripts/index_sync.py, docs/cloud/C21), with "In the indexes" on a name\'s page; the\n  Mahabharata e-text counted, never quoted. Raychaudhuri\'s view beside each step and on a name\'s page (B2,\n  docs/cloud/C23), and a search over the scholarly English (X1c, C24): DOCS98_2026_10_28.\n- **\U0001f4be Database** \u2014 snapshots the DB and opens it in **Datasette** for read-only SQL.\n')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

