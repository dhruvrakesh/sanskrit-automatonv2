# -*- coding: ascii -*-
"""TESTS_HERMETIC_2026_11_11: the tests never read this PC's .env and never depend on the clock's day for the Claude
credit. tests/__init__.py sets SA_NO_DOTENV and SA_TEST_TODAY and takes the keys out; each loader of .env leaves it
alone under SA_NO_DOTENV; claude_engine.credit takes the tests' day; a process a test starts inherits all of it.
Temp folders only; nothing is called."""
import datetime, importlib, os, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))
MARK = "TESTS_HERMETIC_2026_11_11"
APPLIED = MARK.encode() in (SCRIPTS / "env_loader.py").read_bytes()


class ThePackage(unittest.TestCase):
    def test_the_environment_a_test_sees(self):
        import tests   # noqa: F401  (imported first by python -m unittest tests.<module>)
        self.assertEqual(os.environ.get("SA_NO_DOTENV"), "1")
        self.assertEqual(os.environ.get("SA_TEST_TODAY"), "2026-10-20")
        for k in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "CORPUS_SYNC_SECRET", "SA_CLAUDE_CREDIT_USD"):
            self.assertNotIn(k, os.environ, k)

    def test_ascii_and_marks(self):
        for p in (REPO / "tests" / "__init__.py", Path(__file__)):
            b = p.read_bytes()
            self.assertTrue(b.isascii(), p.name)
            self.assertIn(MARK.encode(), b, p.name)


@unittest.skipUnless(APPLIED, "TESTS_HERMETIC_2026_11_11 is not applied here")
class TheLoaders(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.keep)
        self.tmp.cleanup()

    def test_env_loader_leaves_dotenv_alone(self):
        import env_loader
        os.environ.pop("SA_HERMETIC_PROBE", None)
        src = (SCRIPTS / "env_loader.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("SA_NO_DOTENV") == "1"', src)
        env_loader.load_env()
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ, "the PC's .env was not read")

    def test_the_credit_takes_the_tests_day(self):
        import claude_engine as CE
        self.assertEqual(CE.test_today(), datetime.date(2026, 10, 20))
        con = __import__("sqlite3").connect(":memory:")
        c = CE.credit(con)
        self.assertEqual((c["cap"], c["since"], c["expired"]), (190.0, "2026-10-15", False))
        self.assertTrue(CE.credit(con, today=datetime.date(2026, 11, 11))["expired"], "an explicit day wins")
        os.environ["SA_TEST_TODAY"] = "not a day"
        self.assertIsNone(CE.test_today())
        os.environ.pop("SA_TEST_TODAY")
        self.assertIsNone(CE.test_today())
        con.close()

    def test_corpus_sync_reads_only_the_files_it_is_given(self):
        import corpus_sync
        self.assertEqual(corpus_sync.load_config()["secret"], "")
        env = self.t / "x.env"
        env.write_text("CORPUS_SYNC_SECRET=test-not-a-secret\n", encoding="utf-8")
        site = self.t / "site.env"
        site.write_text("VITE_SUPABASE_URL=https://example.invalid\n", encoding="utf-8")
        cfg = corpus_sync.load_config(env, site)
        self.assertEqual((cfg["secret"], cfg["url"]), ("test-not-a-secret", "https://example.invalid"))

    def test_a_process_a_test_starts_inherits_it(self):
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import env_loader, os; "
                            "env_loader.load_env(); print(os.environ.get('SA_NO_DOTENV'), 'ANTHROPIC_API_KEY' in os.environ)"
                            % str(SCRIPTS)], capture_output=True, text=True)
        self.assertEqual(r.stdout.split(), ["1", "False"], r.stdout + r.stderr)

    def test_the_other_loaders_carry_the_guard(self):
        for f in ("ingest_pdf.py", "run_inbox.py", "publish_api.py", "publish_srangam.py", "dashboard.py", "corpus_sync.py"):
            self.assertIn('SA_NO_DOTENV', (SCRIPTS / f).read_text(encoding="utf-8", errors="replace"), f)


if __name__ == "__main__":
    unittest.main()
