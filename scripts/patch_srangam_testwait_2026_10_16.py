#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_srangam_testwait_2026_10_16.py  (2026-10-16)  TEST_WAIT_2026_10_16

For the SRANGAM repo (run from D:\\srangam-42267, on main, with ORNAMENT_2026_10_16: 55fadc6 or later). On 16 Oct the
suite (npx vitest run) was run while the automaton's benchmark was running: six tests failed in one run (reader-nav
and texts-reader at Vitest's 5 s test timeout, a link not yet shown), one other in the next (corner-mail: the Settings
checkbox not found within Testing Library's 1 s), the jsdom environment taking 527 s over 41 files. The failures moved
between runs, and none is in the code the ornament release changed: the waits are too short for a busy computer.
  - src/test/setup.ts: configure({ asyncUtilTimeout: 5000 }) from @testing-library/react (it passes it to
    @testing-library/dom): findBy* and waitFor wait up to 5 s;
  - vitest.config.ts: testTimeout 20000 (a test may take 20 s);
  - src/__tests__/test-wait.test.ts: new, the two settings asserted (2 tests);
  - docs/RELIABILITY_AUDIT.md: Phase AJ appended (invariant 57).
A test that is wrong still fails, a few seconds later. Nothing the site builds or serves changes. Each file is edited
only over the exact version main has (md5 of its text, line endings ignored), keeping its line endings; all or
nothing; backups .bak_testwait_<date>. Re-running changes nothing.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_testwait_2026_10_16.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_testwait_2026_10_16.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, shutil, sys
from pathlib import Path

MARK = "TEST_WAIT_2026_10_16"
TAG = "testwait"
AUDIT = "docs/RELIABILITY_AUDIT.md"
AUDIT_NEEDS = "ORNAMENT_2026_10_16"

# path -> (md5 of the LF text main has (55fadc6), [(anchor, replacement)])
EDITS = {
    "src/test/setup.ts": ("a597da02664a6f231e4d34331e0fc962", [(
        "import '@testing-library/jest-dom';\n"
        "import { SANCTIONED_OVERFLOW_RE, hasSanctionedInlineOverflowX } from './overflow-rules';\n",
        "import '@testing-library/jest-dom';\n"
        "import { configure } from '@testing-library/react';\n"
        "import { SANCTIONED_OVERFLOW_RE, hasSanctionedInlineOverflowX } from './overflow-rules';\n"
        "\n"
        "// TEST_WAIT_2026_10_16: findBy* and waitFor wait up to 5 s, not Testing Library's 1 s. The suite runs 41 files at\n"
        "// once in jsdom; on a busy computer a page that renders correctly took longer than 1 s to show (16 Oct). A test\n"
        "// that is wrong still fails, a few seconds later. vitest.config.ts gives a test 20 s to match.\n"
        "configure({ asyncUtilTimeout: 5000 });\n")]),
    "vitest.config.ts": ("ee246b8cf2b1df766db091a758c55296", [(
        "    globals: true,\n",
        "    globals: true,\n"
        "    testTimeout: 20000,   // TEST_WAIT_2026_10_16: a test may take 20 s on a busy computer (Vitest's default: 5 s)\n")]),
}

NEW = {"src/__tests__/test-wait.test.ts": """/**
 * TEST_WAIT_2026_10_16 - the suite's waits, set once: findBy* and waitFor wait up to 5 s (src/test/setup.ts), a test
 * may take 20 s (vitest.config.ts). On 16 Oct, on a busy computer, tests that render correctly failed at the old
 * waits (1 s and 5 s), a different one in each run. A test that needs more says why.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { getConfig } from '@testing-library/react';

describe('the suite waits as a busy computer needs (TEST_WAIT_2026_10_16)', () => {
  it('findBy* and waitFor wait up to 5 s', () => {
    expect(getConfig().asyncUtilTimeout).toBe(5000);
  });

  it('a test may take 20 s', () => {
    const cfg = readFileSync(resolve(__dirname, '../../vitest.config.ts'), 'utf8');
    expect(cfg).toMatch(/testTimeout:\\s*20000/);
  });
});
"""}

AUDIT_TEXT = """## Phase AJ - The tests wait as a busy computer needs (TEST_WAIT_2026_10_16, 2026-10-16)

On 16 Oct the suite was run while the automaton's benchmark was running. Six tests failed in one run (reader-nav and
texts-reader at Vitest's 5 s test timeout; a link not yet shown), one other in the next (corner-mail: the Settings
checkbox not found within Testing Library's 1 s), the jsdom environment taking 527 s over 41 files. The failures moved
between runs and none was in the code the ornament release changed (Phase AI): the waits were too short for a busy
computer, not the pages wrong.

### AJ.1 - What changes
- src/test/setup.ts: configure({ asyncUtilTimeout: 5000 }) (@testing-library/react, passed to @testing-library/dom):
  findBy* and waitFor wait up to 5 s.
- vitest.config.ts: testTimeout 20000.
- src/__tests__/test-wait.test.ts: the two settings asserted (2 tests).
- A test that is wrong still fails, a few seconds later. Nothing the site builds or serves changes.

### Invariants added (Phase AJ)
57. The suite's waits are set once, in the setup and the config (5 s for an element to appear, 20 s for a test), not
    test by test; a test that needs more says why in a comment.
"""


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
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo = []
    for rel, (want, edits) in EDITS.items():
        p = root / rel
        if not p.exists():
            print("REFUSE: %s not found. Nothing written." % rel); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already %s)" % (rel, MARK)); continue
        if md5(lf(raw)) != want:
            print("REFUSE: %s is not the version main had (md5 %s, expected %s); it changed since. Nothing written."
                  % (rel, md5(lf(raw)), want)); return 1
        text = lf(raw).decode("utf-8")
        for k, (old, new) in enumerate(edits, 1):
            if text.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (rel, k, text.count(old)))
                return 1
            text = text.replace(old, new, 1)
        out = text.encode("utf-8")
        if crlf_style(raw):
            out = out.replace(b"\n", b"\r\n")
        todo.append((rel, out))
    for rel, body in NEW.items():
        p = root / rel
        data = body.encode("utf-8")
        if p.exists():
            if lf(p.read_bytes()) == lf(data):
                print("skip %s (already there)" % rel); continue
            print("REFUSE: %s exists and differs. Nothing written." % rel); return 1
        todo.append((rel, data))
    a = root / AUDIT
    if a.exists():
        raw = a.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (AUDIT, MARK))
        elif AUDIT_NEEDS.encode() not in raw:
            print("REFUSE: %s has no %s phase (apply that release first). Nothing written." % (AUDIT, AUDIT_NEEDS)); return 1
        else:
            nl = b"\r\n" if crlf_style(raw) else b"\n"
            body = raw if raw.endswith(b"\n") else raw + nl
            todo.append((AUDIT, body + nl + AUDIT_TEXT.encode("utf-8").replace(b"\n", nl)))
    else:
        print("NOTE: %s is not in this checkout; Phase AJ is not appended." % AUDIT)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
