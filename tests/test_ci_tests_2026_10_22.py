# -*- coding: ascii -*-
"""CI_TESTS_2026_10_22: .github/workflows/tests.yml runs the suite as the PC does (scripts/run_tests.ps1, one module at
a time) on a clean checkout, on Ubuntu for every push to main and pull request and on Windows only by hand; it reads
the repository and nothing more, is given no secret, and deploys, pushes and publishes nothing. Read as text: no YAML
library is needed."""
import re, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WF = REPO / ".github" / "workflows" / "tests.yml"
MARK = "CI_TESTS_2026_10_22"


@unittest.skipUnless(WF.exists(), "the workflow is not here")
class TheWorkflow(unittest.TestCase):
    def setUp(self):
        self.b = WF.read_bytes()
        self.s = self.b.decode("ascii")
        self.code = "\n".join(l for l in self.s.splitlines() if not l.lstrip().startswith("#"))

    def test_ascii_mark_and_no_tabs(self):
        self.assertTrue(all(x < 128 for x in self.b))
        self.assertIn(MARK, self.s)
        self.assertNotIn("\t", self.s, "YAML indents with spaces")

    def test_reads_only_and_holds_no_secret(self):
        self.assertRegex(self.code, r"(?m)^permissions:\n  contents: read$")
        self.assertNotIn("secrets.", self.code)
        self.assertNotIn("write", re.search(r"(?ms)^permissions:\n(.*?)^\S", self.code + "\nx").group(1))
        for word in ("deploy", "git push", "gh release", "upload-artifact", "publish", "GEMINI", "ANTHROPIC",
                     "CORPUS_SYNC", "RESEND", "context.db"):
            self.assertNotIn(word, self.code, word)

    def test_runs_the_suite_as_the_pc_does(self):
        runs = re.findall(r"run: (.*)", self.code)
        self.assertEqual(runs.count('./scripts/run_tests.ps1 -Repo "${{ github.workspace }}" -Python python -Show'), 2)
        self.assertEqual(runs.count("python -m pip install -r requirements.txt"), 2)
        self.assertEqual(self.code.count('python-version: "3.13"'), 2, "as the PC")
        self.assertTrue((REPO / "scripts" / "run_tests.ps1").exists())
        self.assertTrue((REPO / "requirements.txt").exists())

    def test_when_it_runs(self):
        on = re.search(r"(?ms)^on:\n(.*?)^\S", self.code).group(1)
        self.assertIn("push:\n    branches: [main]", on)
        self.assertIn("pull_request:", on)
        self.assertIn("workflow_dispatch:", on)
        self.assertNotIn("schedule", on, "no standing schedule")
        win = self.code.split("  windows:", 1)[1]
        self.assertIn("if: ${{ github.event_name == 'workflow_dispatch' && inputs.windows }}", win, "Windows by hand only")
        self.assertIn("cancel-in-progress: true", self.code)
        self.assertEqual(len(re.findall(r"timeout-minutes: \d+", self.code)), 2)


if __name__ == "__main__":
    unittest.main()
