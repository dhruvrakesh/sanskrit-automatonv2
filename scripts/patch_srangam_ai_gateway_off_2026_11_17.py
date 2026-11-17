#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_ai_gateway_off_2026_11_17.py  (2026-11-17)  AI_GATEWAY_OFF_2026_11_17

For the SRANGAM repo (run from D:\\srangam-42267, on main, at HOME_HEAL_2026_11_14: de1e346 or later). Asked on 17 Nov:
"I1: move the two site functions off the Lovable gateway". The project's rule (Phase H.2d, _shared/ai-provider.ts) and
the owner's: every AI call uses the project's own keys, GEMINI_API_KEY first and OPENAI_API_KEY second, never the
Lovable AI Gateway. Two edge functions still called https://ai.gateway.lovable.dev with LOVABLE_API_KEY:
  - supabase/functions/detect-duplicate-articles/index.ts (the AI comparison of two excerpts),
  - supabase/functions/suggest-tag-categories/index.ts (the admin's tag categories);
both now call ai-provider's generic JSON call (aiExtractCitations: Gemini 2.5 Flash, one retry, then OpenAI
gpt-4o-mini) with telemetry in srangam_ai_usage; when both keys fail they say so and call nothing else.
  - src/__tests__/ai-gateway-off.test.ts: new; fails if any file under supabase/functions names the gateway or its key;
  - docs/RELIABILITY_AUDIT.md: Phase AS appended (invariant 69).
The files travel in the automaton repository, docs/srangam/AI_GATEWAY_OFF_2026-11-17/. A replaced file is written
only over the exact version main has (md5, line endings ignored) and keeps its own line endings; a file changed since
is refused, never overwritten. All-or-nothing; backups .bak_aigwoff_<date>. Re-running changes nothing. No database
change; the site runs the new code once Lovable deploys the two functions.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_ai_gateway_off_2026_11_17.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_ai_gateway_off_2026_11_17.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "AI_GATEWAY_OFF_2026_11_17"
PREREQ = ("supabase/functions/_shared/ai-provider.ts", "export async function aiExtractCitations(")
HERE = Path(__file__).resolve().parent
PAYLOAD = HERE.parent / "docs" / "srangam" / "AI_GATEWAY_OFF_2026-11-17"
TAG = "aigwoff"

# path -> md5 of the LF text main has (de1e346, HOME_HEAL_2026_11_14)
REPLACE = {
    "supabase/functions/detect-duplicate-articles/index.ts": "a6ce65f990bff67e74ed01e6aaddec0b",
    "supabase/functions/suggest-tag-categories/index.ts": "acacb563ea65a7b9a0ed879ea44621dc",
}
NEW = ["src/__tests__/ai-gateway-off.test.ts"]
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "B2_SITE_2026_10_28"
AUDIT_APPEND = "_append/RELIABILITY_AUDIT.phaseAS.md"


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def crlf_style(raw: bytes) -> bool:
    return raw.count(b"\r\n") > raw.count(b"\n") // 2


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    root = Path.cwd()
    if not (root / "supabase" / "functions").is_dir() or not (root / "package.json").exists():
        print("FAIL: run this from the Srangam repo root (D:\\srangam-42267)."); return 2
    pre = root / PREREQ[0]
    if not pre.exists() or PREREQ[1].encode() not in pre.read_bytes():
        print("REFUSE: %s has no %s (the shared AI provider). Nothing written." % PREREQ); return 1
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
        print("NOTE: %s is not in this checkout; Phase AS is not appended." % AUDIT)
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
    print("Then ask Lovable to deploy detect-duplicate-articles and suggest-tag-categories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
