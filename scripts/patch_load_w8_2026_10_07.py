#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_load_w8_2026_10_07.py  (2026-10-07)  LOAD_W8_2026_10_07

For the SRANGAM repo (run from D:\\srangam-42267, on main). Two load-time fixes measured on
2026-10-07 (sourcemap of the production build, and the live site's resource timings):

  index.html   The home page's hero picture (172 KB WebP) was preloaded at high priority on EVERY
               page, because index.html is the shell of every route: /texts, /articles/... all
               downloaded it first, competing with the scripts. A four-line inline script now adds
               the very same preload only when the address is the home page ("/"), so the home page
               is unchanged and every other page skips 172 KB.
  src/App.tsx  AdminLayout (and the shadcn sidebar it pulls in, about 15 KB) was imported eagerly,
               so every visitor downloaded the admin shell. It is now lazy like the admin pages it
               wraps; the routes already sit inside <Suspense>.
  src/__tests__/load-w8.test.ts   new: the preload runs on "/" only (the script is executed against
               a fake document), and AdminLayout stays out of the entry.

Anchored, all-or-nothing, marker-idempotent; keeps each file's line endings; backups
.bak_w8_<date>. Nothing else changes: no dependency, no route, no component.
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_load_w8_2026_10_07.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_load_w8_2026_10_07.py"
Then: npm run typecheck ; npx vitest run src/__tests__/load-w8.test.ts src/__tests__/texts-reader.test.tsx ; npm run build
"""
from __future__ import annotations
import argparse, datetime, os, shutil, sys
from pathlib import Path

MARK = "LOAD_W8_2026_10_07"

HERO = "/images/hero_indian-ocean_aerial_21x9_v1.webp"

EDITS = {
    "index.html": [(
        "hero preload",
        '    <link rel="preload" as="image" href="' + HERO + '" type="image/webp" fetchpriority="high" />\n',
        "    <!-- " + MARK + ": the hero is on the home page only, so only the home page preloads it (it was\n"
        "         172 KB at high priority on every route, ahead of the scripts). Same link as before. -->\n"
        "    <script>\n"
        "      (function () {\n"
        "        var p = location.pathname;\n"
        "        if (p !== '/' && p !== '/index.html') return;\n"
        "        var l = document.createElement('link');\n"
        "        l.rel = 'preload'; l.as = 'image'; l.type = 'image/webp'; l.href = '" + HERO + "';\n"
        "        l.setAttribute('fetchpriority', 'high');\n"
        "        document.head.appendChild(l);\n"
        "      })();\n"
        "    </script>\n",
    )],
    "src/App.tsx": [(
        "lazy admin layout",
        'import { AdminLayout } from "./components/admin/AdminLayout";\n',
        "// " + MARK + ": admin only, so out of the entry bundle (with the sidebar it uses).\n"
        'const AdminLayout = lazy(() => import("./components/admin/AdminLayout").then((m) => ({ default: m.AdminLayout })));\n',
    )],
}

TEST_PATH = "src/__tests__/load-w8.test.ts"
TEST = """import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

// LOAD_W8_2026_10_07 - keep the first download small: the hero preload only on the home page, and
// the admin shell out of the entry bundle.
const here = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(here, '../..');
const html = readFileSync(resolve(ROOT, 'index.html'), 'utf-8');
const app = readFileSync(resolve(ROOT, 'src/App.tsx'), 'utf-8');
const HERO = '/images/hero_indian-ocean_aerial_21x9_v1.webp';

function runHeadScript(pathname: string) {
  const code = (html.match(/<script>([\\s\\S]*?)<\\/script>/) || [])[1] || '';
  const added: any[] = [];
  const doc = {
    createElement: () => {
      const el: any = {};
      Object.defineProperty(el, 'setAttribute', { value: (k: string, v: string) => { el[k] = v; } });
      return el;
    },
    head: { appendChild: (el: any) => { added.push(el); } },
  };
  new Function('location', 'document', code)({ pathname }, doc);
  return added;
}

describe('first download', () => {
  it('no static preload of the hero picture is left in the shell', () => {
    expect(html).not.toMatch(/<link[^>]*rel="preload"[^>]*hero_indian-ocean/);
  });

  it('the home page still preloads it, at high priority', () => {
    const added = runHeadScript('/');
    expect(added.length).toBe(1);
    expect(added[0]).toMatchObject({ rel: 'preload', as: 'image', type: 'image/webp', href: HERO, fetchpriority: 'high' });
  });

  it('other pages do not', () => {
    for (const p of ['/texts', '/texts/markandeya_purana', '/articles/x', '/admin']) {
      expect(runHeadScript(p)).toEqual([]);
    }
  });

  it('the admin layout is loaded lazily', () => {
    expect(app).not.toMatch(/^import \\{ AdminLayout \\}/m);
    expect(app).toMatch(/const AdminLayout = lazy\\(/);
  });
});
"""


def load(p: Path):
    raw = p.read_bytes(); crlf = raw.count(b"\r\n")
    return raw.decode("utf-8").replace("\r\n", "\n"), ("\r\n" if crlf > (raw.count(b"\n") - crlf) else "\n")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not Path("src/App.tsx").exists() or not Path("index.html").exists():
        print("FAIL: run from the Srangam repo root (D:\\srangam-42267)."); return 2
    stamp = datetime.date.today().strftime("%Y%m%d")
    todo, problems = [], []
    for rel, edits in EDITS.items():
        p = Path(rel); src, nl = load(p)
        if MARK in src:
            print("skip %s (already carries %s)" % (rel, MARK)); continue
        out = src
        for name, old, new in edits:
            c = out.count(old)
            if c != 1:
                problems.append("%s: anchor '%s' found %d times (want 1)" % (rel, name, c)); continue
            out = out.replace(old, new, 1)
        todo.append((p, out.replace("\n", nl).encode("utf-8")))
    tp = Path(TEST_PATH)
    if tp.exists():
        if tp.read_text(encoding="utf-8").replace("\r\n", "\n") != TEST:
            problems.append("%s exists with other content" % TEST_PATH)
        else:
            print("skip %s (already present)" % TEST_PATH)
    else:
        todo.append((tp, TEST.encode("utf-8")))
    if problems:
        for x in problems:
            print("REFUSE: " + x)
        print("Nothing written."); return 1
    if a.check:
        print("CHECK OK: %d file(s) to write: %s. Nothing written." % (len(todo), ", ".join(str(p) for p, _ in todo)))
        return 0
    for p, data in todo:
        if p.exists():
            shutil.copy2(p, p.with_name(p.name + ".bak_w8_" + stamp))
        t = p.with_name(p.name + ".tmp_w8"); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % p)
    print("Next: npm run typecheck ; npx vitest run src/__tests__/load-w8.test.ts ; npm run build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
