#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_rbac_2026_10_08.py  (2026-10-08)  RBAC_RESEARCHERS_2026_10_08

For the SRANGAM repo (run from D:\\srangam-42267, on main, after CORPUS_LIBRARY_C6_2026_10_08). Roles
on the site: the super admin's /admin/researchers (invite fellow researchers, withdraw invitations,
remove researchers, choose who may read the working corpus, the audit log), the researcher's
/invite/:token (sign in or create an account, accept, on to /corpus), roles in AuthContext
(roles, isSuperAdmin, isResearcher, refreshRoles), sign-up that comes back to the invitation, the
Researchers link and the Super admin badge in the admin sidebar, and a corpus refusal that says
how researchers get in. Needs docs/cloud/C7a and C7 in the database; before them the site works
as it does now (my_roles() missing = roles from has_role; the new pages say C7 is not applied).

The files travel in the automaton repository, docs/srangam/RBAC_2026-10-08/, under the paths they
take in Srangam. This script copies them in:
  - a NEW file is written only where nothing is, or where the same file already is;
  - a REPLACED file is written only over the exact version it was made from (md5, line endings
    ignored), so a file changed since (by Lovable or by hand) is refused, never overwritten;
  - src/App.tsx gets four anchored insertions (two lazy pages, two routes), marker-idempotent;
  - every payload file is checked against its recorded md5 first.
All-or-nothing: everything is checked before anything is written. Backups .bak_rbac_<date>.
A replaced file keeps its own line endings; new files are LF. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_rbac_2026_10_08.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_rbac_2026_10_08.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "RBAC_RESEARCHERS_2026_10_08"
PAYLOAD = Path(__file__).resolve().parent.parent / "docs" / "srangam" / "RBAC_2026-10-08"

# (path in Srangam, md5 of the payload file, md5 of the version it replaces or None for a new file)
FILES = [
    ('docs/RBAC_RESEARCHERS_2026-10-08.md', '1523911bc9f148fc906f5288743ed4d1', None),
    ('src/__tests__/auth-role.test.tsx', '5b59bbf59e523dfc70684777c5993315', 'af30da3d3551e02d862f522d0c6678ef'),
    ('src/__tests__/rbac-auth.test.tsx', '38de7f975609889126db44b18a38e4c9', None),
    ('src/__tests__/rbac-pages.test.tsx', '80821b43c9813a4c253f59ce3611ef29', None),
    ('src/components/admin/AdminLayout.tsx', 'e68860d0d32e94aba3cba065bbca4080', 'bc99dffb77c618c61db6d8874213e5b1'),
    ('src/components/corpus/CorpusGate.tsx', '3fb2a0969a5f173aaca6194a9d077629', '0a96c453b11daa51c28cfa6c3a8fb8c6'),
    ('src/contexts/AuthContext.tsx', '536da1528f195179509af5a509d00546', 'b20f637b2e733fd2bd8aa9309b766a30'),
    ('src/lib/rbac.ts', 'eea748b124bdba98280ac9195648df40', None),
    ('src/pages/Auth.tsx', '666dff80e54ce39cde982fc1a71edf9f', '4eb4b928ddd9bc1cc9b5d7e5320e17f1'),
    ('src/pages/InviteAccept.tsx', '4d192fbfe15352992f52cd2d324b83f7', None),
    ('src/pages/admin/Researchers.tsx', '785bec298d1c25f82a315be87e9a7b01', None),
]

