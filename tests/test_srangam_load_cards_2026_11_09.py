# -*- coding: ascii -*-
"""LOAD_CARDS_2026_11_09: the Srangam patch reads the article cards from the view (C25) and falls back to the old read
while the view is not there; both reads are bounded, as Srangam's own ratchet (QUERY_CEILING_2026_09_10) counts a
bound; the patch writes all or nothing, keeps CRLF and runs once. C25 makes a view with the invoker's rights and grants
it to the site's visitors, and changes no table. Made-up checkouts in temp folders, built from the patch's anchors."""
import importlib.util, re, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_srangam_load_cards_2026_11_09.py"
C25 = REPO / "docs" / "cloud" / "C25_article_cards_2026-11-09.sql"
MARK = "LOAD_CARDS_2026_11_09"
F = "src/hooks/useArticles.ts"
FROM_CALL = re.compile(r"\.from\(\s*['\"]([A-Za-z0-9_]+)['\"]")
BOUNDED = re.compile(r"\.limit\(|\.range\(|\.single\(\)|\.maybeSingle\(\)|head:\s*true")


def chains(src: str) -> list:
    """Srangam's src/__tests__/query-bounds.test.ts chainsIn, in Python: (table, bounded) to the statement's end."""
    out = []
    for m in FROM_CALL.finditer(src):
        end = src.find(";", m.start())
        chain = src[m.start(): end if end != -1 else m.start() + 400]
        out.append((m.group(1), bool(BOUNDED.search(chain))))
    return out


def patcher():
    spec = importlib.util.spec_from_file_location("pat_load_cards", str(PAT))
    mod = importlib.util.module_from_spec(spec)
    old = sys.argv
    try:
        sys.argv = ["x", "--check"]
        spec.loader.exec_module(mod)
    finally:
        sys.argv = old
    return mod


@unittest.skipUnless(PAT.exists(), "the patch is not here")
class ThePatch(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        (self.t / "src" / "hooks").mkdir(parents=True)
        self.mod = patcher()
        # a made-up file: the patch's anchors, in order, between other lines; CRLF as Srangam's file has it
        body = "// header\n" + "\n// between\n".join(old for _f, _n, old, _new in self.mod.E) + "\n// end\n"
        self.raw = body.replace("\n", "\r\n").encode("utf-8")
        (self.t / F).write_bytes(self.raw)

    def tearDown(self):
        self.td.cleanup()

    def run_pat(self, *a):
        return subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(self.t), capture_output=True, text=True)

    def test_applies_once_and_keeps_crlf(self):
        self.assertIn("CHECK OK: 1 file(s)", self.run_pat("--check").stdout)
        self.assertEqual((self.t / F).read_bytes(), self.raw, "--check writes nothing")
        r = self.run_pat()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = (self.t / F).read_bytes()
        self.assertNotIn(b"\n", out.replace(b"\r\n", b""), "CRLF kept")
        s = out.decode("utf-8").replace("\r\n", "\n")
        self.assertIn(MARK, s)
        self.assertIn(".from('srangam_article_cards')", s)
        self.assertIn("body_languages", s)
        self.assertIn("computeBodyLanguages(article.content)", s, "the old read's languages, as the fallback")
        self.assertEqual([c for c in chains(s) if not c[1]], [], "no unbounded read (the ratchet's rule)")
        self.assertEqual(sorted(t for t, _b in chains(s)), ["srangam_article_cards", "srangam_articles"])
        self.assertTrue(list(self.t.glob("src/hooks/useArticles.ts.bak_loadcards_*")), "a backup")
        self.assertIn("Nothing to do", self.run_pat().stdout)

    def test_refuses_a_file_changed_since(self):
        _f, _n, first, _new = self.mod.E[0]
        changed = self.raw.replace(first.replace("\n", "\r\n").encode("utf-8")[:40], b"// changed")
        (self.t / F).write_bytes(changed)
        r = self.run_pat()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSE", r.stdout)
        self.assertEqual((self.t / F).read_bytes(), changed, "nothing written")


@unittest.skipUnless(C25.exists(), "C25 is not here")
class TheView(unittest.TestCase):
    def test_a_view_and_its_grant_only(self):
        q = C25.read_text(encoding="utf-8")
        self.assertTrue(q.isascii())
        self.assertIn(MARK, q)
        body = "\n".join(ln for ln in q.splitlines() if not ln.lstrip().startswith("--"))
        self.assertIn("CREATE OR REPLACE VIEW public.srangam_article_cards", body)
        self.assertIn("WITH (security_invoker = true)", body)
        self.assertIn("GRANT SELECT ON public.srangam_article_cards TO anon, authenticated;", body)
        self.assertIsNone(re.search(r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER\s+TABLE)\b", body, re.I))
        self.assertNotIn(" content,", body.split("FROM public.srangam_articles a;")[0].split("AS\nSELECT")[1],
                         "the view does not carry the bodies")
        for col in ("id", "slug", "slug_alias", "title", "dek", "theme", "tags", "read_time_minutes", "author",
                    "published_date", "created_at", "status"):
            self.assertIn("a.%s" % col, body)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            if not f.exists():
                self.skipTest("%s is not here" % f.name)
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)


if __name__ == "__main__":
    unittest.main()
