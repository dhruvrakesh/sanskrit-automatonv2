#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_load_l2_2026_10_09.py  (2026-10-09)  LOAD_L2_2026_10_09

For the SRANGAM repo (run from D:\\srangam-42267, on main, after STATE_LEARN_2026_10_09). Two surgical
changes to the first visit, measured on a production build of main 84409ca (docs/LOAD_L2_2026-10-09.md):
  - src/components/home/GeomythologySection.tsx: "samudra" was wrapped in CulturalTermTooltip, which
    downloads the whole cultural-terms dataset (547.9 kB, 132.4 kB gzip) on every home visit to look the
    word up. The word is not in the dataset, so the tooltip only ever rendered a plain <span>. It is
    now that <span>. Saving: the 548 kB request on every home visit (unless a live article card shows
    a {{cultural:...}} term, which still loads it as before).
  - src/App.tsx: the two toast hosts (Radix toaster and sonner) load right after the first render,
    inside a Suspense, instead of in the entry bundle (-46.7 kB, -13.1 kB gzip before first paint,
    every route). Radix toasts raised before the host mounts are kept in use-toast's memory and shown.
  - src/__tests__/load-l2.test.ts: new (3 tests).
Anchored edits: each anchor must be found exactly once in the exact version main has (md5 with line
endings ignored); a file changed since is refused, never overwritten. All-or-nothing; backups
.bak_load_l2_<date>; each file keeps its own line endings. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_load_l2_2026_10_09.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_load_l2_2026_10_09.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "LOAD_L2_2026_10_09"
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "LOAD_L2_2026-10-09"

GEO_OLD_IMPORT = "import { CulturalTermTooltip } from '@/components/language/CulturalTermTooltip';\n"
GEO_OLD_ITEM = ("      // Use CulturalTermTooltip for terms that exist in the cultural terms\n"
                "      // dataset. For example, samudra (sea) appears in `cultural-terms.ts`.\n"
                "      <>Intertidal ecology & <CulturalTermTooltip term=\"samudra\">samudra</CulturalTermTooltip> memory</>,\n")
GEO_NEW_ITEM = ("      // LOAD_L2_2026_10_09: \"samudra\" is not in the cultural-terms dataset, so CulturalTermTooltip only\n"
                "      // ever rendered it as this plain <span>, after downloading the whole 548 kB dataset to find that\n"
                "      // out. Wrap a term in CulturalTermTooltip again once it is in the dataset.\n"
                "      <>Intertidal ecology & <span>samudra</span> memory</>,\n")

APP_OLD_IMPORTS = ('import { Toaster } from "@/components/ui/toaster";\n'
                   'import { Toaster as Sonner } from "@/components/ui/sonner";\n')
APP_NEW_IMPORTS = ('// LOAD_L2_2026_10_09: the toast hosts load right after the first render instead of in the entry.\n'
                   '// Radix toasts raised before the host mounts are kept in use-toast\'s memory state and shown on mount.\n'
                   'const Toaster = lazy(() => import("@/components/ui/toaster").then((m) => ({ default: m.Toaster })));\n'
                   'const Sonner = lazy(() => import("@/components/ui/sonner").then((m) => ({ default: m.Toaster })));\n')
APP_OLD_HOSTS = ("                <Toaster />\n"
                 "                <Sonner />\n")
APP_NEW_HOSTS = ("                <Suspense fallback={null}>\n"
                 "                  <Toaster />\n"
                 "                  <Sonner />\n"
                 "                </Suspense>\n")

# path -> (md5 of the LF text as main has it, [(old, new), ...])
EDITS = {
    "src/components/home/GeomythologySection.tsx": ("05a3660265db933a67b586aab825837a",
                                                   [(GEO_OLD_IMPORT, ""), (GEO_OLD_ITEM, GEO_NEW_ITEM)]),
    "src/App.tsx": ("e85399a071cd9febebda7379ebb1f1cc",
                    [(APP_OLD_IMPORTS, APP_NEW_IMPORTS), (APP_OLD_HOSTS, APP_NEW_HOSTS)]),
}
NEW_FILES = ["src/__tests__/load-l2.test.ts"]


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    root = Path.cwd()
    if not (root / "src" / "App.tsx").exists() or not (root / "package.json").exists():
        print("FAIL: run this from the Srangam repo root (D:\\srangam-42267)."); return 2
    app = (root / "src" / "App.tsx").read_bytes()
    if b"STATE_LEARN_2026_10_09" not in app:
        print("REFUSE: src/App.tsx has no STATE_LEARN_2026_10_09: apply that release first. Nothing written."); return 1
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []   # (path, bytes)
    for rel, (want, edits) in EDITS.items():
        p = root / rel
        if not p.exists():
            print("REFUSE: %s not found. Nothing written." % rel); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        text = lf(raw)
        if md5(text) != want:
            print("REFUSE: %s is not the version main had (md5 %s, expected %s); it changed since. Nothing written."
                  % (rel, md5(text), want)); return 1
        s = text.decode("utf-8")
        for old, new in edits:
            if s.count(old) != 1:
                print("REFUSE: %s: an anchor is found %d times (expected once). Nothing written." % (rel, s.count(old))); return 1
            s = s.replace(old, new)
        out = s.encode("utf-8")
        if raw.count(b"\r\n") > raw.count(b"\n") // 2:
            out = out.replace(b"\n", b"\r\n")
        todo.append((rel, out))
    for rel in NEW_FILES:
        src, dst = PAYLOAD / rel, root / rel
        data = src.read_bytes()
        if dst.exists():
            if lf(dst.read_bytes()) == lf(data):
                print("skip %s (already there)" % rel); continue
            print("REFUSE: %s exists and differs from the payload. Nothing written." % rel); return 1
        todo.append((rel, data))
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
                shutil.copy2(p, p.with_name(p.name + ".bak_load_l2_" + stamp))
            p.parent.mkdir(parents=True, exist_ok=True)
            t = p.with_name(p.name + ".tmp_load_l2")
            t.write_bytes(data); os.replace(t, p)
            done.append(rel)
            print("wrote %s" % rel)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_load_l2_%s copies: %s" % (e, stamp, ", ".join(done)))
        return 3
    print("\nNext: npm run typecheck ; npx vitest run ; npm run build")
    print("git add -- " + " ".join(rel for rel, _d in todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
