"""
SYNC_SPLIT_2026_10_09 - a batch the database cancels for its statement timeout is sent again in
halves (down to one row); any other error, and a one-row timeout, stops the run as before. The fixture,
the fake server and the fake sink are those of tests/test_corpus_sync_2026_10_08.py.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import corpus_sync as cs                      # noqa: E402
import test_corpus_sync_2026_10_08 as base    # noqa: E402

TIMEOUT = "corpus-ingest HTTP 422: {\"ok\":false,\"error\":\"corpus_ingest: canceling statement due to statement timeout\"}"


class SlowVectors(base.FakeSink):
    """Times out on any vectors batch of more than `limit` rows, as the HNSW inserts did."""

    def __init__(self, server, limit=2, error=TIMEOUT):
        super().__init__(server)
        self.limit, self.error, self.sizes = limit, error, []

    def ingest(self, table, rows, run_id):
        if table == "vectors":
            self.sizes.append(len(rows))
            if len(rows) > self.limit:
                raise cs.SinkError(self.error)
        return super().ingest(table, rows, run_id)


class Split(base.Base):
    def test_the_client_says_43_and_sends_vectors_25_to_a_call(self):
        self.assertEqual(cs.CLIENT_VERSION, "4.3")
        self.assertEqual(cs.MAX_VEC_ROWS_PER_CALL, 25)

    def test_a_timed_out_batch_is_sent_again_in_halves(self):
        notes = []
        sink = SlowVectors(self.server, limit=2)
        s = self.sync(sink=sink, progress=notes.append)
        self.assertEqual(s["stopped"], "done", s)
        self.assertEqual(s["tables"]["vectors"]["changed"], 10)          # every vector arrived
        self.assertGreater(max(sink.sizes), 2)                            # a whole batch was tried first
        first = sink.sizes[0]
        self.assertTrue(any("vectors: the database timed out on %d rows; sending them as %d + %d"
                            % (first, first // 2, first - first // 2) in n for n in notes), notes)
        self.assertEqual(s["verified"]["groups_different"], 0)
        again = self.sync(sink=SlowVectors(self.server, limit=2))
        self.assertEqual(again["tables"]["vectors"]["changed"], 0)

    def test_another_error_is_not_split(self):
        sink = SlowVectors(self.server, limit=2, error="corpus-ingest HTTP 401: bad signature")
        s = self.sync(sink=sink)
        self.assertEqual(s["stopped"], "error")
        self.assertIn("bad signature", s["error"])
        self.assertEqual(len(sink.sizes), 1)                              # tried once, not split

    def test_a_single_row_that_times_out_is_raised(self):
        sink = SlowVectors(self.server, limit=0)
        s = self.sync(sink=sink)
        self.assertEqual(s["stopped"], "error")
        self.assertIn("statement timeout", s["error"])
        self.assertIn(1, sink.sizes)                                      # halved down to one row, then stopped


if __name__ == "__main__":
    unittest.main()
