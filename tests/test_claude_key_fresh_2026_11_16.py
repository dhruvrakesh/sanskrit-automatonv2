# -*- coding: ascii -*-
"""CLAUDE_KEY_FRESH_2026_11_16. From 14 to 16 Nov the dashboard (started on 13 Nov) gave its jobs the Claude key that was
refused ("401 invalid x-api-key"): python-dotenv does not replace a key already in the environment. The 18 Sonnet jobs
of 15 Nov translated nothing and said "empty after a paid call" for each passage; nothing was billed. Now each Client
reads .env again and uses its key when it differs, and a refused key is said once, plainly. Fake keys and a stubbed
SDK only; no .env of this PC is read."""
import os, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import claude_engine as CE   # noqa: E402
import infer_mt as MT        # noqa: E402

MARK = "CLAUDE_KEY_FRESH_2026_11_16"
REFUSED = ("Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': "
           "'invalid x-api-key'}, 'request_id': 'req_test'}")


class Kw:
    """The SDK, as far as Client builds it: what it was given."""

    def __init__(self):
        self.given = None
        outer = self

        class Anthropic:
            def __init__(self, **kw):
                outer.given = kw
        self.Anthropic = Anthropic


class TheKey(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        self.env_key = CE.env_key

    def tearDown(self):
        CE.env_key = self.env_key
        os.environ.clear(); os.environ.update(self.keep)

    def test_env_key_reads_the_file_given(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".env"
            p.write_text("OTHER=1\nANTHROPIC_API_KEY=test-new-key\n", encoding="ascii")
            try:
                import dotenv  # noqa: F401
            except ImportError:
                self.skipTest("python-dotenv is not here")
            self.assertEqual(CE.env_key(p), "test-new-key")
            p.write_text("OTHER=1\n", encoding="ascii")
            self.assertIsNone(CE.env_key(p))
        os.environ["SA_NO_DOTENV"] = "1"
        self.assertIsNone(CE.env_key(), "the tests never read this PC's .env")

    def test_the_client_uses_the_key_in_env_file_when_it_differs(self):
        os.environ["ANTHROPIC_API_KEY"] = "test-old-key"
        CE.env_key = lambda path=None: "test-new-key"
        sdk = Kw()
        CE.Client(CE.MODEL if hasattr(CE, "MODEL") else "claude-sonnet-5-5", sdk=sdk)
        self.assertEqual(sdk.given.get("api_key"), "test-new-key")
        CE.env_key = lambda path=None: "test-old-key"
        sdk = Kw()
        CE.Client("claude-sonnet-5-5", sdk=sdk)
        self.assertNotIn("api_key", sdk.given, "the same key: the environment's, as before")
        CE.env_key = lambda path=None: None
        sdk = Kw()
        CE.Client("claude-sonnet-5-5", sdk=sdk)
        self.assertNotIn("api_key", sdk.given)
        del os.environ["ANTHROPIC_API_KEY"]
        self.assertRaises(RuntimeError, CE.Client, "claude-sonnet-5-5", sdk=Kw())
        CE.env_key = lambda path=None: "test-new-key"
        sdk = Kw()
        CE.Client("claude-sonnet-5-5", sdk=sdk)
        self.assertEqual(sdk.given.get("api_key"), "test-new-key", "the key in .env alone is enough")


class TheRefusal(unittest.TestCase):
    def setUp(self):
        self.keep = dict(os.environ)
        os.environ["ANTHROPIC_API_KEY"] = "test-old-key"
        del CE._SAID_REFUSED[:]

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.keep)

    def test_a_refused_key_is_said_once_and_raised(self):
        class Stream:
            def __enter__(self):
                raise RuntimeError(REFUSED)

            def __exit__(self, *a):
                return False

        class SDK:
            class Anthropic:
                def __init__(self, **kw):
                    self.messages = self

                def stream(self, **kw):
                    return Stream()
        c = CE.Client("claude-sonnet-5-5", sdk=SDK())
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            for _ in range(3):
                with self.assertRaises(RuntimeError):
                    c.create("s", "u", 100)
        self.assertEqual(buf.getvalue().count("[claude] the key was refused (401 invalid x-api-key)"), 1)
        self.assertIn("claude_engine.py --probe", buf.getvalue())
        self.assertTrue(CE.refused(RuntimeError(REFUSED)))
        self.assertFalse(CE.refused(RuntimeError("Connection reset")))
        self.assertTrue(issubclass(MT.ClaudeUnavailable, MT.QuotaExhausted), "as before")


PAT = REPO / "scripts" / "patch_claude_key_fresh_2026_11_16.py"
FILES = ("scripts/claude_engine.py",)


@unittest.skipUnless(PAT.exists(), "patch_claude_key_fresh_2026_11_16.py is not here")
class ThePatch(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(PAT.read_bytes().isascii())

    def test_replays_once(self):
        with tempfile.TemporaryDirectory() as tdir:
            t = Path(tdir)
            for rel in FILES:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_keyfresh_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True,
                                            text=True)
            r = run("--check")
            self.assertIn("CHECK OK: %d file(s)" % len(FILES), r.stdout, r.stdout + r.stderr)
            self.assertEqual(run().returncode, 0)
            for rel in FILES:
                self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)
            self.assertIn("Nothing to do", run().stdout)


class TheFile(unittest.TestCase):
    def test_ascii_and_mark(self):
        self.assertTrue(Path(__file__).read_bytes().isascii())
        self.assertIn(MARK.encode(), (SCRIPTS / "claude_engine.py").read_bytes())
        self.assertTrue((SCRIPTS / "claude_engine.py").read_bytes().isascii())


if __name__ == "__main__":
    unittest.main()
