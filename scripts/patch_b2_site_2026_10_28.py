#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_b2_site_2026_10_28.py  (2026-10-28)  B2_SITE_2026_10_28

B2, asked on 28 Oct: "B2 (Raychaudhuri's view of each step)". docs/B2_AND_X1C_2026-10-28.md.

1. scripts\\index_sync.py (scheme i2): the genealogies' sync also sends the historian's view. It reads
   data\\shelf\\claims.db read-only (--claims-db): the works in the public domain only (Raychaudhuri 1923), their claims
   whose quotation was found on the page (exact or close), a name of the claim tied to ours only when one name of ours
   was found for it (cands 1; certain: exact or numbered exact; else probable); each statement gets "scholars" (the
   desk's kin_ties.scholar: agrees, differs, reversed, with the claims it rests on, found as kin_index.claims_index
   finds them) and each step its best "scholar". A statement or step without a verdict hashes as before, so only those
   with one are sent again. Until docs\\cloud\\C23 is pasted (the manifest has no claims) or corpus-index is deployed
   again (it answers "unknown table"), the claims wait and everything else is sent without the new fields and
   verified as before; the verdict says what to do.
2. tests\\test_index_site_pg_2026_10_25.py: the scheme it expects is the script's own (i1 or i2).

Anchored, all-or-nothing, marker-idempotent; line endings kept; .bak_b2site_<date> copies; py_compile first.
Needs INDEX_SITE_2026_10_25. No database is touched here.

  python scripts\\patch_b2_site_2026_10_28.py --check
  python scripts\\patch_b2_site_2026_10_28.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'B2_SITE_2026_10_28'
