#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
NAME_LINKS_FAST_2026_10_24: "Named together" on the site, filled in seconds.

The fault (24 Oct, on the site): P4 and the fill of corpus.name_links ended "Server error". C20a's query joined each
passage's names to themselves. On a copy the size of the site (48,491 mentions) the planner guessed that the names
left after the 12-name rule were one row and joined them pair by pair (some 1.6 billion comparisons): it ran for more
than 5 minutes. The nightly job (C20c) would have run that query every night at 04:40 UTC.

The fix: the query takes each passage's names (2 to 12) as one sorted list and makes the pairs from it, with no
self-join; the passage check reads only the index corpus_passages_live. The same pairs (proven equal: 58,913, none
different) in 0.2 s. This patch writes it into C20a (the definition of record) and the preflight's P4, gives C20c's job
a 5-minute limit of its own, and updates test_name_links_pg's checks to match. For the site as it stands, paste the new
docs\\cloud\\C20d_name_links_fast_2026-10-24.sql (with C20d_checks), then C20b.

Run from the repo root:  python scripts\\patch_name_links_fast_2026_10_24.py --check   then without --check.
Backups: .bak_name_links_fast_ and the date beside each file. Test: tests\\test_name_links_fast_pg_2026_10_24.py.
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'NAME_LINKS_FAST_2026_10_24'
TAG = 'name_links_fast'
FILES = ['docs/cloud/C20a_name_links_view_2026-10-24.sql', 'docs/cloud/C20c_name_links_nightly_2026-10-24.sql', 'docs/cloud/C20_preflight_2026-10-24.sql', 'tests/test_name_links_pg_2026_10_24.py']
NEEDS = {'docs/cloud/C20a_name_links_view_2026-10-24.sql': 'NAME_LINKS_C20_SPLIT_2026_10_24', 'docs/cloud/C20c_name_links_nightly_2026-10-24.sql': 'NAME_LINKS_C20_SPLIT_2026_10_24', 'docs/cloud/C20_preflight_2026-10-24.sql': 'NAME_LINKS_C20_SPLIT_2026_10_24', 'tests/test_name_links_pg_2026_10_24.py': 'NAME_LINKS_C20_SPLIT_2026_10_24'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('docs/cloud/C20a_name_links_view_2026-10-24.sql', 1, '--   COMMIT;\n-- Tested 2026-10-24 on PostgreSQL 16 with pg_cron 1.6, as a role that is not a superuser.\n-- ============================================================\nBEGIN;',
     '--   COMMIT;\n-- Tested 2026-10-24 on PostgreSQL 16 with pg_cron 1.6, as a role that is not a superuser.\n-- NAME_LINKS_FAST_2026_10_24: the view\'s query takes each passage\'s names (2 to 12) as one sorted list and makes the\n-- pairs from it; the first version joined the names to themselves, and on a copy the size of the site (48,491\n-- mentions) the planner guessed one row and joined them pair by pair: it ran 5 minutes and more (on the site P4 and\n-- the fill ended "Server error"). The same pairs (proven equal), in 0.2 s on 48,000 mentions. A site that has the first version: C20d.\n-- ============================================================\nBEGIN;')

edit('docs/cloud/C20a_name_links_view_2026-10-24.sql', 2, "\nCREATE MATERIALIZED VIEW corpus.name_links AS\nWITH live AS (\n  SELECT m.doc_code, m.page_no, m.idx, m.canonical\n  FROM corpus.mentions m\n  JOIN corpus.docs d ON d.doc_code = m.doc_code AND d.retired_at IS NULL\n  JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx\n                        AND p.retired_at IS NULL\n  WHERE m.retired_at IS NULL AND m.doc_code NOT LIKE '%-RETIRED'\n), kept AS (\n  SELECT l.* FROM live l\n  JOIN (SELECT doc_code, page_no, idx FROM live GROUP BY doc_code, page_no, idx HAVING count(*) <= 12) s\n    ON s.doc_code = l.doc_code AND s.page_no = l.page_no AND s.idx = l.idx\n), pairs AS (\n  SELECT a.canonical AS name_a, b.canonical AS name_b, a.doc_code, a.page_no, a.idx\n  FROM kept a JOIN kept b ON b.doc_code = a.doc_code AND b.page_no = a.page_no AND b.idx = a.idx\n                         AND a.canonical < b.canonical\n)\nSELECT name_a, name_b, count(*)::integer AS passages, count(DISTINCT doc_code)::integer AS texts,",
     "\nCREATE MATERIALIZED VIEW corpus.name_links AS\nWITH named AS (\n  SELECT m.doc_code, m.page_no, m.idx, m.canonical\n  FROM corpus.mentions m\n  JOIN corpus.docs d ON d.doc_code = m.doc_code AND d.retired_at IS NULL\n  WHERE m.retired_at IS NULL AND m.doc_code NOT LIKE '%-RETIRED'\n), few AS (\n  SELECT n.doc_code, n.page_no, n.idx, array_agg(n.canonical ORDER BY n.canonical) AS names\n  FROM named n\n  GROUP BY n.doc_code, n.page_no, n.idx\n  HAVING count(*) BETWEEN 2 AND 12\n), live AS (\n  SELECT f.doc_code, f.page_no, f.idx, f.names FROM few f\n  WHERE EXISTS (SELECT 1 FROM corpus.passages p WHERE p.doc_code = f.doc_code AND p.page_no = f.page_no\n                AND p.idx = f.idx AND p.retired_at IS NULL)\n), pairs AS (\n  SELECT x.a AS name_a, y.b AS name_b, l.doc_code, l.page_no, l.idx\n  FROM live l\n  CROSS JOIN LATERAL unnest(l.names) WITH ORDINALITY AS x(a, i)\n  CROSS JOIN LATERAL unnest(l.names) WITH ORDINALITY AS y(b, j)\n  WHERE x.i < y.j\n)\nSELECT name_a, name_b, count(*)::integer AS passages, count(DISTINCT doc_code)::integer AS texts,")

edit('docs/cloud/C20c_name_links_nightly_2026-10-24.sql', 1, "-- it again changes nothing. Expect one row: a jobid.\n-- Undo: SELECT cron.unschedule('srangam-corpus-name-links');\n-- ============================================================\nSELECT cron.schedule('srangam-corpus-name-links', '40 4 * * *', 'SELECT corpus._refresh_name_links();') AS jobid;\n",
     "-- it again changes nothing. Expect one row: a jobid.\n-- Undo: SELECT cron.unschedule('srangam-corpus-name-links');\n-- NAME_LINKS_FAST_2026_10_24: the job stops itself after 5 minutes (the fill takes seconds), so a slow night never\n-- holds the database.\n-- ============================================================\nSELECT cron.schedule('srangam-corpus-name-links', '40 4 * * *', 'SET statement_timeout = ''5min''; SELECT corpus._refresh_name_links();') AS jobid;\n")

edit('docs/cloud/C20_preflight_2026-10-24.sql', 1, '\n\n-- P4 how long the fill takes on the site: the view\'s own query, counted, nothing kept. Read the last two lines\n--    (Planning Time, Execution Time). Under about 20 seconds: go on to C20a. Longer, or "Server error" here too:\n--    stop and send the CSV (the fill then needs to be made in parts).\nEXPLAIN (ANALYZE, SUMMARY) SELECT count(*) FROM (\nWITH live AS (\n  SELECT m.doc_code, m.page_no, m.idx, m.canonical\n  FROM corpus.mentions m\n  JOIN corpus.docs d ON d.doc_code = m.doc_code AND d.retired_at IS NULL\n  JOIN corpus.passages p ON p.doc_code = m.doc_code AND p.page_no = m.page_no AND p.idx = m.idx\n                        AND p.retired_at IS NULL\n  WHERE m.retired_at IS NULL AND m.doc_code NOT LIKE \'%-RETIRED\'\n), kept AS (\n  SELECT l.* FROM live l\n  JOIN (SELECT doc_code, page_no, idx FROM live GROUP BY doc_code, page_no, idx HAVING count(*) <= 12) s\n    ON s.doc_code = l.doc_code AND s.page_no = l.page_no AND s.idx = l.idx\n), pairs AS (\n  SELECT a.canonical AS name_a, b.canonical AS name_b, a.doc_code, a.page_no, a.idx\n  FROM kept a JOIN kept b ON b.doc_code = a.doc_code AND b.page_no = a.page_no AND b.idx = a.idx\n                         AND a.canonical < b.canonical\n)\nSELECT name_a, name_b, count(*)::integer AS passages, count(DISTINCT doc_code)::integer AS texts,',
     '\n\n-- P4 (NAME_LINKS_FAST_2026_10_24: the fast query; the first one ended "Server error" here on 24 Oct)\n--    how long the fill takes on the site: the view\'s own query, counted, nothing kept. Read the last two lines\n--    (Planning Time, Execution Time). Under about 20 seconds: go on to C20a. Longer, or "Server error" here too:\n--    stop and send the CSV (the fill then needs to be made in parts).\nEXPLAIN (ANALYZE, SUMMARY) SELECT count(*) FROM (\nWITH named AS (\n  SELECT m.doc_code, m.page_no, m.idx, m.canonical\n  FROM corpus.mentions m\n  JOIN corpus.docs d ON d.doc_code = m.doc_code AND d.retired_at IS NULL\n  WHERE m.retired_at IS NULL AND m.doc_code NOT LIKE \'%-RETIRED\'\n), few AS (\n  SELECT n.doc_code, n.page_no, n.idx, array_agg(n.canonical ORDER BY n.canonical) AS names\n  FROM named n\n  GROUP BY n.doc_code, n.page_no, n.idx\n  HAVING count(*) BETWEEN 2 AND 12\n), live AS (\n  SELECT f.doc_code, f.page_no, f.idx, f.names FROM few f\n  WHERE EXISTS (SELECT 1 FROM corpus.passages p WHERE p.doc_code = f.doc_code AND p.page_no = f.page_no\n                AND p.idx = f.idx AND p.retired_at IS NULL)\n), pairs AS (\n  SELECT x.a AS name_a, y.b AS name_b, l.doc_code, l.page_no, l.idx\n  FROM live l\n  CROSS JOIN LATERAL unnest(l.names) WITH ORDINALITY AS x(a, i)\n  CROSS JOIN LATERAL unnest(l.names) WITH ORDINALITY AS y(b, j)\n  WHERE x.i < y.j\n)\nSELECT name_a, name_b, count(*)::integer AS passages, count(DISTINCT doc_code)::integer AS texts,')

edit('tests/test_name_links_pg_2026_10_24.py', 1, '        rows = self.pg.execute("SELECT schedule, command, active FROM cron.job WHERE jobname = "\n                               "\'srangam-corpus-name-links\'").fetchall()\n        self.assertEqual(rows, [("40 4 * * *", "SELECT corpus._refresh_name_links();", True)])\n        self.pg.execute(rows[0][1])\n        self.assertTrue(self.filled(), "the job\'s own command fills the view")\n',
     '        rows = self.pg.execute("SELECT schedule, command, active FROM cron.job WHERE jobname = "\n                               "\'srangam-corpus-name-links\'").fetchall()\n        self.assertEqual(rows, [("40 4 * * *", "SET statement_timeout = \'5min\'; SELECT corpus._refresh_name_links();",\n                                 True)], "NAME_LINKS_FAST_2026_10_24: the job stops itself after 5 minutes")\n        self.pg.execute(rows[0][1])\n        self.pg.execute("RESET statement_timeout")\n        self.assertTrue(self.filled(), "the job\'s own command fills the view")\n')

edit('tests/test_name_links_pg_2026_10_24.py', 2, '        self.assertIn("WITH NO DATA;", a, "C20a fills nothing")\n        self.assertNotIn("cron.schedule", a.split("BEGIN;", 1)[1], "the job is C20c\'s")\n        self.assertIn("HAVING count(*) <= 12", a, "the desk\'s list rule")\n        self.assertIn("m.doc_code NOT LIKE \'%-RETIRED\'", a)\n        self.assertIn("PERFORM corpus._reader_gate();", a)',
     '        self.assertIn("WITH NO DATA;", a, "C20a fills nothing")\n        self.assertNotIn("cron.schedule", a.split("BEGIN;", 1)[1], "the job is C20c\'s")\n        self.assertTrue("HAVING count(*) <= 12" in a or "HAVING count(*) BETWEEN 2 AND 12" in a,\n                        "the desk\'s list rule")   # NAME_LINKS_FAST_2026_10_24: 2 to 12, the pairs from a list\n        self.assertIn("m.doc_code NOT LIKE \'%-RETIRED\'", a)\n        self.assertIn("PERFORM corpus._reader_gate();", a)')

edit('tests/test_name_links_pg_2026_10_24.py', 3, '            body = [ln for ln in statements(f).splitlines() if ln.strip() and not ln.startswith("--")]\n            self.assertEqual(len(body), 1, "%s is one statement" % f.name)\n        view = a[a.index("WITH live AS ("):a.index("GROUP BY name_a, name_b") + len("GROUP BY name_a, name_b")]\n        pre = statements(CLOUD / "C20_preflight_2026-10-24.sql")\n        self.assertIn(view, pre, "P4 times the view\'s own query")\n        old = CLOUD / "C20_name_links_2026-10-23.sql"\n        if old.exists():\n            self.assertIn(view, statements(old), "the same pairs as the 23 Oct C20 (and the site\'s own count)")\n\n',
     '            body = [ln for ln in statements(f).splitlines() if ln.strip() and not ln.startswith("--")]\n            self.assertEqual(len(body), 1, "%s is one statement" % f.name)\n        start = a.index("AS\\nWITH ") + 3\n        view = a[start:a.index("GROUP BY name_a, name_b", start) + len("GROUP BY name_a, name_b")]\n        pre = statements(CLOUD / "C20_preflight_2026-10-24.sql")\n        self.assertIn(view, pre, "P4 times the view\'s own query")\n        old = CLOUD / "C20_name_links_2026-10-23.sql"\n        if old.exists() and "NAME_LINKS_FAST_2026_10_24" not in a:\n            self.assertIn(view, statements(old), "the same pairs as the 23 Oct C20 (and the site\'s own count)")\n        # NAME_LINKS_FAST_2026_10_24: since then the query differs from 23 Oct\'s and its pairs are proven equal to\n        # them in tests/test_name_links_fast_pg_2026_10_24.py\n\n')


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
            print("FAIL: %s not found. Run from the repo root." % f); return 2
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        nl = nl_of(raw)
        src = raw.decode("utf-8").replace("\r\n", "\n")
        if NEEDS.get(f) and NEEDS[f] not in src:
            print("REFUSE: %s has no %s (apply it first). Nothing written." % (f, NEEDS[f])); return 1
        for ff, n, old, new in E:
            if ff != f:
                continue
            if src.count(old) != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, src.count(old))); return 1
            src = src.replace(old, new, 1)
        if MARK not in src:
            print("FAIL: %s: the edits did not bring %s. Nothing written." % (f, MARK)); return 2
        plan[f] = src.replace("\n", nl).encode("utf-8")
    with tempfile.TemporaryDirectory() as td:
        for f, data in plan.items():
            if f.endswith(".py"):
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), doraise=True)
                except py_compile.PyCompileError as ex:
                    print("FAIL: %s would not compile: %s. Nothing written." % (f, str(ex)[:300])); return 2
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        p = Path(f)
        shutil.copy2(p, p.with_name(p.name + ".bak_" + TAG + "_" + stamp))
        t = p.with_name(p.name + ".tmp_" + TAG); t.write_bytes(data); os.replace(t, p)
        print("wrote %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
