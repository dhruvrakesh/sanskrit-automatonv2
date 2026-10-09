#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_corpus_sync_split_2026_10_09.py  SYNC_SPLIT_2026_10_09

Why: the two-hourly mirror stopped at 12:32 and 14:32 IST on 2026-10-09 with
    vectors nilamata_seg: 50 to send
    ERROR: corpus-ingest HTTP 422: corpus_ingest: canceling statement due to statement timeout
Entities, passages, mentions and the Corner's stories went through; only the 50 new passage vectors
(halfvec(1536), each one an insert into the HNSW index of about 22,000 vectors) did not. Because a run
stops at its first error, the documents after nilamata_seg were not compared on those two ticks.

What changes in scripts/corpus_sync.py (client 4.2 -> 4.3):
  1. A batch the database cancels for its statement timeout is sent again as two halves, down to
     one row. A cancelled statement is rolled back whole and corpus_ingest is idempotent, so a
     re-send is safe. Any other error is raised as before, and so is a one-row timeout.
  2. Vectors travel 25 to a call instead of 150 (about 0.3 MB of text a call).
Nothing else changes: the rows, their hashes, the digests and the edge function stay as they are.

Anchored, all-or-nothing, marker-idempotent, md5-guarded (the file must be the one released on
2026-10-08, md5 b03f0684...). Backup .bak_split_<date>; LF kept; py_compile before the atomic replace.

  python scripts/patch_corpus_sync_split_2026_10_09.py --check
  python scripts/patch_corpus_sync_split_2026_10_09.py
Then: python -m unittest tests.test_corpus_sync_2026_10_08 tests.test_corpus_sync_split_2026_10_09
"""
from __future__ import annotations
import argparse, datetime, hashlib, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = "SYNC_SPLIT_2026_10_09"
TARGET = Path("scripts/corpus_sync.py")
WANT_MD5 = "b03f06842df43116ef4541588088a3a8"

EDITS = [
    ("the client version",
     'CLIENT_VERSION = "4.2"\n',
     'CLIENT_VERSION = "4.3"          # SYNC_SPLIT_2026_10_09: a timed-out batch is sent again in halves\n'),
    ("the vectors per call",
     "MAX_VEC_ROWS_PER_CALL = 150      # about 12 KB of text per vector\n",
     "MAX_VEC_ROWS_PER_CALL = 25       # about 12 KB of text per vector; SYNC_SPLIT_2026_10_09: 150 (and 50)\n"
     "                                 # timed out on 2026-10-09, each row an insert into the HNSW index\n"),
    ("the call in _send",
     "            res = self.sink.ingest(table, chunk, self.run_id) or {}\n",
     "            res = self._ingest(table, chunk)   # SYNC_SPLIT_2026_10_09\n"),
    ("the split",
     "    def _retire(self, table: str, group: str, keys: list, remote_n: int, local_n: int, whole_doc=False) -> bool:\n",
     "    def _ingest(self, table: str, chunk: list) -> dict:\n"
     "        \"\"\"SYNC_SPLIT_2026_10_09: a batch the database cancels for its statement timeout was rolled\n"
     "        back whole, and corpus_ingest is idempotent, so it is sent again as two halves, down to one\n"
     "        row. Any other error, and a one-row timeout, is raised as before.\"\"\"\n"
     "        try:\n"
     "            return self.sink.ingest(table, chunk, self.run_id) or {}\n"
     "        except SinkError as e:\n"
     "            if \"statement timeout\" not in str(e) or len(chunk) <= 1:\n"
     "                raise\n"
     "            half = len(chunk) // 2\n"
     "            self._p(\"    %s: the database timed out on %d rows; sending them as %d + %d\"\n"
     "                    % (table, len(chunk), half, len(chunk) - half))\n"
     "            a = self._ingest(table, chunk[:half])\n"
     "            b = self._ingest(table, chunk[half:])\n"
     "            return {\"received\": len(chunk),\n"
     "                    \"changed\": int(a.get(\"changed\", 0)) + int(b.get(\"changed\", 0))}\n"
     "\n"
     "    def _retire(self, table: str, group: str, keys: list, remote_n: int, local_n: int, whole_doc=False) -> bool:\n"),
]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if not TARGET.exists():
        print("FAIL: %s not found. Run from the repo root." % TARGET); return 2
    raw = TARGET.read_bytes()
    if MARK.encode() in raw:
        print("Nothing to do: %s already carries %s." % (TARGET, MARK)); return 0
    have = hashlib.md5(raw).hexdigest()
    if have != WANT_MD5:
        print("REFUSE: %s has md5 %s, not the released %s (changed since). Nothing written." % (TARGET, have, WANT_MD5))
        return 1
    text = raw.decode("utf-8")
    if "\r\n" in text:
        print("REFUSE: %s has CRLF line endings; expected LF. Nothing written." % TARGET); return 1
    for name, old, new in EDITS:
        n = text.count(old)
        if n != 1:
            print("REFUSE: anchor '%s' found %d times (want 1). Nothing written." % (name, n)); return 1
        text = text.replace(old, new, 1)
    data = text.encode("utf-8")
    try:
        data.decode("ascii")
    except UnicodeDecodeError:
        print("REFUSE: the result is not ASCII. Nothing written."); return 1
    with tempfile.TemporaryDirectory() as d:
        probe = Path(d) / "corpus_sync_probe.py"
        probe.write_bytes(data)
        try:
            py_compile.compile(str(probe), doraise=True)
        except py_compile.PyCompileError as e:
            print("REFUSE: the result does not compile: %s. Nothing written." % e); return 1
    if a.check:
        print("CHECK OK: %d edit(s) to %s. Nothing written." % (len(EDITS), TARGET)); return 0
    stamp = datetime.date.today().strftime("%Y%m%d")
    shutil.copy2(TARGET, TARGET.with_name(TARGET.name + ".bak_split_" + stamp))
    tmp = TARGET.with_name(TARGET.name + ".tmp_split")
    tmp.write_bytes(data)
    os.replace(tmp, TARGET)
    print("patched %s (%d edits; client 4.3). Backup: %s.bak_split_%s" % (TARGET, len(EDITS), TARGET.name, stamp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
