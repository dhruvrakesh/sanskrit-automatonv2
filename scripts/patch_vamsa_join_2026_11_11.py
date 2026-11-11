#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_vamsa_join_2026_11_11.py  (2026-11-11)  VAMSA_JOIN_2026_11_11

G5c: the dynasties to the site. scripts\\vamsa_join.py (new, beside this patch) joins G5a's lines (vamsa_read.py: the
Puranas' own genealogical books read verse by verse) to the Purana Index's persons; index_sync.py now sends them as the
table dynasties (one row a line, one a work's counts), which docs\\cloud\\C28_index_dynasties_2026-11-11.sql makes on the
site, for the Dynasties page (the Srangam kit DYNASTIES_2026_11_11).
  scripts/index_sync.py   the table dynasties (optional, as the claims: sent only when the site has the table and
                          corpus-index takes it; nothing waits when there is nothing to send); --vamsa-read; the claims'
                          verdicts stripped only when the claims' own table is missing (not when C28 is)
  tests/test_b2_site_pg_2026_10_28.py   a table with nothing to send and none there is not counted among the equal
Until C28 is pasted and corpus-index deployed again, index_sync.py sends the rest as before and says the dynasties wait.

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_vamsajoin_<date> copies.

  python scripts\\patch_vamsa_join_2026_11_11.py --check
  python scripts\\patch_vamsa_join_2026_11_11.py
  python scripts\\vamsa_join.py
  python scripts\\index_sync.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_JOIN_2026_11_11'
TAG = 'vamsajoin'
FILES = ['scripts/index_sync.py', 'tests/test_b2_site_pg_2026_10_28.py']
NEEDS = {'scripts/index_sync.py': 'GENEALOGY_HEAL_2026_11_10', 'tests/test_b2_site_pg_2026_10_28.py': 'B2_SITE_2026_10_28'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/index_sync.py', 1, '\nThe last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py\'s.\n"""\nfrom __future__ import annotations',
     '\nThe last lines are VERDICT:, NEXT: and ALSO:, as repair_text.py\'s.\n\nVAMSA_JOIN_2026_11_11 (G5c): and the dynasties, the Puranas\' own lines read verse by verse (vamsa_read.py, G5a) and\njoined to the Purana Index\'s persons (vamsa_join.py, G5b): the table dynasties (docs\\\\cloud\\\\C28_index_dynasties_\n2026-11-11.sql), one row a line of three persons or more, each step with its verse, its Sanskrit words (GRETIL\'s text,\nCC BY-NC-SA 4.0, as the verses the site shows already), its index person and what the index says of it; a row "<work>:0"\na work\'s counts. Sent only when the site has the table (C28) and corpus-index takes it (the Srangam kit DYNASTIES),\nas the claims were; until then the rest goes as before and the plan says the dynasties wait.\n"""\nfrom __future__ import annotations')

edit('scripts/index_sync.py', 2, 'ROOT = HERE.parent\nsys.path.insert(0, str(HERE))\nTABLES = ("texts", "persons", "steps", "statements", "claims", "lines", "verses", "meta")\nOPTIONAL = ("claims",)   # sent only when the site has the table (C23) and corpus-index takes it\nMAX_ROWS, MAX_BYTES, MAX_KEYS = 1000, 3 * 1024 * 1024, 5000\nINDEX_RIGHTS = ("the relations derived from the index, with the entry\'s own words: Cologne Digital Sanskrit "',
     'ROOT = HERE.parent\nsys.path.insert(0, str(HERE))\nTABLES = ("texts", "persons", "steps", "statements", "claims", "lines", "verses", "dynasties", "meta")   # VAMSA_JOIN_2026_11_11: dynasties\nOPTIONAL = ("claims", "dynasties")   # sent only when the site has the table (C23, C28) and corpus-index takes it\nMAX_ROWS, MAX_BYTES, MAX_KEYS = 1000, 3 * 1024 * 1024, 5000\nINDEX_RIGHTS = ("the relations derived from the index, with the entry\'s own words: Cologne Digital Sanskrit "')

edit('scripts/index_sync.py', 3, '\n\ndef build(db: str, kin_db: str, vamsa_db: str, immutable: bool = False, claims_db: str = "") -> dict:\n    """{table: [row]}: the site\'s rows, from the stores the dashboard\'s Vamsa page reads; read-only."""\n    import relations_view as rv\n    if immutable:',
     '\n\ndef build(db: str, kin_db: str, vamsa_db: str, immutable: bool = False, claims_db: str = "",\n          vamsa_read_dir: str = "") -> dict:\n    """{table: [row]}: the site\'s rows, from the stores the dashboard\'s Vamsa page reads; read-only. vamsa_read_dir:\n    G5a\'s readings (data\\\\vamsa_read), for the dynasties (VAMSA_JOIN_2026_11_11); none given, none sent."""\n    import relations_view as rv\n    if immutable:')

edit('scripts/index_sync.py', 4, '            out["verses"].append(finish({"key": "%s|%s" % (t, ref), "text": t, "ref": ref, "words": w}))\n\n    counts = {t: len(out[t]) for t in TABLES if t != "meta"}\n    out["meta"].append(finish({"key": "run", "value": {"mark": MARK, "scheme": SCHEME, "counts": counts,',
     '            out["verses"].append(finish({"key": "%s|%s" % (t, ref), "text": t, "ref": ref, "words": w}))\n\n    # VAMSA_JOIN_2026_11_11: the dynasties, the Puranas\' own lines joined to the index\'s persons (vamsa_join.py)\n    if vamsa_read_dir and Path(vamsa_read_dir).exists():\n        out["dynasties"] = dynasty_rows(vamsa_read_dir, db, kin_db, g, {r["key"] for r in out["persons"]})\n    counts = {t: len(out[t]) for t in TABLES if t != "meta"}\n    out["meta"].append(finish({"key": "run", "value": {"mark": MARK, "scheme": SCHEME, "counts": counts,')

edit('scripts/index_sync.py', 5, '                                                       "kin": v["meta"].get("kin", "")}}))\n    return out\n\n',
     '                                                       "kin": v["meta"].get("kin", "")}}))\n    return out\n\n\nSTEP_FIELDS = ("name", "father", "ref", "words", "person", "index_head", "how", "index", "joined")\n\n\ndef dynasty_rows(vamsa_read_dir: str, db: str, kin_db: str, g: dict, persons: set) -> list:\n    """VAMSA_JOIN_2026_11_11: one row a line ("<work>:<n>"), and one a work ("<work>:0", its counts); a step\'s person\n    is linked ("page") only when the site has a page for it (a person with a line)."""\n    import vamsa_join as vj\n    d = vj.dynasties(vamsa_read_dir, db, kin_db, graph=g)\n    rows = []\n    for wk, w in sorted(d.items()):\n        rows.append(finish({"key": "%s:0" % wk, "work": wk, "n": 0, "title": w["title"], "text_code": w["text"],\n                            "label": "", "length": 0, "steps": [], "counts": w["counts"], "source": w["source"]}))\n        for ln in w["lines"]:\n            steps = []\n            for s in ln["steps"]:\n                x = {k: s.get(k) for k in STEP_FIELDS if s.get(k) not in (None, "")}\n                if s.get("person") and s["person"] in persons:\n                    x["page"] = True\n                steps.append(x)\n            rows.append(finish({"key": "%s:%d" % (wk, ln["n"]), "work": wk, "n": ln["n"], "title": w["title"],\n                                "text_code": w["text"], "label": ln["label"], "length": ln["length"], "steps": steps,\n                                "counts": {}, "source": w["source"]}))\n    return rows\n\n')

edit('scripts/index_sync.py', 6, '    man = sink.manifest() or {}\n    got = {"tables": {}, "sent": 0, "deleted": 0, "changed": 0, "waiting": [], "features_waiting": []}\n    if not all(t in man for t in OPTIONAL):\n        rows = without_claims(rows)   # B2_SITE_2026_10_28: C23 not pasted yet\n    if not (man.get("features") or {}).get("aliases"):',
     '    man = sink.manifest() or {}\n    got = {"tables": {}, "sent": 0, "deleted": 0, "changed": 0, "waiting": [], "features_waiting": []}\n    if "claims" not in man:   # VAMSA_JOIN_2026_11_11: the claims\' table only (C28\'s table says nothing of them)\n        rows = without_claims(rows)   # B2_SITE_2026_10_28: C23 not pasted yet\n    if not (man.get("features") or {}).get("aliases"):')

edit('scripts/index_sync.py', 7, '        got["features_waiting"].append("aliases")\n    for t in TABLES:\n        if t in OPTIONAL and t not in man:\n            got["waiting"].append(t)   # B2_SITE_2026_10_28: the site has no such table yet (C23 not pasted)',
     '        got["features_waiting"].append("aliases")\n    for t in TABLES:\n        if t in OPTIONAL and t not in man and not rows.get(t):\n            got.setdefault("absent", []).append(t)   # VAMSA_JOIN_2026_11_11: nothing to send, no table there: nothing\n            continue\n        if t in OPTIONAL and t not in man:\n            got["waiting"].append(t)   # B2_SITE_2026_10_28: the site has no such table yet (C23 not pasted)')

edit('scripts/index_sync.py', 8, '    if apply:\n        after = sink.manifest() or {}\n        tabs = [t for t in TABLES if t not in got["waiting"]]\n        bad = [t for t in tabs if (after.get(t) or {}).get("digest") !=\n               digest((r["key"], r["row_hash"]) for r in rows.get(t, []))]',
     '    if apply:\n        after = sink.manifest() or {}\n        tabs = [t for t in TABLES if t not in got["waiting"] and t not in got.get("absent", [])]\n        bad = [t for t in tabs if (after.get(t) or {}).get("digest") !=\n               digest((r["key"], r["row_hash"]) for r in rows.get(t, []))]')

edit('scripts/index_sync.py', 9, '    ap.add_argument("--kin-db", default="")\n    ap.add_argument("--vamsa-db", default="")\n    ap.add_argument("--claims-db", default="", help="the scholars\' claims (default data\\\\shelf\\\\claims.db; none there: none sent)")\n    ap.add_argument("--immutable", action="store_true", help="the database is a backup copy: read it as immutable")',
     '    ap.add_argument("--kin-db", default="")\n    ap.add_argument("--vamsa-db", default="")\n    ap.add_argument("--vamsa-read", default="", help="G5a\'s readings, for the dynasties (default data\\\\vamsa_read)")\n    ap.add_argument("--claims-db", default="", help="the scholars\' claims (default data\\\\shelf\\\\claims.db; none there: none sent)")\n    ap.add_argument("--immutable", action="store_true", help="the database is a backup copy: read it as immutable")')

edit('scripts/index_sync.py', 10, '    kin = a.kin_db or str(ROOT / "data" / "shelf" / "kin.db")\n    vam = a.vamsa_db or str(ROOT / "data" / "shelf" / "vamsa.db")\n    clm = a.claims_db or str(ROOT / "data" / "shelf" / "claims.db")\n    print("index_sync.py  %s  %s" % (MARK, "APPLY" if a.apply else "PLAN (nothing sent)"))',
     '    kin = a.kin_db or str(ROOT / "data" / "shelf" / "kin.db")\n    vam = a.vamsa_db or str(ROOT / "data" / "shelf" / "vamsa.db")\n    vrd = a.vamsa_read or str(ROOT / "data" / "vamsa_read")   # VAMSA_JOIN_2026_11_11\n    clm = a.claims_db or str(ROOT / "data" / "shelf" / "claims.db")\n    print("index_sync.py  %s  %s" % (MARK, "APPLY" if a.apply else "PLAN (nothing sent)"))')

edit('scripts/index_sync.py', 11, '            return 0 if a.if_configured else 1\n    t0 = time.time()\n    rows = build(db, kin, vam, immutable=a.immutable, claims_db=clm)\n    sizes = {t: sum(len(json.dumps(r, ensure_ascii=False)) for r in rows[t]) for t in TABLES}\n    print("built in %.1f s: %s" % (time.time() - t0, ", ".join("%s %d (%.1f MB)" % (t, len(rows[t]), sizes[t] / 1e6)',
     '            return 0 if a.if_configured else 1\n    t0 = time.time()\n    rows = build(db, kin, vam, immutable=a.immutable, claims_db=clm, vamsa_read_dir=vrd)\n    sizes = {t: sum(len(json.dumps(r, ensure_ascii=False)) for r in rows[t]) for t in TABLES}\n    print("built in %.1f s: %s" % (time.time() - t0, ", ".join("%s %d (%.1f MB)" % (t, len(rows[t]), sizes[t] / 1e6)')

edit('scripts/index_sync.py', 12, '        say("stopped: %s" % e, "python scripts\\\\index_sync.py   (the plan, again)")\n        return 1\n    wait = (["the claims wait (%s): paste docs\\\\cloud\\\\C23_index_claims_2026-10-28.sql, then ask Lovable to deploy "\n             "supabase/functions/corpus-index again" % ", ".join(got["waiting"])] if got.get("waiting") else [])\n    if "aliases" in got.get("features_waiting", []):   # GENEALOGY_HEAL_2026_11_10\n        wait.append("the epithets wait (Kaunteya = Arjuna): paste docs\\\\cloud\\\\C26_index_aliases_2026-11-10.sql in one "',
     '        say("stopped: %s" % e, "python scripts\\\\index_sync.py   (the plan, again)")\n        return 1\n    wait = (["the claims wait: paste docs\\\\cloud\\\\C23_index_claims_2026-10-28.sql, then ask Lovable to deploy "\n             "supabase/functions/corpus-index again"] if "claims" in got.get("waiting", []) else [])\n    if "dynasties" in got.get("waiting", []):   # VAMSA_JOIN_2026_11_11\n        wait.append("the dynasties wait (%d lines): paste docs\\\\cloud\\\\C28_index_dynasties_2026-11-11.sql (B1, the "\n                    "change, A1), then the Srangam kit DYNASTIES (corpus-index deployed again), then python "\n                    "scripts\\\\index_sync.py --apply" % sum(1 for r in rows.get("dynasties", []) if r.get("n")))\n    if "aliases" in got.get("features_waiting", []):   # GENEALOGY_HEAL_2026_11_10\n        wait.append("the epithets wait (Kaunteya = Arjuna): paste docs\\\\cloud\\\\C26_index_aliases_2026-11-10.sql in one "')

edit('tests/test_b2_site_pg_2026_10_28.py', 1, '        self.assertEqual(self.before["waiting"], ["claims"])\n        self.assertEqual(self.before["verified"]["tables_different"], [])\n        self.assertEqual(self.before["verified"]["tables_equal"], len(self.ix.TABLES) - 1)\n\n    def test_with_c23_the_claims_go_and_all_is_verified(self):',
     '        self.assertEqual(self.before["waiting"], ["claims"])\n        self.assertEqual(self.before["verified"]["tables_different"], [])\n        self.assertEqual(self.before["verified"]["tables_equal"],   # VAMSA_JOIN_2026_11_11: a table with nothing to send\n                         len(self.ix.TABLES) - 1 - len(self.before.get("absent", [])))   # and none there is not counted\n\n    def test_with_c23_the_claims_go_and_all_is_verified(self):')


def nl_of(raw: bytes) -> str:
    return "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); args = ap.parse_args()
    stamp = datetime.date.today().strftime("%Y%m%d")
    for f, m in REQUIRES.items():
        if not Path(f).exists() or m.encode() not in Path(f).read_bytes():
            print("REFUSE: %s does not carry %s (apply it first). Nothing written." % (f, m)); return 1
    plan = {}
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print("REFUSE: %s is not here (run this from the repository root). Nothing written." % f); return 1
        raw = p.read_bytes()
        if MARK.encode() in raw:
            print("skip %s (already carries %s)" % (f, MARK)); continue
        need = NEEDS.get(f)
        if need and need.encode() not in raw:
            print("REFUSE: %s does not carry %s (apply that first). Nothing written." % (f, need)); return 1
        nl = nl_of(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        for ff, n, old, new in E:
            if ff != f:
                continue
            k = text.count(old)
            if k != 1:
                print("REFUSE: %s: anchor %d found %d times (want 1). Nothing written." % (f, n, k)); return 1
            text = text.replace(old, new)
        plan[f] = (text.replace("\n", "\r\n") if nl == "\r\n" else text).encode("utf-8")
    if not plan:
        print("Nothing to do: every file already carries %s." % MARK); return 0
    for f, data in plan.items():
        if f.endswith(".py"):
            with tempfile.TemporaryDirectory() as td:
                t = Path(td) / Path(f).name
                t.write_bytes(data)
                try:
                    py_compile.compile(str(t), cfile=str(t) + "c", doraise=True)
                except py_compile.PyCompileError as e:
                    print("FAIL: %s would not compile (%s). Nothing written." % (f, e)); return 1
    if args.check:
        print("CHECK OK: %d file(s) to write. Nothing written." % len(plan)); return 0
    done = []
    try:
        for f, data in plan.items():
            p = Path(f)
            shutil.copy2(p, p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp)))
            tmp = p.with_name(p.name + ".tmp_" + TAG)
            tmp.write_bytes(data)
            os.replace(tmp, p)
            done.append(f)
            print("wrote %s" % f)
    except OSError as e:
        print("FAIL while writing (%s). Restore from the .bak_%s_%s copies: %s" % (e, TAG, stamp, ", ".join(done)))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

