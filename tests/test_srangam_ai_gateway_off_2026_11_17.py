# -*- coding: ascii -*-
"""AI_GATEWAY_OFF_2026_11_17 (I1): the Srangam kit that moves detect-duplicate-articles and suggest-tag-categories off
the Lovable AI Gateway to the project's own keys (_shared/ai-provider.ts: Gemini first, OpenAI second). The payload
names neither the gateway nor its key and calls ai-provider with telemetry; the patch writes only over the version main
had, keeps CRLF, backs up, appends Phase AS once, refuses a changed file and runs once. Made-up checkouts in temp
folders; nothing is called."""
import hashlib, importlib.util, io, os, re, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAT = REPO / "scripts" / "patch_srangam_ai_gateway_off_2026_11_17.py"
KIT = REPO / "docs" / "srangam" / "AI_GATEWAY_OFF_2026-11-17"
MARK = "AI_GATEWAY_OFF_2026_11_17"
DUP = "supabase/functions/detect-duplicate-articles/index.ts"
TAGS = "supabase/functions/suggest-tag-categories/index.ts"
GATEWAY = re.compile(r"ai\.gateway\.lovable\.dev|LOVABLE_API_KEY")


def patcher():
    spec = importlib.util.spec_from_file_location("pat_aigwoff", str(PAT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ThePayload(unittest.TestCase):
    def test_no_gateway_and_the_provider_with_telemetry(self):
        for rel, purpose in ((DUP, "duplicate_check"), (TAGS, "tag_categories")):
            src = (KIT / rel).read_text(encoding="utf-8")
            self.assertIsNone(GATEWAY.search(src), rel)
            self.assertIn(MARK, src)
            self.assertIn("from '../_shared/ai-provider.ts'", src)
            self.assertIn("aiExtractCitations(", src)
            self.assertIn("function_name: '%s'" % rel.split("/")[2], src)
            self.assertIn("purpose: '%s'" % purpose, src)
            self.assertIn("GEMINI_API_KEY", src); self.assertIn("OPENAI_API_KEY", src)
            self.assertIn("requireAdmin(req)", src, "the admin gate stays")
        tags = (KIT / TAGS).read_text(encoding="utf-8")
        for kept in ("fetchCategoryExamples", "suggestions", "examplesUsed", "processingTimeMs", "status: 429"):
            self.assertIn(kept, tags, kept)
        dup = (KIT / DUP).read_text(encoding="utf-8")
        for kept in ("similarity_score", "is_duplicate", "'AI not available'", "calculateContentHash"):
            self.assertIn(kept, dup, kept)

    def test_the_vitest_and_the_audit(self):
        t = (KIT / "src/__tests__/ai-gateway-off.test.ts").read_text(encoding="utf-8")
        self.assertIn(MARK, t)
        self.assertIn("ai\\.gateway\\.lovable\\.dev", t)
        self.assertIn("aiExtractCitations", t)
        a = (KIT / "_append/RELIABILITY_AUDIT.phaseAS.md").read_text(encoding="utf-8")
        self.assertTrue(a.startswith("## Phase AS - "))
        self.assertIn(MARK, a)
        self.assertIn("69. No edge function calls the Lovable AI Gateway", a)


@unittest.skipUnless(PAT.exists(), "the patch is not here")
class ThePatch(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.t = Path(self.td.name)
        self.mod = patcher()
        (self.t / "package.json").write_text("{}", encoding="ascii")
        sh = self.t / "supabase/functions/_shared"; sh.mkdir(parents=True)
        (sh / "ai-provider.ts").write_text("export async function aiExtractCitations(opts) {}\n", encoding="ascii")
        self.fake = {}
        for rel in (DUP, TAGS):
            p = self.t / rel; p.parent.mkdir(parents=True)
            body = ("// %s as main had it\nconst k = Deno.env.get('LOVABLE_API_KEY');\n" % rel).replace("\n", "\r\n")
            p.write_bytes(body.encode("ascii"))
            self.fake[rel] = body.encode("ascii")
        (self.t / "docs").mkdir()
        (self.t / "docs/RELIABILITY_AUDIT.md").write_bytes(b"# Audit\n\n## Phase AR - x (B2_SITE_2026_10_28)\n")
        self.mod.REPLACE = {rel: hashlib.md5(self.fake[rel].replace(b"\r\n", b"\n")).hexdigest() for rel in self.fake}

    def tearDown(self):
        self.td.cleanup()

    def run_main(self, *a):
        old_cwd, old_argv = os.getcwd(), sys.argv
        buf = io.StringIO()
        try:
            os.chdir(str(self.t)); sys.argv = ["x"] + list(a)
            with redirect_stdout(buf):
                rc = self.mod.main()
        finally:
            os.chdir(old_cwd); sys.argv = old_argv
        return rc, buf.getvalue()

    def test_applies_once_keeps_crlf_and_backs_up(self):
        rc, out = self.run_main("--check")
        self.assertEqual(rc, 0, out); self.assertIn("CHECK OK: 4 file(s)", out)
        self.assertEqual((self.t / DUP).read_bytes(), self.fake[DUP], "--check writes nothing")
        rc, out = self.run_main()
        self.assertEqual(rc, 0, out)
        for rel in (DUP, TAGS):
            b = (self.t / rel).read_bytes()
            self.assertNotIn(b"\n", b.replace(b"\r\n", b""), "CRLF kept: " + rel)
            self.assertIsNone(GATEWAY.search(b.decode("utf-8")), rel)
            self.assertTrue(list((self.t / rel).parent.glob("index.ts.bak_aigwoff_*")), "a backup")
        self.assertTrue((self.t / "src/__tests__/ai-gateway-off.test.ts").exists())
        audit = (self.t / "docs/RELIABILITY_AUDIT.md").read_text(encoding="utf-8")
        self.assertEqual(audit.count("## Phase AS - "), 1)
        rc, out = self.run_main()
        self.assertEqual(rc, 0); self.assertIn("Nothing to do", out)
        self.assertEqual((self.t / "docs/RELIABILITY_AUDIT.md").read_text(encoding="utf-8"), audit, "once")

    def test_refuses_a_file_changed_since(self):
        changed = self.fake[TAGS] + b"// changed\r\n"
        (self.t / TAGS).write_bytes(changed)
        rc, out = self.run_main()
        self.assertEqual(rc, 1); self.assertIn("REFUSE", out)
        self.assertEqual((self.t / TAGS).read_bytes(), changed)
        self.assertEqual((self.t / DUP).read_bytes(), self.fake[DUP], "all or nothing")
        self.assertFalse((self.t / "src/__tests__/ai-gateway-off.test.ts").exists())

    def test_refuses_without_the_provider_or_outside_the_repo(self):
        (self.t / "supabase/functions/_shared/ai-provider.ts").write_text("// none\n", encoding="ascii")
        rc, out = self.run_main()
        self.assertEqual(rc, 1); self.assertIn("aiExtractCitations", out)
        (self.t / "package.json").unlink()
        rc, out = self.run_main()
        self.assertEqual(rc, 2); self.assertIn("FAIL: run this from the Srangam repo root", out)


class TheFiles(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            b = f.read_bytes()
            self.assertTrue(all(x < 128 for x in b), f.name)
            self.assertIn(MARK.encode(), b, f.name)
        self.assertEqual(sorted(patcher().REPLACE), [DUP, TAGS])


if __name__ == "__main__":
    unittest.main()
