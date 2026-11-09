#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_srangam_load_cards_2026_11_09.py  (2026-11-09)  LOAD_CARDS_2026_11_09

For the SRANGAM repo (run from D:\\srangam-42267, on main). The home page and /articles read every published
article with select('*'). Measured on 9 Nov 2026 (a cold load of https://srangam.nartiang.org/ in Playwright, from
the cloud): the page transferred 3,091 KB, 2,329 KB of it this one query; `content` was 4.64 MB of its 4.73 MB
uncompressed, read only to learn which languages have a body.

src/hooks/useArticles.ts now reads the cards from the view public.srangam_article_cards (docs\\cloud\\
C25_article_cards_2026-11-09.sql in the automaton repo: the cards' columns and body_languages, computed in the
database by the same rule), and falls back to the old read while the view is not there. So the order of pasting
C25 and publishing does not matter. Both reads are bounded at 1000, PostgREST's own ceiling made explicit
(QUERY_CEILING_2026_09_10: the count of unbounded reads falls by one).

Anchored, all-or-nothing, marker-idempotent; line endings kept; .bak_loadcards_<date> copies.

  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_load_cards_2026_11_09.py" --check
  python "D:\\Sanksrit Automatons\\sanskrit-automatonv2\\scripts\\patch_srangam_load_cards_2026_11_09.py"
Then: npm run typecheck ; npx vitest run ; npm run build
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'LOAD_CARDS_2026_11_09'
TAG = 'loadcards'
FILES = ['src/hooks/useArticles.ts']
NEEDS = {}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('src/hooks/useArticles.ts', 1, "const FETCH_TIMEOUT_MS = 12_000;\n\nconst computeBodyLanguages = (content: unknown): SupportedLanguage[] => {\n  if (!content || typeof content !== 'object') return ['en'];",
     "const FETCH_TIMEOUT_MS = 12_000;\n\n/**\n * LOAD_CARDS_2026_11_09 - the list pages read the cards, not the bodies.\n * Measured on 9 Nov 2026 (Playwright, a cold load of https://srangam.nartiang.org/): the home page transferred\n * 3,091 KB, of which 2,329 KB was this one query, `select('*')` over the 50 published articles - 4.64 MB of their\n * 4.73 MB uncompressed was `content`, read only to learn which languages have a body. The view\n * public.srangam_article_cards (docs/cloud/C25_article_cards_2026-11-09.sql in the automaton repository) gives the\n * card's columns and `body_languages`, computed in the database with the same rule as computeBodyLanguages. Until\n * that view exists the old read stays the fallback, so the order of deploying the two does not matter.\n */\nconst CARD_COLUMNS =\n  'id, slug, slug_alias, title, dek, theme, tags, read_time_minutes, author, published_date, created_at, body_languages';\n\nconst computeBodyLanguages = (content: unknown): SupportedLanguage[] => {\n  if (!content || typeof content !== 'object') return ['en'];")

edit('src/hooks/useArticles.ts', 2, "\n      const fetchPromise = (async () => {\n        const { data, error } = await supabase\n          .from('srangam_articles')\n          .select('*')\n          .eq('status', 'published')\n          // Phase AB.3 \u2014 deterministic ordering so same-day rows don't flip.\n          .order('published_date', { ascending: false })\n          .order('created_at', { ascending: false })\n          .abortSignal(signal);\n\n        if (error) {\n          console.error('Error fetching database articles:', error);\n          throw error;\n        }\n\n        return data.map((article): DisplayArticle => {\n          const title = typeof article.title === 'object' && article.title !== null\n            ? article.title as { [key: string]: string }",
     "\n      const fetchPromise = (async () => {\n        // LOAD_CARDS_2026_11_09: the cards first (the view); the bounds are PostgREST's own ceiling, made explicit.\n        const cards = await (supabase as any)\n          .from('srangam_article_cards')\n          .select(CARD_COLUMNS)\n          .eq('status', 'published')\n          // Phase AB.3 \u2014 deterministic ordering so same-day rows don't flip.\n          .order('published_date', { ascending: false })\n          .order('created_at', { ascending: false })\n          .limit(1000)\n          .abortSignal(signal);\n        let data: any[] | null = cards.data;\n        let error: any = cards.error;\n\n        if (error && (error as any)?.name !== 'AbortError') {\n          // The view is not there yet (C25 not pasted): the old read, as before.\n          const full = await supabase\n            .from('srangam_articles')\n            .select('*')\n            .eq('status', 'published')\n            .order('published_date', { ascending: false })\n            .order('created_at', { ascending: false })\n            .limit(1000)\n            .abortSignal(signal);\n          data = full.data;\n          error = full.error;\n        }\n\n        if (error || !data) {\n          console.error('Error fetching database articles:', error);\n          throw error;\n        }\n\n        return data.map((article: any): DisplayArticle => {\n          const title = typeof article.title === 'object' && article.title !== null\n            ? article.title as { [key: string]: string }")

edit('src/hooks/useArticles.ts', 3, "            date: article.published_date,\n            source: 'database' as const,\n            bodyLanguages: computeBodyLanguages(article.content),\n            slugAlias: slugAlias || undefined,\n            rawSlug,",
     "            date: article.published_date,\n            source: 'database' as const,\n            bodyLanguages: Array.isArray(article.body_languages) && article.body_languages.length > 0\n              ? (article.body_languages as SupportedLanguage[])\n              : computeBodyLanguages(article.content),\n            slugAlias: slugAlias || undefined,\n            rawSlug,")


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

