#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_admin_status_2026_11_19.py  (2026-11-19)  ADMIN_STATUS_2026_11_19

For the SRANGAM repo (run from D:\\srangam-42267, on main, at VAMSA_WAYIN_2026_11_18: cc32c10 or later; pull first:
Lovable committed after cc32c10). A1 of docs\\ADMIN_REWIRE_2026-11-19.md in the automaton repo: the desk and the site
at a glance, for the super admin (/admin/desk-site, "Desk and site" in the admin sidebar).
  - src/pages/admin/DeskSite.tsx: new; one read-only call (corpus_admin_status()); "as of" and Refresh;
  - src/App.tsx: the route (lazy);
  - src/components/admin/AdminLayout.tsx: the sidebar's entry, super admin only;
  - src/__tests__/desk-site.test.tsx: new;
  - docs/RELIABILITY_AUDIT.md: Phase AV appended (invariant 72).
Needs the automaton's docs/cloud/C30_admin_status_2026-11-19.sql pasted first (until then the page says it is not
switched on yet). No edge function changes.
The files travel in the automaton repository, docs/srangam/ADMIN_STATUS_2026-11-19/. A replaced file is written only
over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since is
refused, never overwritten. All-or-nothing; backups .bak_adminstatus_<date>. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_admin_status_2026_11_19.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_admin_status_2026_11_19.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "ADMIN_STATUS_2026_11_19"
PREREQ = ("src/lib/indexSite.ts", "VAMSA_WAYIN_2026_11_18")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "ADMIN_STATUS_2026-11-19"
TAG = "adminstatus"

# path -> md5 of the LF text main has (cc32c10, VAMSA_WAYIN_2026_11_18)
REPLACE = {
    "src/App.tsx": "8f35093280f22733e6d0ecfa8e27c4b3",
    "src/components/admin/AdminLayout.tsx": "cf018fe035ab52216aa49ae8143ec9bd",
}
NEW = ["src/pages/admin/DeskSite.tsx", "src/__tests__/desk-site.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "VAMSA_WAYIN_2026_11_18"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAV.md"


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def crlf_style(raw: bytes) -> bool:
    return raw.count(b"\r\n") > raw.count(b"\n") // 2


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    root = Path.cwd()
    if not (root / "src" / "lib").is_dir() or not (root / "package.json").exists():
        print("FAIL: run this from the Srangam repo root (D:\\srangam-42267)."); return 2
    pre = root / PREREQ[0]
    if not pre.exists() or PREREQ[1].encode() not in pre.read_bytes():
        print("REFUSE: %s has no %s (apply the kit VAMSA_WAYIN first). Nothing written." % PREREQ); return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for rel, want in REPLACE.items():
        p = root / rel
        if not p.exists():
            print("REFUSE: %s is not here. Nothing written." % rel); return 1
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
        print("NOTE: %s is not in this checkout; Phase AV is not appended." % AUDIT)
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
                shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            p.parent.mkdir(parents=True, exist_ok=True)
            t = p.with_name(p.name + ".tmp_" + TAG)
            t.write_bytes(data); os.replace(t, p)
            done.append(rel)
            print("wrote %s" % rel)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    print("\nNext: npm run typecheck ; npx vitest run ; npm run build")
    print("git add -- " + " ".join(rel for rel, _d in todo))
    print("Then: paste the automaton's docs\\cloud\\C30_admin_status_2026-11-19.sql (B1, the change, A1, A2) if not yet;")
    print("Publish; then open /admin/desk-site as the super admin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
