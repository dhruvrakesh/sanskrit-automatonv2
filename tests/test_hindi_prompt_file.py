# -*- coding: ascii -*-
"""HI_PROMPT_FILE_2026_10_03. python -m unittest tests.test_hindi_prompt_file -v
Subprocesses import infer_mt with a temp prompt file; translate_passages runs on
a throwaway DB with translate_batch FAKED. No API, no network, no context.db."""
import json, os, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LAC = "[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]"
PROMPT = ("\u0906\u092a \u090f\u0915 \u0938\u0902\u0938\u094d\u0915\u0943\u0924 \u0935\u093f\u0926\u094d\u0935\u093e\u0928\u094d "
          "\u0939\u0948\u0902\u0964 ") * 30


def run_py(code, env_extra):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", **env_extra)
    return subprocess.run([sys.executable, "-c", code], cwd=str(REPO), env=env, capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


PROBE = "import sys; sys.path.insert(0,'scripts'); import infer_mt as m; print('VER=' + m.PROMPT_VERSIONS['hi'])"


def ver(res):
    lines = [l for l in res.stdout.splitlines() if l.startswith("VER=")]
    return lines[-1][4:] if lines else "(no version: %s)" % (res.stdout + res.stderr)[-300:]


class HindiPromptFile(unittest.TestCase):
    def test_marker(self):
        for f in ("infer_mt.py", "translate_passages.py"):
            self.assertTrue("HI_PROMPT_FILE_2026_10_03" in (REPO / "scripts" / f).read_text(encoding="utf-8"),
                            "%s is not patched" % f)

    def test_file_sets_content_hashed_version_crlf_invariant(self):
        with tempfile.TemporaryDirectory() as t:
            lf = Path(t) / "lf.txt"; lf.write_bytes(PROMPT.replace("\u0964 ", "\u0964\n").encode("utf-8"))
            crlf = Path(t) / "crlf.txt"; crlf.write_bytes(PROMPT.replace("\u0964 ", "\u0964\r\n").encode("utf-8"))
            a = run_py(PROBE, {"SA_HI_PROMPT_FILE": str(lf)}); b = run_py(PROBE, {"SA_HI_PROMPT_FILE": str(crlf)})
            self.assertEqual(a.returncode, 0, a.stderr[-800:])
            va, vb = ver(a), ver(b)
            self.assertTrue(va.startswith("hi-file-")); self.assertEqual(va, vb)
            none = run_py(PROBE, {"SA_HI_PROMPT_FILE": str(Path(t) / "absent.txt")})
            self.assertEqual(ver(none), "hi-v3-2026-09-27", "no file: built-in version unchanged")
            short = Path(t) / "short.txt"; short.write_text("too short", encoding="utf-8")
            self.assertEqual(ver(run_py(PROBE, {"SA_HI_PROMPT_FILE": str(short)})), "hi-v3-2026-09-27")

    def test_only_lacuna_and_noref_end_to_end(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t); db = t / "c.db"
            code = r'''
import sys, json, sqlite3
sys.path.insert(0, "scripts")
from db_utils import ensure_schema
db = sys.argv[1]
con = sqlite3.connect(db); ensure_schema(con)
con.execute("INSERT INTO docs(id, code) VALUES(1, 'T')")
SA = "\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0915\u0941\u0930\u0941\u0915\u094d\u0937\u0947\u0924\u094d\u0930\u0947 \u0938\u092e\u0935\u0947\u0924\u093e \u092f\u0941\u092f\u0941\u0924\u094d\u0938\u0935\u0903 \u0964 \u092e\u093e\u092e\u0915\u093e\u0903 \u092a\u093e\u0923\u094d\u0921\u0935\u093e\u0936\u094d\u091a\u0948\u0935 \u0965"
for i in (1, 2):
    con.execute("INSERT INTO passages(id, doc_id, page_no, idx, text, translation, translation_qa, quality_score, text_type) "
                "VALUES(?,1,1,?,?,?,0.9,0.9,'mula')", (i, i, SA, "On the field of dharma. //"))
con.execute("INSERT INTO translations_l10n(passage_id, lang, translation, mt_prompt_version) VALUES(1,'hi',?, 'old')",
            ("\u0927\u0930\u094d\u092e " + "[\u0905\u0938\u094d\u092a\u0937\u094d\u091f]",))
con.execute("INSERT INTO translations_l10n(passage_id, lang, translation, mt_prompt_version) VALUES(2,'hi','\u0938\u093e\u092b', 'old')")
con.commit(); con.close()
import translate_passages as tp
seen = []
def fake(con, texts, **kw):
    seen.append(kw.get("reference_list"))
    return ["\u0927\u0930\u094d\u092e\u0915\u094d\u0937\u0947\u0924\u094d\u0930 \u092e\u0947\u0902 \u090f\u0915\u0924\u094d\u0930 \u0939\u0941\u090f //" for _ in texts]
tp.translate_batch = fake
sys.argv = ["x", "--db", db, "--doc", "T", "--lang", "hi", "--only-lacuna", "--reference", "none",
            "--engine", "echo", "--sleep", "0", "--progress", sys.argv[2], "--config", sys.argv[3], "--min-quality", "0"]
tp.main()
con = sqlite3.connect(db)
rows = con.execute("SELECT passage_id, translation, mt_prompt_version FROM translations_l10n ORDER BY passage_id").fetchall()
hist = con.execute("SELECT passage_id, reason FROM translation_history").fetchall()
print(json.dumps({"rows": rows, "hist": hist, "refs": seen}, ensure_ascii=True))
'''
            r = subprocess.run([sys.executable, "-c", code, str(db), str(t / "p.json"), str(t / "c.json")],
                               cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", timeout=120,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8", SA_HI_PROMPT_FILE=str(t / "absent.txt")))
            self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-1500:])
            out = json.loads(r.stdout.strip().splitlines()[-1])
            rows = {p: (tr, v) for p, tr, v in out["rows"]}
            self.assertNotIn(LAC, rows[1][0], "the lacuna row was re-translated")
            self.assertTrue(rows[1][1].endswith("+noref"), rows[1][1])
            self.assertEqual(rows[2], ("\u0938\u093e\u092b", "old"), "a row without a lacuna is untouched")
            self.assertEqual(out["hist"], [[1, "retranslate-overwrite"]])
            self.assertEqual(out["refs"], [[None]], "no English reference was shown to the model")


if __name__ == "__main__":
    unittest.main()
