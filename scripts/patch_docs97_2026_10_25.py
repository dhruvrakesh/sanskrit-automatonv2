#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_docs97_2026_10_25.py  (2026-10-25)  DOCS97_2026_10_25

The genealogies of the indexes on the site, recorded: docs\\STATE_2026-10-18.md gains section 32 (25 Oct, night),
RUNBOOK.md the steps in order, README.md the site's page beside /vamsa; the full account is
docs\\INDEX_SITE_2026-10-25.md (a new file, beside them).

Needs DOCS96_2026_10_25 in STATE, DOCS95_2026_10_25 in RUNBOOK.md and README.md, and docs\\INDEX_SITE_2026-10-25.md.
Anchored, all-or-nothing, marker-idempotent; line endings kept; .bak_docs97_<date> copies.

  python scripts\\patch_docs97_2026_10_25.py --check
  python scripts\\patch_docs97_2026_10_25.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'DOCS97_2026_10_25'
TAG = 'docs97'
FILES = ['docs/STATE_2026-10-18.md', 'RUNBOOK.md', 'README.md']
NEEDS = {'docs/STATE_2026-10-18.md': 'DOCS96_2026_10_25', 'RUNBOOK.md': 'DOCS95_2026_10_25', 'README.md': 'DOCS95_2026_10_25'}
REQUIRES = {'docs/INDEX_SITE_2026-10-25.md': 'INDEX_SITE_2026_10_25', 'scripts/index_sync.py': 'INDEX_SITE_2026_10_25'}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/STATE_2026-10-18.md', 1, "| The cap | $111.28 spent of $125.00 at 15:01 IST (the rounds keep $1.00) |\n| Next | G3: the indexes' relations and lines of descent on the site (C21) |\n",
     '| The cap | $111.28 spent of $125.00 at 15:01 IST (the rounds keep $1.00) |\n| Next | G3: the indexes\' relations and lines of descent on the site (C21) |\n## 32. 25 Oct, night: the genealogies of the indexes on the site (DOCS97_2026_10_25)\n\n| What | State |\n|---|---|\n| Release | `a551ac97` pushed; Srangam `9cef3f6` pushed; C22 pasted and checked (1,671 scholarly rows) |\n| Built | INDEX_SITE (index_sync.py, the Srangam kit, the mirror task\'s step), C21 (seven tables, five readers behind the gate, checks), the edge function corpus-index; docs\\INDEX_SITE_2026-10-25.md |\n| The rows | 53,628: persons 14,979, steps 10,861, relations 22,021, GRETIL verses 5,702, lines 53, texts 11; built in 6 s, read-only, no model |\n| The rights | the indexes\' relations with their words (Cologne, CC BY-NC-SA 3.0, credited); GRETIL\'s verses (CC BY-NC-SA 4.0); the Mahabharata e-text counted, never quoted; our passages only where the site has the text |\n| To do | paste C21; Srangam\'s patcher, push; deploy corpus-index; python scripts\\index_sync.py --apply; then /corpus/genealogies |\n| Next | B2 (Raychaudhuri\'s claims, the "R" of a step); X1c (search over the scholarly English) |\n')

edit('RUNBOOK.md', 1, '   (what the next round would run); the allowance: `python scripts\\repair_auto.py --allow 0.25` (0 stops the paid\n   steps). The maintenance task runs a round at each tick; `python scripts\\repair_auto.py --log` shows them.\n',
     '   (what the next round would run); the allowance: `python scripts\\repair_auto.py --allow 0.25` (0 stops the paid\n   steps). The maintenance task runs a round at each tick; `python scripts\\repair_auto.py --log` shows them.\n## 25 Oct, night: the genealogies on the site (DOCS97_2026_10_25)\n\ndocs\\INDEX_SITE_2026-10-25.md. From the repository root:\n\n1. `python scripts\\patch_index_task_2026_10_25.py --check`, then without --check; the same for\n   `patch_docs97_2026_10_25.py`. Then `powershell -ExecutionPolicy Bypass -File scripts\\run_tests.ps1`.\n2. In the Lovable Cloud SQL editor: P1 of docs\\cloud\\C21_checks_2026-10-25.sql; the whole of\n   docs\\cloud\\C21_index_site_2026-10-25.sql in one paste; V1 and V2.\n3. In D:\\srangam-42267: `python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_index_site_2026_10_25.py"`\n   (--check first), the typecheck, the tests and the build, commit and push; ask Lovable to deploy\n   supabase/functions/corpus-index as it is.\n4. `python scripts\\index_sync.py` (the plan), then `python scripts\\index_sync.py --apply` (about 25 MB of JSON, gzip;\n   what differs only, so a second run sends nothing); `--status` shows the counts here and there. E1 to E3 of the\n   checks; open /corpus/genealogies signed in.\n5. The mirror task sends what changes after that, last in each tick; it is quiet until steps 2 and 3 are done.\n')

edit('README.md', 1, "  names stand (GRETIL's editions, read by scripts/vamsa_check.py), the epics' verses that name both, our\n  passages and Raychaudhuri's view. Read-only; no model is called.\n- **\U0001f4be Database** \u2014 snapshots the DB and opens it in **Datasette** for read-only SQL.\n",
     '  names stand (GRETIL\'s editions, read by scripts/vamsa_check.py), the epics\' verses that name both, our\n  passages and Raychaudhuri\'s view. Read-only; no model is called.\n  On the site (INDEX_SITE_2026_10_25, DOCS97_2026_10_25): **/corpus/genealogies**, the same lines for signed-in\n  readers, from the mirror (scripts/index_sync.py, docs/cloud/C21), with "In the indexes" on a name\'s page; the\n  Mahabharata e-text counted, never quoted; Raychaudhuri\'s view not yet (B2).\n- **\U0001f4be Database** \u2014 snapshots the DB and opens it in **Datasette** for read-only SQL.\n')


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
            print("FAIL: %s not found. Run from the repo root." % f); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS.get(f) and NEEDS[f] not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (f, NEEDS[f])); return 1
        for ff, n, old, new in E:
            if ff != f:
                continue
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (f, MARK)); return 2
        plan[f] = src.replace("\n", nl).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        for f, data in plan.items():
            if f.endswith(".py"):
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), doraise=True)
                except py_compile.PyCompileError as ex:
                    print("FAIL: %s would not compile: %s. Nothing written." % (f, str(ex)[:300])); return 2
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        p = Path(f)
        shutil.copy2(p, p.with_name(p.name + ".bak_" + TAG + "_" + stamp))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
