#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_maintenance_2026_10_04.py  (2026-10-04)  MAINT_2026_10_04

Three small repairs found in the 2026-10-04 run. All-or-nothing across the three
files, marker-idempotent, backups, atomic replace, py_compile before writing.

1. tests/test_translation_filters2.py  (the one failure in the 117-test suite)
   test_versions_and_rules asserted PROMPT_VERSIONS['hi'] == 'hi-v3-2026-09-27'.
   Since HI_PROMPT_FILE_2026_10_03 the Hindi prompt comes from
   prompts/hi-production.txt when that file exists, so the assertion fails on
   every machine that has activated a reviewed prompt - which is the intended
   production state. Now: the BUILT-IN prompt is checked in a child process with
   the file switched off (SA_HI_PROMPT_FILE -> a path that does not exist), and
   file mode must carry a content version 'hi-file-<10 hex>'.

2. scripts/images.py  approve <ids...>
   `approve 3 4 5 6 10` approved #3 and then STOPPED at #4 ("already approved"),
   leaving #6 and #10 as drafts. Now an already-approved image is skipped with a
   note, anything else that cannot be approved is reported, and the loop goes
   on. Exit code 1 only if something other than "already approved" was skipped.

3. scripts/resegment_doc.py  (data-loss guard)
   It writes one file per SOURCE PAGE but appended one (file, records) entry per
   source PASSAGE. When a page holds several passages - any source ingested with
   segmentation - the page file was opened 'w' once per passage and only the
   page's LAST passage survived. Consecutive entries for the same file are now
   merged. Single-passage pages (the page-blob case it was written for) produce
   byte-identical output.

  python scripts/patch_maintenance_2026_10_04.py --check
  python scripts/patch_maintenance_2026_10_04.py
Test: python -m unittest tests.test_maintenance_2026_10_04 tests.test_translation_filters2 -v
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys
from pathlib import Path

MARK = "MAINT_2026_10_04"

T_OLD = r'''        self.assertEqual(infer_mt.PROMPT_VERSIONS["hi"], "hi-v3-2026-09-27")
        self.assertIn("ONLY when no part of the text can be read", infer_mt._SYSTEM_PROMPT_BASE)
        self.assertIn("\u0906\u0902\u0936\u093f\u0915 \u0915\u094d\u0937\u0924\u093f", infer_mt._SYSTEM_PROMPT_HI)
        self.assertNotIn("\u0935\u0948\u0936\u092e\u094d\u092a\u093e\u092f\u0928 \u0928\u0947", infer_mt._SYSTEM_PROMPT_HI)
'''
T_NEW = r'''        self.assertIn("ONLY when no part of the text can be read", infer_mt._SYSTEM_PROMPT_BASE)
        # MAINT_2026_10_04: since HI_PROMPT_FILE_2026_10_03 production Hindi may come from
        # prompts/hi-production.txt. The BUILT-IN prompt is checked with the file switched off.
        import json, os, subprocess, tempfile
        probe = ("import json, sys; sys.path.insert(0, %r); import infer_mt as m; "
                 "print('J=' + json.dumps([m.PROMPT_VERSIONS['hi'], m.HI_PROMPT_SOURCE, m._SYSTEM_PROMPT_HI]))"
                 % str(Path(__file__).resolve().parent.parent / "scripts"))
        env = dict(os.environ, PYTHONIOENCODING="utf-8",
                   SA_HI_PROMPT_FILE=os.path.join(tempfile.gettempdir(), "no_such_hi_prompt_maint_20261004.txt"))
        p = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                           encoding="utf-8", env=env)
        line = [l for l in p.stdout.splitlines() if l.startswith("J=")]
        self.assertTrue(line, p.stdout + p.stderr)
        ver, src, hi = json.loads(line[-1][2:])
        self.assertEqual((ver, src), ("hi-v3-2026-09-27", "built-in"))
        self.assertIn("\u0906\u0902\u0936\u093f\u0915 \u0915\u094d\u0937\u0924\u093f", hi)
        self.assertNotIn("\u0935\u0948\u0936\u092e\u094d\u092a\u093e\u092f\u0928 \u0928\u0947", hi)
        if infer_mt.HI_PROMPT_SOURCE != "built-in":   # a reviewed file is active: versioned by content
            self.assertRegex(infer_mt.PROMPT_VERSIONS["hi"], r"^hi-file-[0-9a-f]{10}$")
'''

I_OLD = '''        if args.cmd == "approve":
            for i in args.id:
                approve(con, i); print("  #%d approved" % i)
            return 0
'''
I_NEW = '''        if args.cmd == "approve":   # MAINT_2026_10_04: skip and continue, never stop half-way
            bad = 0
            for i in args.id:
                row = get(con, i)
                if row["status"] == "approved":
                    print("  skip #%d: already approved" % i); continue
                if row["status"] != "draft" or not row["path"]:
                    print("  skip #%d: it is %s%s - only a draft with an image can be approved"
                          % (i, row["status"], "" if row["path"] else " with no image yet")); bad += 1; continue
                approve(con, i); print("  #%d approved" % i)
            return 1 if bad else 0
'''

R_OLD = '''            to_write.append((fname, recs))
'''
R_NEW = '''            # MAINT_2026_10_04: one file per source PAGE. A page held by several passages
            # (a segmented source) used to be written once per passage, each open('w')
            # replacing the last - only its final passage survived. Merge instead.
            if to_write and to_write[-1][0] == fname:
                to_write[-1][1].extend(recs)
            else:
                to_write.append((fname, recs))
'''

TARGETS = [(Path("tests/test_translation_filters2.py"), T_OLD, T_NEW),
           (Path("scripts/images.py"), I_OLD, I_NEW),
           (Path("scripts/resegment_doc.py"), R_OLD, R_NEW)]


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    for p, _, _ in TARGETS:
        if not p.exists():
            print("FAIL: %s not found. Run from the repo root." % p); return 2
    loaded = [(p, *load(p), old, new) for p, old, new in TARGETS]
    marked = [MARK in src for p, src, nl, old, new in loaded]
    if all(marked):
        print("Already patched (%s). Nothing to do." % MARK); return 0
    if any(marked):
        print("REFUSING: marker in some files only - inspect by hand."); return 1
    problems, out = [], []
    for p, src, nl, old, new in loaded:
        n = src.count(old)
        if n != 1:
            problems.append("%s: anchor matched %d times, expected 1" % (p, n))
        else:
            out.append((p, src.replace(old, new), nl))
    if problems:
        print("REFUSING TO WRITE:"); [print("  " + x) for x in problems]; return 1
    if args.check:
        print("CHECK OK: 3 anchored edits. Nothing written."); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    tmps = []
    for p, text, nl in out:
        t = p.with_name(p.name + ".tmp_maint")
        t.write_bytes(text.replace("\n", nl).encode("utf-8"))
        try:
            py_compile.compile(str(t), doraise=True)
        except py_compile.PyCompileError as e:
            for x, _ in tmps + [(t, p)]:
                x.unlink(missing_ok=True)
            print("REFUSING TO WRITE: %s would not compile:\n%s" % (p, e)); return 1
        tmps.append((t, p))
    for t, p in tmps:
        shutil.copy2(p, p.with_name(p.name + ".bak_maint_" + stamp))
    for t, p in tmps:
        os.replace(t, p)
        print("patched %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