TAG = 'b2site'
FILES = ['scripts/index_sync.py', 'tests/test_index_site_pg_2026_10_25.py']
NEEDS = {'scripts/index_sync.py': 'INDEX_SITE_2026_10_25', 'tests/test_index_site_pg_2026_10_25.py': 'INDEX_SITE_2026_10_25'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/index_sync.py', 1, "their lines up and down, the steps, every kept relation the indexes state (all kinds), the longest lines, and the\nGRETIL verses where both names stand. The site's /corpus/genealogies reads them (Srangam INDEX_SITE_2026_10_25).\n\n  read     data/context.db (the shelf's entries, our names and their ties, our passages), data/shelf/kin.db (the\n           kinships read: kin_index.py), data/shelf/vamsa.db (their citations read in GRETIL: vamsa_check.py); all\n           read-only (--immutable for a backup copy). No model is called.\n  send     what differs only: the server's digest of each table first, then its keys and hashes; a row the desk no\n           longer has is deleted there (these tables are derived, recomputed every run).\n  not sent Raychaudhuri's claims (their mirror is B2); the Mahabharata e-text's words (BORI asks that the text not be\n           given to others: its references and counts only); the shelf's entries themselves (the Cologne files: only\n           the relations derived from them, with the words they rest on, as H2 decided, with the credit and the",
     "their lines up and down, the steps, every kept relation the indexes state (all kinds), the longest lines, and the\nGRETIL verses where both names stand. The site's /corpus/genealogies reads them (Srangam INDEX_SITE_2026_10_25).\nB2_SITE_2026_10_28 (scheme i2, docs/cloud/C23): and the scholars' claims beside them: each relation's verdict in\nRaychaudhuri's Political History of Ancient India (1923; public domain) as the desk weighs it (kin_index.py: agrees,\nreversed, differs), with the claims it rests on, and those claims themselves (data/shelf/claims.db: scholar_claims.py),\nonly the public-domain works', only the claims whose quotation was found on the page (exact or close), their names tied\nto ours only where one name of ours is the candidate. Until C23 is pasted the claims are left out, the rest is sent.\n\n  read     data/context.db (the shelf's entries, our names and their ties, our passages), data/shelf/kin.db (the\n           kinships read: kin_index.py), data/shelf/vamsa.db (their citations read in GRETIL: vamsa_check.py),\n           data/shelf/claims.db (the scholars' claims: scholar_claims.py); all read-only (--immutable for a backup\n           copy). No model is called.\n  send     what differs only: the server's digest of each table first, then its keys and hashes; a row the desk no\n           longer has is deleted there (these tables are derived, recomputed every run).\n  not sent a work not in the public domain; a claim whose quotation was not found on its page; the Mahabharata e-text's words (BORI asks that the text not be\n           given to others: its references and counts only); the shelf's entries themselves (the Cologne files: only\n           the relations derived from them, with the words they rest on, as H2 decided, with the credit and the")

edit('scripts/index_sync.py', 2, '\nMARK = "INDEX_SITE_2026_10_25"\nSCHEME = "i1"\nHERE = Path(__file__).resolve().parent\nROOT = HERE.parent\nsys.path.insert(0, str(HERE))\nTABLES = ("texts", "persons", "steps", "statements", "lines", "verses", "meta")\nMAX_ROWS, MAX_BYTES, MAX_KEYS = 1000, 3 * 1024 * 1024, 5000\nINDEX_RIGHTS = ("the relations derived from the index, with the entry\'s own words: Cologne Digital Sanskrit "',
     '\nMARK = "INDEX_SITE_2026_10_25"\nSCHEME = "i2"   # B2_SITE_2026_10_28: i2 adds the claims\nHERE = Path(__file__).resolve().parent\nROOT = HERE.parent\nsys.path.insert(0, str(HERE))\nTABLES = ("texts", "persons", "steps", "statements", "claims", "lines", "verses", "meta")\nOPTIONAL = ("claims",)   # sent only when the site has the table (C23) and corpus-index takes it\nMAX_ROWS, MAX_BYTES, MAX_KEYS = 1000, 3 * 1024 * 1024, 5000\nINDEX_RIGHTS = ("the relations derived from the index, with the entry\'s own words: Cologne Digital Sanskrit "')

edit('scripts/index_sync.py', 3, '# a citation\'s check: the forms (the two names as the verse writes them, to mark them) only for a text shown\nCITE_FIELDS = ("text", "ref", "verdict", "printed", "at", "subject_form", "object_form")\n\n',
     '# a citation\'s check: the forms (the two names as the verse writes them, to mark them) only for a text shown\nCITE_FIELDS = ("text", "ref", "verdict", "printed", "at", "subject_form", "object_form")\nCLAIM_QUOTES = ("exact", "close")          # a claim goes to the site only when its quotation was found on its page\nCERTAIN_TIES = ("exact", "numbered exact")  # the others are probable; the site says how each was made\nSCHOLAR_ORDER = ["agrees", "differs", "reversed"]   # vamsa_view\'s order of the scholars\' verdicts\n\n')

edit('scripts/index_sync.py', 4, '\n\ndef build(db: str, kin_db: str, vamsa_db: str, immutable: bool = False) -> dict:\n    """{table: [row]}: the site\'s rows, from the stores the dashboard\'s Vamsa page reads; read-only."""\n    import relations_view as rv',
     '\n\ndef _claims(claims_db: str, live, immutable: bool = False):\n    """(works rows, claim rows, (key_ix, pair_ix)) from data/shelf/claims.db, read-only. Only the public-domain works,\n    only the claims whose quotation was found on the page. The indexes match the claims to the kinships as kin_index.py\n    does (claims_index, norm: by our entities on both sides, every tie counted), so a verdict the site shows always has\n    a claim on the site beside it."""\n    if not claims_db or not Path(claims_db).exists():\n        return [], [], ({}, {})\n    import kin_index as ki\n    con = (ro_immutable(claims_db) if immutable else\n           sqlite3.connect(Path(claims_db).resolve().as_uri() + "?mode=ro", uri=True, timeout=10))\n    try:\n        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = \'table\'")}\n        if not {"claims", "claim_works", "claim_links"} <= have:\n            return [], [], ({}, {})\n        works = {}\n        for code, author, title, pub, year, source, handle, licence in con.execute(\n                "SELECT code, author, title, publisher, year, source, handle, licence FROM claim_works"):\n            if (licence or "").lower().startswith("public domain"):\n                works[code] = {"key": "work:" + code, "kind": "work", "code": code,\n                               "title": "%s, %s" % (author, title), "show": True, "rights": licence or "",\n                               "edition": "; ".join(x for x in ("%s, %s" % (pub, year) if pub else str(year or ""),\n                                                               "the scan: %s" % source if source else "",\n                                                               "handle %s" % handle if handle else "") if x)}\n        sides = collections.defaultdict(lambda: {"subject": set(), "object": set()})\n        tie_rows = collections.defaultdict(list)\n        for cid, role, eid, canonical, how, cands in con.execute(\n                "SELECT claim_id, role, entity_id, canonical, how, cands FROM claim_links"):\n            if role in ("subject", "object"):\n                sides[cid][role].add(eid)\n                tie_rows[(cid, role)].append((canonical, how, cands))\n        cites = collections.defaultdict(list)\n        if "claim_cites" in have:\n            for cid, printed, work, locus, ours, note in con.execute(\n                    "SELECT claim_id, printed, work, locus, ours, note FROM claim_cites ORDER BY claim_id, n"):\n                held = ours if ours and ours in live else None\n                cites[cid].append({"printed": printed or "", "work": work or "", "locus": locus or "",\n                                   "ours": held, "note": (note or "") if held else ""})\n        rows, key_of = [], {}\n        for (cid, work, page, printed, n, subj, rel, obj, claim, quote, qc, stance, hedge) in con.execute(\n                "SELECT id, work, pdf_page, printed, n, subject, relation, object, claim, quote, quote_check, stance, "\n                "hedge FROM claims ORDER BY work, pdf_page, n"):\n            if work not in works or qc not in CLAIM_QUOTES:\n                continue\n            key = "%s:%d:%d" % (work, page, n)\n            key_of[cid] = (key, rel)\n\n            def tie(role):\n                tr = tie_rows.get((cid, role), [])\n                if len(tr) == 1 and int(tr[0][2] or 0) == 1 and tr[0][0]:\n                    return tr[0][0], tr[0][1] or ""\n                return None, ""\n            sc, sh = tie("subject")\n            oc, oh = tie("object")\n            rows.append(finish({"key": key, "work": work, "pdf_page": page, "printed": printed or "", "n": n,\n                                "subject": subj or "", "relation": rel or "", "object": obj or "",\n                                "claim": claim or "", "quote": quote or "", "quote_check": qc, "stance": stance or "",\n                                "hedge": hedge or "", "subject_canonical": sc, "subject_how": sh,\n                                "object_canonical": oc, "object_how": oh, "cites": cites.get(cid, [])[:8]}))\n    finally:\n        con.close()\n    key_ix, pair_ix = collections.defaultdict(list), collections.defaultdict(list)\n    for cid, sd in sorted(sides.items()):\n        if cid not in key_of:\n            continue\n        ck, rel = key_of[cid]\n        for s in sorted(sd["subject"]):\n            for o in sorted(sd["object"]):\n                if s == o:\n                    continue\n                if ck not in pair_ix[(min(s, o), max(s, o))]:\n                    pair_ix[(min(s, o), max(s, o))].append(ck)\n                if rel in ki.CLASS and ck not in key_ix[ki.norm(rel, s, o)]:\n                    key_ix[ki.norm(rel, s, o)].append(ck)\n    return [finish(w) for _c, w in sorted(works.items())], rows, (key_ix, pair_ix)\n\n\ndef scholar_view(r: dict, ix) -> list:\n    """[{work, verdict, note, claims}]: the desk\'s verdict on a relation (kin_index.py, stored in kin_ties), with the\n    claims on the site it rests on; nothing when none of them is on the site."""\n    import kin_index as ki\n    verdict = r.get("raychaudhuri") or ""\n    s, o, rel = r.get("subject_entity"), r.get("object_entity"), r.get("relation")\n    if verdict not in SCHOLAR_ORDER or not s or not o or s == o:\n        return []\n    key_ix, pair_ix = ix\n    if verdict == "differs" or rel not in ki.CLASS:\n        keys = pair_ix.get((min(s, o), max(s, o)), [])\n    else:\n        k = ki.norm(rel, s, o)\n        keys = key_ix.get(k if verdict == "agrees" else (k[0], k[2], k[1]), [])\n    if not keys:\n        return []\n    by = collections.OrderedDict()\n    for ck in keys:\n        by.setdefault(ck.split(":")[0], []).append(ck)\n    return [{"work": w, "verdict": verdict, "note": r.get("raychaudhuri_note") or "", "claims": ks[:3]}\n            for w, ks in by.items()]\n\n\ndef _best_scholar(stmts: dict, keys: list) -> str:\n    """A step\'s scholar: the best verdict of its statements\' (agrees before differs before reversed), as /vamsa."""\n    vs = [sv["verdict"] for k in keys for sv in (stmts.get(k) or {}).get("scholars", [])]\n    vs = [x for x in vs if x in SCHOLAR_ORDER]\n    return min(vs, key=SCHOLAR_ORDER.index) if vs else ""\n\n\ndef build(db: str, kin_db: str, vamsa_db: str, immutable: bool = False, claims_db: str = "") -> dict:\n    """{table: [row]}: the site\'s rows, from the stores the dashboard\'s Vamsa page reads; read-only."""\n    import relations_view as rv')

edit('scripts/index_sync.py', 5, '        pairs = {(r["subject_entity"], r["object_entity"]) for r in rows_all\n                 if r.get("subject_entity") and r.get("object_entity") and r["subject_entity"] != r["object_entity"]}\n        places = _places(con, pairs, {r[1] for r in cs.live_docs(con)})\n    finally:\n        con.close()\n    key_of, stmts = {}, collections.OrderedDict()\n    for r in rows_all:',
     '        pairs = {(r["subject_entity"], r["object_entity"]) for r in rows_all\n                 if r.get("subject_entity") and r.get("object_entity") and r["subject_entity"] != r["object_entity"]}\n        live = {r[1] for r in cs.live_docs(con)}\n        places = _places(con, pairs, live)\n    finally:\n        con.close()\n    works, claims, cix = _claims(claims_db, live, immutable)   # B2_SITE_2026_10_28\n    out["texts"].extend(works)\n    out["claims"] = claims\n    key_of, stmts = {}, collections.OrderedDict()\n    for r in rows_all:')

edit('scripts/index_sync.py', 6, '        if k in stmts:\n            stmts[k]["n"] += 1\n            continue\n        x = v["rel"].get(r["kin_id"], {})',
     '        if k in stmts:\n            stmts[k]["n"] += 1\n            if not stmts[k]["scholars"]:\n                stmts[k]["scholars"] = scholar_view(r, cix)\n            continue\n        x = v["rel"].get(r["kin_id"], {})')

edit('scripts/index_sync.py', 7, '                               if k2 in c} for c in (x.get("cites") or [])[:6]],\n                    "best_text": x.get("best_text", ""), "best_ref": x.get("best_ref", ""),\n                    "together": x.get("together", {})}\n    out["statements"] = [finish(s) for s in stmts.values()]\n',
     '                               if k2 in c} for c in (x.get("cites") or [])[:6]],\n                    "best_text": x.get("best_text", ""), "best_ref": x.get("best_ref", ""),\n                    "together": x.get("together", {}), "scholars": scholar_view(r, cix)}\n    for s in stmts.values():\n        if not s["scholars"]:\n            del s["scholars"]   # a relation without a scholar\'s view keeps the row (and the hash) it had in i1\n    out["statements"] = [finish(s) for s in stmts.values()]\n')

edit('scripts/index_sync.py', 8, '                                    "joined": ev["joined"], "both_entries": bool(ev["both_entries"]),\n                                    "cited": ev["cited"], "ours": ev["ours"], "epic": ev["epic"],\n                                    "statements": keys, "verse_keys": vk}))\n\n    # the persons: every one with a parent, a child or a spouse in the index',
     '                                    "joined": ev["joined"], "both_entries": bool(ev["both_entries"]),\n                                    "cited": ev["cited"], "ours": ev["ours"], "epic": ev["epic"],\n                                    "statements": keys, "verse_keys": vk,\n                                    **({"scholar": sb} if (sb := _best_scholar(stmts, keys)) else {})}))\n\n    # the persons: every one with a parent, a child or a spouse in the index')

edit('scripts/index_sync.py', 9, '\n\ndef sync(rows: dict, sink, apply: bool, log=print) -> dict:\n    """Send what differs: a table whose digest the server has is left alone; else only the rows whose hash differs,\n    and the keys the desk no longer has are deleted. The run\'s row (meta) goes last."""\n    man = sink.manifest() or {}\n    got = {"tables": {}, "sent": 0, "deleted": 0, "changed": 0}\n    for t in TABLES:\n        mine = {r["key"]: r for r in rows.get(t, [])}\n        d = digest((k, r["row_hash"]) for k, r in mine.items())',
     '\n\ndef without_claims(rows: dict) -> dict:\n    """The rows as a site without C23 stores them: no scholars\' verdicts on the statements and the steps (C21\'s ingest\n    has no column for them). Their hashes are then the ones such a site keeps, so once C23 is pasted they differ and\n    the rows go again with the verdicts (else a site that took them before C23 would never get the verdicts)."""\n    out = dict(rows)\n    for t, field in (("statements", "scholars"), ("steps", "scholar")):\n        out[t] = [finish({k: v for k, v in r.items() if k not in (field, "row_hash")}) for r in rows.get(t, [])]\n    return out\n\n\ndef sync(rows: dict, sink, apply: bool, log=print) -> dict:\n    """Send what differs: a table whose digest the server has is left alone; else only the rows whose hash differs,\n    and the keys the desk no longer has are deleted. The run\'s row (meta) goes last."""\n    man = sink.manifest() or {}\n    got = {"tables": {}, "sent": 0, "deleted": 0, "changed": 0, "waiting": []}\n    if not all(t in man for t in OPTIONAL):\n        rows = without_claims(rows)   # B2_SITE_2026_10_28: C23 not pasted yet\n    for t in TABLES:\n        if t in OPTIONAL and t not in man:\n            got["waiting"].append(t)   # B2_SITE_2026_10_28: the site has no such table yet (C23 not pasted)\n            log("  %-10s here %6d, the site has no table for them yet (C23): left for later" % (t, len(rows.get(t, []))))\n            continue\n        mine = {r["key"]: r for r in rows.get(t, [])}\n        d = digest((k, r["row_hash"]) for k, r in mine.items())')

edit('scripts/index_sync.py', 10, '            got["tables"][t] = {"here": len(mine), "there": len(mine), "send": 0, "delete": 0}\n            continue\n        keys = sink.keys(t) or {}\n        send = [r for k, r in mine.items() if keys.get(k) != r["row_hash"]]\n        gone = sorted(k for k in keys if k not in mine)',
     '            got["tables"][t] = {"here": len(mine), "there": len(mine), "send": 0, "delete": 0}\n            continue\n        try:\n            keys = sink.keys(t) or {}\n        except SinkError as e:\n            if t in OPTIONAL and "unknown table" in str(e):\n                got["waiting"].append(t)   # corpus-index not yet deployed again with the table\n                log("  %-10s corpus-index does not take them yet (deploy it again): left for later" % t)\n                continue\n            raise\n        send = [r for k, r in mine.items() if keys.get(k) != r["row_hash"]]\n        gone = sorted(k for k in keys if k not in mine)')

edit('scripts/index_sync.py', 11, '    if apply:\n        after = sink.manifest() or {}\n        bad = [t for t in TABLES if (after.get(t) or {}).get("digest") !=\n               digest((r["key"], r["row_hash"]) for r in rows.get(t, []))]\n        got["verified"] = {"tables_equal": len(TABLES) - len(bad), "tables_different": bad}\n    return got\n',
     '    if apply:\n        after = sink.manifest() or {}\n        tabs = [t for t in TABLES if t not in got["waiting"]]\n        bad = [t for t in tabs if (after.get(t) or {}).get("digest") !=\n               digest((r["key"], r["row_hash"]) for r in rows.get(t, []))]\n        got["verified"] = {"tables_equal": len(tabs) - len(bad), "tables_different": bad}\n    return got\n')

edit('scripts/index_sync.py', 12, '    ap.add_argument("--kin-db", default="")\n    ap.add_argument("--vamsa-db", default="")\n    ap.add_argument("--immutable", action="store_true", help="the database is a backup copy: read it as immutable")\n    ap.add_argument("--sink", default="auto", choices=("auto", "edge", "pg", "none"))',
     '    ap.add_argument("--kin-db", default="")\n    ap.add_argument("--vamsa-db", default="")\n    ap.add_argument("--claims-db", default="", help="the scholars\' claims (default data\\\\shelf\\\\claims.db; none there: none sent)")\n    ap.add_argument("--immutable", action="store_true", help="the database is a backup copy: read it as immutable")\n    ap.add_argument("--sink", default="auto", choices=("auto", "edge", "pg", "none"))')

edit('scripts/index_sync.py', 13, '    kin = a.kin_db or str(ROOT / "data" / "shelf" / "kin.db")\n    vam = a.vamsa_db or str(ROOT / "data" / "shelf" / "vamsa.db")\n    print("index_sync.py  %s  %s" % (MARK, "APPLY" if a.apply else "PLAN (nothing sent)"))\n    if a.if_configured and not a.dump and a.sink in ("auto", "edge"):',
     '    kin = a.kin_db or str(ROOT / "data" / "shelf" / "kin.db")\n    vam = a.vamsa_db or str(ROOT / "data" / "shelf" / "vamsa.db")\n    clm = a.claims_db or str(ROOT / "data" / "shelf" / "claims.db")\n    print("index_sync.py  %s  %s" % (MARK, "APPLY" if a.apply else "PLAN (nothing sent)"))\n    if a.if_configured and not a.dump and a.sink in ("auto", "edge"):')

edit('scripts/index_sync.py', 14, '            return 0 if a.if_configured else 1\n    t0 = time.time()\n    rows = build(db, kin, vam, immutable=a.immutable)\n    sizes = {t: sum(len(json.dumps(r, ensure_ascii=False)) for r in rows[t]) for t in TABLES}\n    print("built in %.1f s: %s" % (time.time() - t0, ", ".join("%s %d (%.1f MB)" % (t, len(rows[t]), sizes[t] / 1e6)',
     '            return 0 if a.if_configured else 1\n    t0 = time.time()\n    rows = build(db, kin, vam, immutable=a.immutable, claims_db=clm)\n    sizes = {t: sum(len(json.dumps(r, ensure_ascii=False)) for r in rows[t]) for t in TABLES}\n    print("built in %.1f s: %s" % (time.time() - t0, ", ".join("%s %d (%.1f MB)" % (t, len(rows[t]), sizes[t] / 1e6)')

edit('scripts/index_sync.py', 15, '        say("stopped: %s" % e, "python scripts\\\\index_sync.py   (the plan, again)")\n        return 1\n    if a.status or not a.apply:\n        todo = sum(x["send"] + x["delete"] for x in got["tables"].values())\n        say("%s: %d row(s) to send or delete%s" % ("the site is current" if not todo else "the plan", todo,\n                                                     " (no network: --sink none)" if sink.name == "none" else ""),\n            "python scripts\\\\index_sync.py --apply" if todo else "")\n        return 0\n    v = got.get("verified") or {}',
     '        say("stopped: %s" % e, "python scripts\\\\index_sync.py   (the plan, again)")\n        return 1\n    wait = (["the claims wait (%s): paste docs\\\\cloud\\\\C23_index_claims_2026-10-28.sql, then ask Lovable to deploy "\n             "supabase/functions/corpus-index again" % ", ".join(got["waiting"])] if got.get("waiting") else [])\n    if a.status or not a.apply:\n        todo = sum(x["send"] + x["delete"] for x in got["tables"].values())\n        say("%s: %d row(s) to send or delete%s" % ("the site is current" if not todo else "the plan", todo,\n                                                     " (no network: --sink none)" if sink.name == "none" else ""),\n            "python scripts\\\\index_sync.py --apply" if todo else "", wait)\n        return 0\n    v = got.get("verified") or {}')

edit('scripts/index_sync.py', 16, '    say("sent %d row(s) (%d changed), deleted %d; the site\'s genealogies equal the desk\'s (%d tables)" % (\n        got["sent"], got["changed"], got["deleted"], v.get("tables_equal", 0)),\n        "open /corpus/genealogies on the site (signed in)")\n    return 0\n',
     '    say("sent %d row(s) (%d changed), deleted %d; the site\'s genealogies equal the desk\'s (%d tables)" % (\n        got["sent"], got["changed"], got["deleted"], v.get("tables_equal", 0)),\n        "open /corpus/genealogies on the site (signed in)", wait)\n    return 0\n')

edit('tests/test_index_site_pg_2026_10_25.py', 1, '        self.assertEqual(sorted(self.rows), sorted(self.ix.TABLES))\n        run = self.rows["meta"][0]\n        self.assertEqual((run["key"], run["value"]["mark"], run["value"]["scheme"]), ("run", MARK, "i1"))\n        self.assertEqual(run["value"]["counts"], {t: len(self.rows[t]) for t in self.ix.TABLES if t != "meta"})\n        for t in self.ix.TABLES:',
     '        self.assertEqual(sorted(self.rows), sorted(self.ix.TABLES))\n        run = self.rows["meta"][0]\n        # B2_SITE_2026_10_28: the scheme is index_sync\'s own (i2 adds the scholars\' claims)\n        self.assertEqual((run["key"], run["value"]["mark"], run["value"]["scheme"]), ("run", MARK, self.ix.SCHEME))\n        self.assertIn(self.ix.SCHEME, ("i1", "i2"))\n        self.assertEqual(run["value"]["counts"], {t: len(self.rows[t]) for t in self.ix.TABLES if t != "meta"})\n        for t in self.ix.TABLES:')


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

