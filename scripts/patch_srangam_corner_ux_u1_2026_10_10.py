#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_corner_ux_u1_2026_10_10.py  (2026-10-10)  CORNER_UX_U1_2026_10_10

For the SRANGAM repo (run from D:\\srangam-42267, on main, after NAV_RBAC_2026_10_10). The Researchers'
Corner, guided (docs/CORNER_UX_U1_2026-10-10.md in the automaton repo):
  - src/pages/corpus/CorpusCorner.tsx: Ask the desk leads with the offering so far, the text (grouped:
    waiting for their first story, with stories; "Surprise me"), where to begin (no forms until a text
    is chosen), what the text has, "What would you like to make?" (?goal=) and "Ready in this text"
    ("Set it up" fills a form and asks nothing); passages chosen in the text; placeholders that no
    longer look like values; a line to Learn after a request and on an empty My requests.
  - src/lib/cornerGuide.ts, src/components/corpus/CornerGuide.tsx, src/components/corpus/PassagePicker.tsx:
    new (the picker is its own chunk, loaded when first opened).
  - src/components/corpus/CornerPanels.tsx: Reply-to's placeholder and hint (nartiang.org has no MX), the
    site address's placeholder.
  - src/pages/corpus/CorpusAnthology.tsx: a researcher is offered approved stories only (as
    corner_collection_save accepts from her, once C13 shows her drafts).
  - src/__tests__/corner-ux-u1.test.tsx: new (17 tests).
  - docs/RELIABILITY_AUDIT.md: Phase AE appended (invariants 47-49).
The files travel in the automaton repository, docs/srangam/CORNER_UX_U1_2026-10-10/. Each replaced file is
written only over the exact version main has (md5, line endings ignored) and keeps its own line endings;
a file changed since is refused, never overwritten. All-or-nothing; backups .bak_cornerux_<date>.
Re-running changes nothing. The site works with the database as it is: corner_offering() (C13) is used
once it is there, and C13 also lets researchers see the drafts the Corner already lets them act on.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_corner_ux_u1_2026_10_10.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_corner_ux_u1_2026_10_10.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "CORNER_UX_U1_2026_10_10"
PREREQ = ("src/lib/corpusAccess.ts", "NAV_RBAC_2026_10_10")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "CORNER_UX_U1_2026-10-10"

# path -> md5 of the LF text main has (ab15244)
REPLACE = {
    "src/pages/corpus/CorpusCorner.tsx": "305cadeba95032ac0fd05e7d09b148db",
    "src/components/corpus/CornerPanels.tsx": "7af5131feeb75da0a19ed3109ffde33a",
    "src/pages/corpus/CorpusAnthology.tsx": "099eb43a9b156b21ae05c935ad4d1714",
}
NEW = ["src/lib/cornerGuide.ts", "src/components/corpus/CornerGuide.tsx", "src/components/corpus/PassagePicker.tsx",
       "src/__tests__/corner-ux-u1.test.tsx"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "NAV_RBAC_2026_10_10"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAE.md"


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
        print("NOTE: %s is not in this checkout; Phase AE is not appended." % AUDIT)
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
                shutil.copy2(p, p.with_name(p.name + ".bak_cornerux_" + stamp))
            p.parent.mkdir(parents=True, exist_ok=True)
            t = p.with_name(p.name + ".tmp_cornerux")
            t.write_bytes(data); os.replace(t, p)
            done.append(rel)
            print("wrote %s" % rel)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_cornerux_%s copies: %s" % (e, stamp, ", ".join(done)))
        return 3
    print("\nNext: npm run typecheck ; npx vitest run ; npm run build")
    print("git add -- " + " ".join(rel for rel, _d in todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