APP = "src/App.tsx"
APP_EDITS = [
    ("lazy invite page",
     'const CorpusNames = lazy(() => import("./pages/corpus/CorpusNames"));\n',
     'const CorpusNames = lazy(() => import("./pages/corpus/CorpusNames"));\n'
     "// " + MARK + ": where an invited researcher lands\n"
     'const InviteAccept = lazy(() => import("./pages/InviteAccept"));\n'),
    ("lazy admin page",
     'const CorpusCorrelations = lazy(() => import("./pages/admin/CorpusCorrelations"));\n',
     'const CorpusCorrelations = lazy(() => import("./pages/admin/CorpusCorrelations"));\n'
     'const Researchers = lazy(() => import("./pages/admin/Researchers"));   // ' + MARK + '\n'),
    ("invite route",
     '                  <Route path="/auth" element={<Auth />} />\n',
     '                  <Route path="/auth" element={<Auth />} />\n'
     '                  {/* ' + MARK + ': research invitations */}\n'
     '                  <Route path="/invite/:token" element={<InviteAccept />} />\n'),
    ("admin route",
     '                    <Route path="data-health" element={<DataHealth />} />\n',
     '                    <Route path="data-health" element={<DataHealth />} />\n'
     '                    <Route path="researchers" element={<Researchers />} />\n'),
]


def md5_lf(b: bytes) -> str:
    return hashlib.md5(b.replace(b"\r\n", b"\n")).hexdigest()


def nl_of(raw: bytes) -> bytes:
    return b"\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else b"\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path(APP).exists() or not Path("supabase").is_dir():
        print("FAIL: run from the Srangam repo root (D:\\srangam-42267)."); return 2
    if not PAYLOAD.is_dir():
        print("FAIL: the payload folder is missing: %s" % PAYLOAD); return 2
    if not Path("src/lib/corpusLibrary.ts").exists():
        print("REFUSE: CORPUS_LIBRARY_C6_2026_10_08 is not applied (src/lib/corpusLibrary.ts is missing)."); return 1
    problems, todo, skip = [], [], []
    for rel, want, old in FILES:
        src = PAYLOAD / rel
        if not src.exists():
            problems.append("payload file missing: %s" % rel); continue
        data = src.read_bytes()
        if hashlib.md5(data).hexdigest() != want:
            problems.append("payload file differs from the one released: %s" % rel); continue
        dest = Path(rel)
        if dest.exists():
            raw = dest.read_bytes()
            have = md5_lf(raw)
            if have == want:
                skip.append(rel); continue
            if old is None:
                problems.append("%s already exists and is not this file (left alone)" % rel); continue
            if have != old:
                problems.append("%s has changed since this patch was made (md5 %s, expected %s)" % (rel, have, old)); continue
            if nl_of(raw) == b"\r\n":
                data = data.replace(b"\n", b"\r\n")
            todo.append((dest, data, True))
        else:
            if old is not None:
                problems.append("%s not found (it should exist and be replaced)" % rel); continue
            todo.append((dest, data, False))

    app = Path(APP)
    raw = app.read_bytes()
    nl = nl_of(raw).decode()
    text = raw.decode("utf-8").replace("\r\n", "\n")
    if MARK in text:
        skip.append(APP)
    else:
        out = text
        for name, anchor, new in APP_EDITS:
            c = out.count(anchor)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (APP, name, c)); continue
            out = out.replace(anchor, new, 1)
        todo.append((app, out.replace("\n", nl).encode("utf-8"), True))

    for rel in skip:
        print("skip %s (already this version)" % rel)
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write (%d replaced or edited, %d new). Nothing written."
              % (len(todo), sum(1 for t in todo if t[2]), sum(1 for t in todo if not t[2])))
        return 0
    if not todo:
        print("Nothing to do."); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    done = []
    try:
        for dest, data, replaced in todo:
            dest.parent.mkdir(parents=True, exist_ok=True)
            bak = None
            if replaced:
                bak = dest.with_name(dest.name + ".bak_rbac_" + stamp)
                shutil.copy2(dest, bak)
            tmp = dest.with_name(dest.name + ".tmp_rbac")
            tmp.write_bytes(data)
            os.replace(tmp, dest)
            done.append((dest, bak))
            print("%s %s" % ("replaced" if replaced else "added", dest.as_posix()))
    except Exception as e:
        print("FAIL while writing: %s: %s. Restoring." % (type(e).__name__, e))
        for dest, bak in done:
            if bak is not None:
                shutil.copy2(bak, dest)
            elif dest.exists():
                dest.unlink()
            print("restored %s" % dest)
        return 2
    print("Next: npm run typecheck ; npx vitest run ; npm run build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
