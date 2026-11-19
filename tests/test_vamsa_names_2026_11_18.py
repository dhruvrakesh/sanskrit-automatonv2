# -*- coding: ascii -*-
"""VAMSA_NAMES_2026_11_18 (P1). The register's second names healed: a second name only where the verse says it of him
(not his minister, his mother, his wives' father, a land); a name typed in plain letters meets it in IAST, the exact
name before the near ones; the father's entry only where most works agree. The patch replays on the copies from
before it, once. Free and read-only. Temp folders only."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vamsa_align as VA        # noqa: E402
import vamsa_register as R      # noqa: E402

MARK = "VAMSA_NAMES_2026_11_18"
PAT = SCRIPTS / "patch_vamsa_names_2026_11_18.py"


def st(a, rel, b, ch=1, ref=None, check="verified", words="tasya putra\u1e25"):
    return {"ref": ref or "R %d" % ch, "a": a, "rel": rel, "b": b, "words": words, "doubt": False, "check": check,
            "chapter": ch}

class TheSecondNames(unittest.TestCase):
    def test_said_of_him(self):
        ok = [st("Vikuk\u1e63i", "son_of", "Ik\u1e63v\u0101ku"),
              st("Vikuk\u1e63i", "other", "\u015aa\u015b\u0101da", words="\u015ba\u015b\u0101dasa\u1e43j\u00f1\u0101m av\u0101pa")]
        self.assertEqual([x[1:3] for x in VA.aliases_said(ok)], [("Vikuk\u1e63i", "\u015aa\u015b\u0101da")])

    def test_not_his_minister_mother_or_land(self):
        bad = [st("Ripu\u00f1jaya", "son_of", "Sunetra"),
               st("Ripu\u00f1jaya", "other", "Mu\u1e47ika", words="tasy\u0101m\u0101tyo muniko n\u0101ma bhavi\u1e63yati"),
               st("\u015ar\u0101ddhadeva", "son_of", "Vivasvat"),
               st("\u015ar\u0101ddhadeva", "other", "Sa\u1e43j\u00f1\u0101", words="sa\u1e43j\u00f1\u0101y\u0101m\u0101sa"),
               st("M\u0101ndh\u0101t\u1e5b", "son_of", "Yuvan\u0101\u015bva"),
               st("Saubhari", "other", "M\u0101ndh\u0101t\u1e5b", words="m\u0101ndh\u0101t\u1e5bduhit\u1e5bsa\u1e43bandh\u0101d \u0101khy\u0101tam"),
               st("Kuru", "son_of", "Sa\u1e43vara\u1e47a"),
               st("Kuru", "other", "Kuruk\u1e63etra", words="tasya n\u0101mn\u0101bhivikhy\u0101ta\u1e43 p\u1e5bthivy\u0101\u1e43 kuruj\u0101\u1e45galam")]
        self.assertEqual(VA.aliases_said(bad), [])


class TheLookup(unittest.TestCase):
    def test_plain_letters(self):
        for typed, iast in (("Bhishma", "Bh\u012b\u1e63ma"), ("Krishna", "K\u1e5b\u1e63\u1e47a"), ("Parikshit", "Par\u012bk\u1e63it"),
                            ("Harishchandra", "Hari\u015bcandra"), ("Shantanu", "\u015aa\u1e43tanu"), ("Yudhishthira", "Yudhi\u1e63\u1e6dhira")):
            self.assertEqual(R.qkey(typed), R.qkey(iast), typed)
        self.assertNotEqual(R.qkey("Devavrata"), R.qkey("Devar\u0101ta"))

    def test_exact_before_near(self):
        reg = {"entries": [{"names": ["Devavrata"]}, {"names": ["Devar\u0101ta"]}]}
        self.assertEqual(R.show(reg, "Devavrata"), [reg["entries"][0]])
        self.assertIn(reg["entries"][0], R.show(reg, "Devavratta"), "near when none is exact")


def make(t):
    out = Path(t) / "data" / "vamsa_read"
    lines = {"vip4": ["Jahnu", "Suratha", "Vid\u016bratha", "S\u0101rvabhauma"],
             "hv": ["Jahnu", "Suratha", "Vid\u016bratha"],
             "matsya": ["Jahnu", "Suratha", "Vi\u1e0d\u016bratha", "S\u0101rvabhauma"]}
    for w, ln in lines.items():
        (out / w).mkdir(parents=True)
        sts, up = [st("Kuru", "son_of", "Sa\u1e43vara\u1e47a", ref="%s 0" % w)], "Kuru"
        for i, n in enumerate(ln):
            sts.append(st(n, "son_of", up, ref="%s %d" % (w, i + 1)))
            up = n
        (out / w / "01_1.json").write_text(json.dumps({"chapter": 1, "statements": sts}, ensure_ascii=False),
                                           encoding="utf-8")
    return out


class TheFather(unittest.TestCase):
    def test_only_where_most_works_agree(self):
        sts = {"hv": [st("Amba", "son_of", "Naba", ch=9, ref="H 9"), st("Naba", "son_of", "Manu", ch=9, ref="H 8"),
                      st("Sindhu", "son_of", "Amba", ch=10, ref="H 10")],
               "matsya": [st("Amba", "son_of", "Naba", ch=12, ref="M 1"), st("Naba", "son_of", "Bhagi", ch=12, ref="M 0"),
                          st("Sindhu", "son_of", "Amba", ch=12, ref="M 2")]}
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "data" / "vamsa_read"
            for w, ss in sts.items():
                (out / w).mkdir(parents=True)
                by = {}
                for s in ss:
                    by.setdefault(s["chapter"], []).append(s)
                for ch, x in by.items():
                    (out / w / ("%02d_1.json" % ch)).write_text(json.dumps({"chapter": ch, "statements": x}), encoding="utf-8")
            reg = R.build(out, ["hv", "matsya"], [])
        s = [e for e in reg["entries"] if e["name"] == "Sindhu"][0]
        self.assertEqual(sorted(s["works"]), ["hv", "matsya"])
        self.assertIsNone(s["father_entry"], "two works, two Ambas: the works part")
        self.assertEqual(len(s["father_entries"]), 2)


@unittest.skipUnless(PAT.exists(), "the patch is not here")


@unittest.skipUnless(PAT.exists(), "the patch is not here")
class ThePatch(unittest.TestCase):
    def test_ascii_and_marks(self):
        for f in (PAT, Path(__file__)):
            f.read_bytes().decode("ascii")
        for f in ("vamsa_align.py", "vamsa_register.py"):
            self.assertIn(MARK, (SCRIPTS / f).read_text(encoding="ascii"), f)

    def test_replays_once(self):
        files = ("scripts/vamsa_align.py", "scripts/vamsa_register.py")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for rel in files:
                p = REPO / rel
                bak = sorted(p.parent.glob(p.name + ".bak_vamsanames_*"))
                srcb = (bak[0] if bak else p).read_bytes()
                if MARK.encode() in srcb:
                    self.skipTest("only patched copies to replay against")
                (t / rel).parent.mkdir(parents=True, exist_ok=True)
                (t / rel).write_bytes(srcb)
            run = lambda *a: subprocess.run([sys.executable, str(PAT)] + list(a), cwd=str(t), capture_output=True, text=True)
            self.assertIn("CHECK OK: 2 file(s)", run("--check").stdout)
            r = run()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for rel in files:
                now = (REPO / rel).read_bytes()
                # VAMSA_WAYIN_2026_11_18: a later patch changes the file again; this one's replay is then compared no more
                if MARK.encode() in now and b"VAMSA_WAYIN_2026_11_18" not in now:
                    self.assertEqual((t / rel).read_bytes(), now, rel)
            self.assertIn("Nothing to do", run().stdout)


if __name__ == "__main__":
    unittest.main()
