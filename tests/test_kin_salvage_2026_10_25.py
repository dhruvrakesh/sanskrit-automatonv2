# -*- coding: ascii -*-
"""KIN_SALVAGE_2026_10_25: kin_index.py keeps the relations given whole in a reply cut short, and does not ask again
(asked again it was cut again: three calls of one entry, about $0.13 a run); in a call of one entry every relation is
that entry's, whatever number the model gave it; an entry whose reading failed twice is not asked again unless
--retry-failed, and the plan says so; --salvage reads again, free, the failed replies already stored. The made-up
database and stub model of test_kin_index_2026_10_23, in a temp folder; never data/context.db, never the network."""
import contextlib, io, json, sqlite3, sys, tempfile, types, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_kin_index_2026_10_23 as K  # noqa: E402

APPLIED = b"KIN_SALVAGE_2026_10_25" in K.TOOL.read_bytes()
CUT = ('{"relations": [ {"entry": 150, "subject": "Abhimanyu", "relation": "son_of", "object": "Arjuna", '
       '"words": "son of Arjuna", "refs": ["I, 2, 401"]}, {"entry": 151, "subject": "Abhimanyu", "rela')


def answer(text):
    ns = types.SimpleNamespace
    return ns(text=text, candidates=[ns(finish_reason="MAX_TOKENS")],
              usage_metadata=ns(prompt_token_count=900, candidates_token_count=8000, thoughts_token_count=0,
                                total_token_count=8900))


def stub_with(calls, odd):
    """The test's stub, except for the entries whose head is in odd: {head: the reply's text}."""
    base = K.stub(calls)

    def call(system, prompt):
        for head, text in odd.items():
            if "] %s" % head in prompt:
                calls.append(prompt)
                return answer(text)
        return base(system, prompt)
    return call


@unittest.skipUnless(APPLIED, "KIN_SALVAGE_2026_10_25 is not applied here")
class TheSalvage(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = self.t = Path(self.td.name)
        (t / "data" / "shelf").mkdir(parents=True)
        self.db = t / "data" / "context.db"
        K.make_db(self.db)
        K.make_claims(t / "data" / "shelf" / "claims.db")
        self.m = K.load()
        self.calls = []

    def tearDown(self):
        self.td.cleanup()

    def run_main(self, *a, odd=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = self.m.main(["--root", str(self.t)] + list(a), caller=stub_with(self.calls, odd or {}))
        return rc, buf.getvalue()

    def kin(self, sql, args=()):
        con = sqlite3.connect(str(self.t / "data" / "shelf" / "kin.db"))
        try:
            return con.execute(sql, args).fetchall()
        finally:
            con.close()

    def test_the_parts_of_a_cut_reply(self):
        s = self.m.salvage(CUT)
        self.assertEqual([d["object"] for d in s], ["Arjuna"])
        self.assertIsNone(self.m.salvage('{"relations": [ {"entry": 1, "subj'))
        self.assertIsNone(self.m.salvage("I cannot answer that."))
        self.assertEqual(len(self.m.salvage('{"relations": [{"entry": 1}, {"entry": 2}]}')), 2)
        c = self.m.clean_relation(s[0], 1)
        self.assertEqual((c["entry"], c["relation"], c["object"]), (1, "son_of", "Arjuna"),
                         "one entry to the call: its number is the entry's, whatever the model wrote")
        self.assertIsNone(self.m.clean_relation(dict(s[0], entry=150), 2), "two entries: the number must be one of them")

    def test_a_cut_reply_is_kept_and_not_asked_again(self):
        rc, out = self.run_main("--yes", odd={"Abhimanyu": CUT})
        self.assertEqual(rc, 0, out)
        asks = [p for p in self.calls if "] Abhimanyu" in p]
        self.assertEqual(len(asks), 1, "one call, not three")
        st = self.kin("SELECT status, relations, note FROM kin_reads WHERE source = 'inm'")
        self.assertEqual(st[0][:2], ("salvaged", 1))
        self.assertIn("salvaged: 1 relation objects of a reply cut short", st[0][2])
        self.assertEqual(self.kin("SELECT subject, relation, object, words_check FROM kin WHERE source = 'inm'"),
                         [("Abhimanyu", "son_of", "Arjuna", "exact")])
        rc, out = self.run_main()
        self.assertIn("0 entries to read", out, "the entry is read")

    def test_twice_failed_is_given_up_until_asked(self):
        odd = {"Abhimanyu": "Sorry, I cannot read this entry."}
        for _ in range(2):
            rc, out = self.run_main("--yes", odd=odd)
            self.assertEqual(rc, 0, out)
        self.assertEqual(self.kin("SELECT count(*) FROM kin_reads WHERE status = 'failed'"), [(2,)])
        n = len(self.calls)
        rc, out = self.run_main("--yes", odd=odd)
        self.assertEqual(len(self.calls), n, "given up: not asked again")
        self.assertIn("1 given up after 2 failed reads", out)
        self.assertIn("--retry-failed asks again", out)
        rc, out = self.run_main("--yes", "--retry-failed")
        self.assertGreater(len(self.calls), n)
        self.assertEqual(self.kin("SELECT count(*) FROM kin_done WHERE source = 'inm'"), [(1,)])

    def test_salvage_reads_the_stored_replies_free(self):
        rc, out = self.run_main("--yes", odd={"Abhimanyu": "{"})   # failed, and nothing to salvage in it
        con = sqlite3.connect(str(self.t / "data" / "shelf" / "kin.db"))
        con.execute("UPDATE kin_reads SET raw = ? WHERE source = 'inm'", (CUT,))   # as the reads of 23 to 25 Oct
        con.commit()
        con.close()
        n = len(self.calls)
        rc, out = self.run_main("--salvage")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.calls), n, "free: no call")
        self.assertIn("salvage: 1 failed read(s) stored; 1 salvaged: 1 entries, 1 relations kept (free)", out)
        self.assertEqual(self.kin("SELECT status, relations FROM kin_reads WHERE source = 'inm'"), [("salvaged", 1)])
        self.assertIn("0 entries to read", out)
        rc, out = self.run_main("--salvage")
        self.assertIn("salvage: 0 failed read(s) stored", out, "once")


class TheFile(unittest.TestCase):
    def test_ascii(self):
        b = Path(__file__).read_bytes()
        self.assertTrue(all(x < 128 for x in b))


if __name__ == "__main__":
    unittest.main()
