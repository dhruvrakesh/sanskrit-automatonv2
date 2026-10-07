# -*- coding: ascii -*-
"""RECALL_768_2026_10_07: recall_check_768 measures how well the first 768 dimensions keep the
nearest neighbours of the full vectors. Synthetic vectors, no network, no real database."""
import os, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import numpy as np
except ImportError:   # pragma: no cover
    np = None


@unittest.skipIf(np is None, "numpy not installed")
class Recall768(unittest.TestCase):
    def _vectors(self, n=300, d=1024, head=768, tail_weight=0.05, seed=1):
        rng = np.random.default_rng(seed)
        m = rng.normal(size=(n, d)).astype(np.float32)
        m[:, head:] *= tail_weight          # Matryoshka-like: the leading dimensions carry the signal
        return m

    def test_leading_dimensions_keep_neighbours(self):
        import recall_check_768 as R
        r = R.recall(self._vectors(), dims=768, sample=50, ks=(5, 12), seed=3)
        self.assertGreater(r["recall@12"], 0.95, r)
        self.assertEqual(r["queries"], 50)

    def test_signal_beyond_the_cut_is_lost(self):
        import recall_check_768 as R
        m = self._vectors(tail_weight=1.0)
        m[:, :768] *= 0.05                  # the opposite: the signal sits after dimension 768
        r = R.recall(m, dims=768, sample=50, ks=(5, 12), seed=3)
        self.assertLess(r["recall@12"], 0.5, r)

    def test_cli_reads_only_and_skips_noise(self):
        d = tempfile.mkdtemp(prefix="recall_")
        db = os.path.join(d, "context.db")
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE passages(id INTEGER PRIMARY KEY, text_type TEXT)")
        con.execute("CREATE TABLE passage_embeddings(passage_id INTEGER PRIMARY KEY, model TEXT, dim INTEGER, vec BLOB)")
        m = self._vectors(n=120)
        for i, v in enumerate(m, 1):
            con.execute("INSERT INTO passages VALUES(?, ?)", (i, "noise" if i <= 20 else "mula"))
            con.execute("INSERT INTO passage_embeddings VALUES(?,?,?,?)", (i, "models/gemini-embedding-001", 1024, v.tobytes()))
        con.commit(); con.close()
        before = os.path.getmtime(db)
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "recall_check_768.py"), "--db", db,
                            "--immutable", "--sample", "30"], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("100 vectors of 1024 dimensions", r.stdout)
        self.assertIn("recall@12", r.stdout)
        self.assertEqual(before, os.path.getmtime(db))


if __name__ == "__main__":
    unittest.main()
