#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_corpus_reader_2026_10_08.py  (2026-10-08)  CORPUS_READER_C5_2026_10_08

For the SRANGAM repo (run from D:\\srangam-42267, on main). Wires the working corpus for signed-in
readers (docs/CORPUS_MIRROR_2026-10-08.md, "Reading it") into three existing files. The new files
must already be in place (they are delivered as files, not by this script):
  src/lib/corpusMirror.ts, src/lib/safeNext.ts, src/components/corpus/CorpusGate.tsx,
  src/pages/corpus/CorpusHome.tsx, src/pages/corpus/CorpusDoc.tsx,
  src/__tests__/corpus-mirror.test.tsx, supabase/functions/search-corpus/index.ts

  src/App.tsx                     two lazy pages and two routes: /corpus and /corpus/:docCode
                                  (lazy, so nothing is added to the entry bundle).
  src/pages/Auth.tsx              ?next=<path on this site> after sign-in; without it the admin
                                  destination (/admin/tags) is unchanged. With next=/corpus... the
                                  card reads "Sign in to read the working corpus".
  src/pages/texts/TextsIndex.tsx  one sentence linking /corpus.

Anchored, all-or-nothing, marker-idempotent; keeps each file's line endings; backups .bak_reader_<date>.
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_corpus_reader_2026_10_08.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_corpus_reader_2026_10_08.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "CORPUS_READER_C5_2026_10_08"

NEEDED = ["src/lib/corpusMirror.ts", "src/lib/safeNext.ts", "src/components/corpus/CorpusGate.tsx",
          "src/pages/corpus/CorpusHome.tsx", "src/pages/corpus/CorpusDoc.tsx",
          "src/__tests__/corpus-mirror.test.tsx", "supabase/functions/search-corpus/index.ts"]

EDITS = {
    "src/App.tsx": [
        ("lazy pages",
         'const TextReader = lazy(() => import("./pages/texts/TextReader"));\n',
         'const TextReader = lazy(() => import("./pages/texts/TextReader"));\n'
         '// ' + MARK + ': the working corpus for signed-in readers\n'
         'const CorpusHome = lazy(() => import("./pages/corpus/CorpusHome"));\n'
         'const CorpusDoc = lazy(() => import("./pages/corpus/CorpusDoc"));\n'),
        ("routes",
         '              <Route path="/texts/:docCode" element={<TextReader />} />\n',
         '              <Route path="/texts/:docCode" element={<TextReader />} />\n'
         '              {/* ' + MARK + ' */}\n'
         '              <Route path="/corpus" element={<CorpusHome />} />\n'
         '              <Route path="/corpus/:docCode" element={<CorpusDoc />} />\n'),
    ],
    "src/pages/Auth.tsx": [
        ("router import",
         'import { useNavigate } from "react-router-dom";\n',
         'import { useNavigate, useSearchParams } from "react-router-dom";\n'
         'import { safeNext } from "@/lib/safeNext";   // ' + MARK + '\n'),
        ("next param",
         '  const navigate = useNavigate();\n'
         '\n'
         '  // Redirect if already logged in\n'
         '  if (user) {\n'
         '    navigate("/admin/tags");\n'
         '    return null;\n'
         '  }\n',
         '  const navigate = useNavigate();\n'
         '  // ' + MARK + ': ?next=/corpus... brings a reader back to the page they came from. Only a\n'
         '  // path on this site is followed; without it the destination is /admin/tags, as before.\n'
         '  const [params] = useSearchParams();\n'
         '  const next = safeNext(params.get("next"));\n'
         '  const reader = !!next && next.startsWith("/corpus");\n'
         '\n'
         '  // Redirect if already logged in\n'
         '  if (user) {\n'
         '    navigate(next ?? "/admin/tags");\n'
         '    return null;\n'
         '  }\n'),
        ("after sign-in",
         '      await signIn(email, password);\n'
         '      navigate("/admin/tags");\n',
         '      await signIn(email, password);\n'
         '      navigate(next ?? "/admin/tags");\n'),
        ("card title",
         '          <CardTitle className="text-2xl font-bold text-center">Srangam Admin</CardTitle>\n'
         '          <CardDescription className="text-center">\n'
         '            Sign in to manage content\n'
         '          </CardDescription>\n',
         '          <CardTitle className="text-2xl font-bold text-center">{reader ? "Srangam" : "Srangam Admin"}</CardTitle>\n'
         '          <CardDescription className="text-center">\n'
         '            {reader ? "Sign in to read the working corpus" : "Sign in to manage content"}\n'
         '          </CardDescription>\n'),
    ],
    "src/pages/texts/TextsIndex.tsx": [
        ("corpus link",
         '          Sanskrit is shown exactly as it was read from the page, damage included.\n'
         '        </p>\n'
         '      </header>\n',
         '          Sanskrit is shown exactly as it was read from the page, damage included.\n'
         '        </p>\n'
         '        {/* ' + MARK + ' */}\n'
         '        <p className="mt-2 text-sm text-muted-foreground">\n'
         '          Signed-in readers can also explore{" "}\n'
         '          <Link to="/corpus" className="text-burgundy hover:underline">the whole working corpus</Link>,\n'
         '          every text on the translation desk before publication.\n'
         '        </p>\n'
         '      </header>\n'),
    ],
}


def load(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("src/App.tsx").exists() or not Path("supabase").is_dir():
        print("FAIL: run from the Srangam repo root (D:\\srangam-42267)."); return 2
    problems = ["new file missing: %s (deliver it first)" % f for f in NEEDED if not Path(f).exists()]
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for rel, edits in EDITS.items():
        p = Path(rel)
        if not p.exists():
            problems.append("%s not found" % rel); continue
        src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        out = src
        for name, old, new in edits:
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        todo.append((p, out.replace("\n", nl).encode("utf-8")))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to patch: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    for p, data in todo:
        shutil.copy2(p, p.with_name(p.name + ".bak_reader_" + stamp))
        t = p.with_name(p.name + ".tmp_reader"); t.write_bytes(data); os.replace(t, p)
        print("patched %s" % p)
    print("Next: npm run typecheck ; npx vitest run ; npm run build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
