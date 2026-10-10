#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_nav_rbac_2026_10_10.py  (2026-10-10)  NAV_RBAC_2026_10_10

For the SRANGAM repo (run from D:\\srangam-42267, on main, after CORNER_C10_MAIL_2026_10_09). The working
corpus in the site's navigation, by role (it was linked from nowhere in the header):
  - src/components/navigation/HeaderNav.tsx: a "Corpus" menu (Library, Stories, Names, Pictures, Graphic
    novels, Researchers' Corner, Learn, Published texts) for whoever may read the corpus; the same in the
    phone's menu sheet and a "Corpus" tab in its bottom bar; "Admin" for admins only; "Sign in" while
    signed out (it was "Admin" for everyone).
  - src/components/navigation/CorpusMenu.tsx, src/lib/corpusAccess.ts: new. Who may read is taken from the
    roles the site already holds (researcher, admin, super_admin: no request); an account with none of
    them asks corpus_reader_allowed() once (a reader list, or the 'signed_in' mode).
  - src/components/admin/AdminLayout.tsx: a "Working corpus" group in the admin sidebar (Library, Corner,
    Learn).
  - src/pages/corpus/CorpusHome.tsx: one line on where to start (Learn, the Corner).
  - src/__tests__/nav-rbac.test.tsx: new (11 tests).
  - docs/RELIABILITY_AUDIT.md: Phase AD appended (invariants 44-46).
The files travel in the automaton repository, docs/srangam/NAV_RBAC_2026-10-10/. Each replaced file is
written only over the exact version main has (md5, line endings ignored) and keeps its own line endings;
a file changed since is refused, never overwritten. All-or-nothing; backups .bak_navrbac_<date>.
Re-running changes nothing. No database change: corpus_reader_allowed() is C5's, granted to authenticated.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_nav_rbac_2026_10_10.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_nav_rbac_2026_10_10.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "NAV_RBAC_2026_10_10"
PREREQ = ("src/lib/cornerMail.ts", "CORNER_C10_MAIL_2026_10_09")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "NAV_RBAC_2026-10-10"

# path -> md5 of the LF text main has (852d852)
REPLACE = {
    "src/components/navigation/HeaderNav.tsx": "8605e72373bf8b53610f52e770b22865",
    "src/components/admin/AdminLayout.tsx": "e68860d0d32e94aba3cba065bbca4080",
    "src/pages/corpus/CorpusHome.tsx": "1cc07cc0fcb812af415c6aa0fcc9dabb",
}
NEW = ["src/lib/corpusAccess.ts", "src/components/navigation/CorpusMenu.tsx", "src/__tests__/nav-rbac.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "CORNER_C10_MAIL_2026_10_09"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAD.md"


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def crlf_style(raw: bytes) -> bool:
    return raw.count(b"\r\n") > raw.count(b"\n") // 2


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    root = Path.cwd()
    if not (root / "src" / "App.tsx").exists() or not (root / "package.json").exists():
        print("FAIL: run this from the Srangam repo root (D:\\srangam-42267)."); return 2
    pre = root / PREREQ[0]
    if not pre.exists() or PREREQ[1].encode() not in pre.read_bytes():
        print("REFUSE: %s has no %s: apply that release first. Nothing written." % PREREQ); return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for rel, want in REPLACE.items():
        p = root / rel
        if not p.exists():
            print("REFUSE: %s not found. Nothing written." % rel); return 1
        raw = p.read_bytes()
        data = (PAYLOAD / rel).read_bytes()
        if lf(raw) == lf(data):
            print("skip %s (already %s)" % (rel, MARK)); continue
        if md5(lf(raw)) != want:
            print("REFUSE: %s is not the version main had (md5 %s, expected %s); it changed since. Nothing written."
                  % (rel, md5(lf(raw)), want)); return 1
        out = lf(data)
        if crlf_style(raw):
            out = out.replace(b"\n", b"\r\n")
        todo.append((rel, out))
    for rel in NEW:
        p = root / rel
        data = (PAYLOAD / rel).read_bytes()
        if p.exists():
            if lf(p.read_bytes()) == lf(data):
                print("skip %s (already there)" % rel); continue
            print("REFUSE: %s exists and differs from the payload. Nothing written." % rel); return 1
        todo.append((rel, data))
    a = root / AUDIT
    if a.exists():
        raw = a.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (AUDIT, MARK))
        elif AUDIT_NEEDS.encode() not in raw:
            print("REFUSE: %s has no %s phase (apply that release first). Nothing written." % (AUDIT, AUDIT_NEEDS)); return 1
        else:
            text = (PAYLOAD / AUDIT_APPEND).read_bytes()
            nl = b"\r\n" if crlf_style(raw) else b"\n"
            body = raw if raw.endswith(b"\n") else raw + nl
            todo.append((AUDIT, body + nl + lf(text).replace(b"\n", nl)))
    else:
        print("NOTE: %s is not in this checkout; Phase AD is not appended." % AUDIT)
    if not todo:
        print("Nothing to do: %s is in place." % MARK); return 0
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(todo))
        for rel, _d in todo:
            print("  " + rel)
        return 0
    done = []
    try:
        for rel, data in todo:
            p = root / rel
            if p.exists():
                shutil.copy2(p, p.with_name(p.name + ".bak_navrbac_" + stamp))
            p.parent.mkdir(parents=True, exist_ok=True)
            t = p.with_name(p.name + ".tmp_navrbac")
            t.write_bytes(data); os.replace(t, p)
            done.append(rel)
            print("wrote %s" % rel)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_navrbac_%s copies: %s" % (e, stamp, ", ".join(done)))
        return 3
    print("\nNext: npm run typecheck ; npx vitest run ; npm run build")
    print("git add -- " + " ".join(rel for rel, _d in todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
