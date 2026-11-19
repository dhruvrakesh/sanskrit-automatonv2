#!/usr/bin/env python3
# -*- coding: ascii -*-
"""
patch_vamsa_wayin_2026_11_18.py  (2026-11-18)  VAMSA_WAYIN_2026_11_18

P2c of the path of 18 Nov: the way in by vamsa (Suryavamsa, Candravamsa) across the works, on the site.
  scripts/vamsa_align.py   vamsa_of(slug): "surya" for the solar line and the Videhas, "candra" for Pururavas's line and
                           every branch of it (ANCHORS), "" for any other
  tests/test_vamsa_site_2026_11_18.py, tests/test_vamsa_names_2026_11_18.py: their replay is compared with the file
                           no more once this patch has changed it again (a test's heal only)
  scripts/index_sync.py    the table vamsas (optional, as the dynasties were): one row a dynasty of G6c
                           (data\\\\vamsa_read\\\\aligned.json): its founder, vamsa, works, generations, each work's name tied
                           to its line of the dynasties sent, Dikshitar's person (the Purana Index) and Raychaudhuri's
                           claims the site carries already (C23; B. C. Law's never); waits until the site has
                           docs\\\\cloud\\\\C29_index_vamsas_2026-11-18.sql and corpus-index takes it (the Srangam kit
                           VAMSA_WAYIN)
Measured on 18 Nov (the backup of 18 Nov, immutable): 10 dynasties, 174 generations, 725 names, 622 tied to a line,
134 generations with Dikshitar's person, 21 with Raychaudhuri's claims on the name, 1 on both persons of a step;
about 105 kB. No model is called; nothing is spent.

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_vamsawayin_<date> copies.

  python scripts\\\\patch_vamsa_wayin_2026_11_18.py --check
  python scripts\\\\patch_vamsa_wayin_2026_11_18.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_WAYIN_2026_11_18'
TAG = 'vamsawayin'
FILES = ['scripts/vamsa_align.py', 'scripts/index_sync.py', 'tests/test_vamsa_site_2026_11_18.py', 'tests/test_vamsa_names_2026_11_18.py']
NEEDS = {'scripts/vamsa_align.py': 'VAMSA_NAMES_2026_11_18', 'scripts/index_sync.py': 'VAMSA_SITE_2026_11_18', 'tests/test_vamsa_site_2026_11_18.py': 'VAMSA_SITE_2026_11_18', 'tests/test_vamsa_names_2026_11_18.py': 'VAMSA_NAMES_2026_11_18'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/vamsa_align.py', 1, '    ("magadha", "B\\u1e5bhadratha", "Vasu", "the B\\u0101rhadrathas of Magadha from B\\u1e5bhadratha son of Vasu"),\n]\n\n',
     '    ("magadha", "B\\u1e5bhadratha", "Vasu", "the B\\u0101rhadrathas of Magadha from B\\u1e5bhadratha son of Vasu"),\n]\n# VAMSA_WAYIN_2026_11_18: the vamsa of each founder\'s line: the solar line and the Videhas (Nimi, son of Ikshvaku) are\n# of the Suryavamsa; Pururavas\'s line and every branch of it (Yayati\'s five sons and theirs) of the Candravamsa\nSURYA = ("solar", "videha")\n\n\ndef vamsa_of(slug: str) -> str:\n    """"surya" or "candra" for a founder of ANCHORS; "" for any other."""\n    if slug in SURYA:\n        return "surya"\n    return "candra" if any(slug == a[0] for a in ANCHORS) else ""\n\n')

edit('scripts/index_sync.py', 1, 'a work\'s counts. Sent only when the site has the table (C28) and corpus-index takes it (the Srangam kit DYNASTIES),\nas the claims were; until then the rest goes as before and the plan says the dynasties wait.\n"""\nfrom __future__ import annotations',
     'a work\'s counts. Sent only when the site has the table (C28) and corpus-index takes it (the Srangam kit DYNASTIES),\nas the claims were; until then the rest goes as before and the plan says the dynasties wait.\n\nVAMSA_WAYIN_2026_11_18 (P2c): and the vamsas, a way in by Suryavamsa and Candravamsa across the works: the table vamsas\n(docs\\\\cloud\\\\C29_index_vamsas_2026-11-18.sql), one row a dynasty of G6c (data\\\\vamsa_read\\\\aligned.json, written by\nvamsa_align.py): its founder, its vamsa, the works that tell it and its generations, each with every work\'s name, verse\nand words, the line of that work\'s dynasties where the same person stands (so the site opens that line), Dikshitar\'s\nperson in the Purana Index, and Raychaudhuri\'s claims on that person (only those the site carries already: C23\'s rule;\nB. C. Law\'s, in copyright, never). Sent only when the site has the table (C29) and corpus-index takes it (the Srangam\nkit VAMSA_WAYIN), as the dynasties were.\n"""\nfrom __future__ import annotations')

edit('scripts/index_sync.py', 2, 'ROOT = HERE.parent\nsys.path.insert(0, str(HERE))\nTABLES = ("texts", "persons", "steps", "statements", "claims", "lines", "verses", "dynasties", "meta")   # VAMSA_JOIN_2026_11_11: dynasties\nOPTIONAL = ("claims", "dynasties")   # sent only when the site has the table (C23, C28) and corpus-index takes it\nMAX_ROWS, MAX_BYTES, MAX_KEYS = 1000, 3 * 1024 * 1024, 5000\nINDEX_RIGHTS = ("the relations derived from the index, with the entry\'s own words: Cologne Digital Sanskrit "',
     'ROOT = HERE.parent\nsys.path.insert(0, str(HERE))\nTABLES = ("texts", "persons", "steps", "statements", "claims", "lines", "verses", "dynasties", "vamsas",\n          "meta")   # VAMSA_JOIN_2026_11_11: dynasties; VAMSA_WAYIN_2026_11_18: vamsas; the run\'s row (meta) last\nOPTIONAL = ("claims", "dynasties", "vamsas")   # sent only when the site has the table (C23, C28, C29) and corpus-index takes it\nRAY_SHOWN = 3   # VAMSA_WAYIN_2026_11_18: a generation\'s claims of Raychaudhuri carried, at most (the count says how many)\nMAX_ROWS, MAX_BYTES, MAX_KEYS = 1000, 3 * 1024 * 1024, 5000\nINDEX_RIGHTS = ("the relations derived from the index, with the entry\'s own words: Cologne Digital Sanskrit "')

edit('scripts/index_sync.py', 3, '                    key_ix[ki.norm(rel, s, o)].append(ck)\n    return [finish(w) for _c, w in sorted(works.items())], rows, (key_ix, pair_ix)\n\n',
     '                    key_ix[ki.norm(rel, s, o)].append(ck)\n    return [finish(w) for _c, w in sorted(works.items())], rows, (key_ix, pair_ix)\n\n\ndef _entity_claims(claims_db: str, on_site: set, immutable: bool = False) -> dict:\n    """VAMSA_WAYIN_2026_11_18: {entity id: [claim key]}: the claims the site carries (on_site: the public-domain works\',\n    their quotation found, as _claims sends them) that name one of our entities, tied to it alone (one candidate), in\n    the book\'s order. A work in copyright (B. C. Law) has no claim on the site, so none here."""\n    if not claims_db or not on_site or not Path(claims_db).exists():\n        return {}\n    con = (ro_immutable(claims_db) if immutable else\n           sqlite3.connect(Path(claims_db).resolve().as_uri() + "?mode=ro", uri=True, timeout=10))\n    out = collections.defaultdict(list)\n    try:\n        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = \'table\'")}\n        if not {"claims", "claim_links"} <= have:\n            return {}\n        for eid, work, page, n in con.execute(\n                "SELECT l.entity_id, c.work, c.pdf_page, c.n FROM claim_links l JOIN claims c ON c.id = l.claim_id "\n                "WHERE l.role IN (\'subject\', \'object\') AND coalesce(l.cands, 0) = 1 ORDER BY c.work, c.pdf_page, c.n"):\n            k = "%s:%d:%d" % (work, page, n)\n            if k in on_site and k not in out[eid]:\n                out[eid].append(k)\n    finally:\n        con.close()\n    return dict(out)\n\n')

edit('scripts/index_sync.py', 4, '        out["dynasties"] = dynasty_rows(vamsa_read_dir, db, kin_db, g, {r["key"] for r in out["persons"]},\n                                        dynasty_works)   # VAMSA_SITE_2026_11_18\n    counts = {t: len(out[t]) for t in TABLES if t != "meta"}\n    out["meta"].append(finish({"key": "run", "value": {"mark": MARK, "scheme": SCHEME, "counts": counts,',
     '        out["dynasties"] = dynasty_rows(vamsa_read_dir, db, kin_db, g, {r["key"] for r in out["persons"]},\n                                        dynasty_works)   # VAMSA_SITE_2026_11_18\n        # VAMSA_WAYIN_2026_11_18: G6c\'s dynasties across the works, by vamsa, each generation tied to the lines above\n        out["vamsas"] = vamsa_rows(vamsa_read_dir, out["dynasties"], g,\n                                   {r["key"]: r.get("canonical") for r in out["persons"]}, out["claims"], cix[1],\n                                   _entity_claims(claims_db, {c["key"] for c in out["claims"]}, immutable))\n    counts = {t: len(out[t]) for t in TABLES if t != "meta"}\n    out["meta"].append(finish({"key": "run", "value": {"mark": MARK, "scheme": SCHEME, "counts": counts,')

edit('scripts/index_sync.py', 5, '                                "counts": {}, "source": w["source"]}))\n    return rows\n\n',
     '                                "counts": {}, "source": w["source"]}))\n    return rows\n\n\ndef vamsa_rows(vamsa_read_dir: str, dyn_rows: list, g: dict, persons: dict, claims: list, pair_ix: dict,\n               ent_claims: dict) -> list:\n    """VAMSA_WAYIN_2026_11_18: one row a dynasty of G6c (aligned.json), for the way in by vamsa: its founder, vamsa, the\n    works that tell it, its generations. A work\'s name in a generation is matched to the step of the dynasties sent\n    (dyn_rows) with the same work, verse and name: its line ("line") and its Purana Index person ("pui": Dikshitar\'s;\n    "page" when the site has the person\'s page). persons: the site\'s persons, {key: canonical name or None}.\n    Raychaudhuri\'s claims, only those the site carries: "ray", the claims that name both this generation\'s person and\n    the one before (the father in the line), at most RAY_SHOWN ("ray_n" how many); "ray_name_n", how many of his claims\n    name this person\'s name (a name may be more than one person: the site sends the reader to the name\'s page,\n    "canonical"). [] when G6c has not been run (no aligned.json)."""\n    import vamsa_align as VA\n    p = Path(vamsa_read_dir) / "aligned.json"\n    if not p.exists():\n        return []\n    al = json.loads(p.read_text(encoding="utf-8"))\n    sent = {r["work"] for r in dyn_rows}\n    at = {}\n    for r in dyn_rows:\n        for s in r.get("steps") or []:\n            at.setdefault((r["work"], s.get("ref"), VA.nkey(s.get("name"))), (r["n"], s))\n    claim_of = {c["key"]: c for c in claims}\n    order = {a[0]: i for i, a in enumerate(VA.ANCHORS, 1)}\n    entity_of = g.get("entity_of") or {}\n\n    def entity(person):\n        src, _c, e = (person or "").partition(":")\n        return entity_of.get((src, int(e))) if e.lstrip("-").isdigit() else None\n\n    def said(k):\n        c = claim_of[k]\n        return {"key": k, "work": c["work"], "printed": c.get("printed") or "", "pdf_page": c["pdf_page"],\n                "claim": c["claim"]}\n    out = []\n    for dy in al.get("dynasties") or []:\n        gens, names, before = [], set(), None\n        for r in dy.get("rows") or []:\n            cells, pui = {}, collections.Counter()\n            for wk, c in sorted((r.get("cells") or {}).items()):\n                cell = {k: c.get(k) for k in ("name", "ref", "words") if c.get(k)}\n                hit = at.get((wk, c.get("ref"), VA.nkey(c.get("name")))) if wk in sent else None\n                if hit:\n                    cell["line"] = hit[0]\n                    if hit[1].get("person"):\n                        pui[(hit[1]["person"], hit[1].get("index_head") or "", hit[1].get("index") or "")] += 1\n                cells[wk] = cell\n                if c.get("name"):\n                    names.add(c["name"])\n            gen = {"gen": r.get("gen"), "status": r.get("status") or "", "name": r.get("name") or "", "cells": cells}\n            ent = None\n            if pui:\n                (person, head, idx), _n = sorted(pui.items(), key=lambda kv: (-kv[1], kv[0]))[0]\n                gen["pui"] = {"person": person, "head": head, "index": idx}\n                if person in persons:\n                    gen["pui"]["page"] = True\n                    if persons[person]:\n                        gen["canonical"] = persons[person]\n                ent = entity(person)\n            if ent is not None:\n                named = [k for k in (ent_claims.get(ent) or []) if k in claim_of]\n                if named:\n                    gen["ray_name_n"] = len(named)\n                if before is not None and before != ent:\n                    both = [k for k in pair_ix.get((min(ent, before), max(ent, before)), []) if k in claim_of]\n                    if both:\n                        gen["ray_n"] = len(both)\n                        gen["ray"] = [said(k) for k in both[:RAY_SHOWN]]\n            before = ent\n            gens.append(gen)\n        slug = dy.get("slug") or ""\n        out.append(finish({"key": slug, "vamsa": VA.vamsa_of(slug), "ord": order.get(slug, 99),\n                           "anchor": dy.get("anchor") or "", "father": dy.get("father") or "",\n                           "title": dy.get("title") or "", "works": list(dy.get("order") or []),\n                           "counts": dy.get("counts") or {}, "rows": gens, "names": sorted(names),\n                           "aligned_at": al.get("at") or ""}))\n    return out\n\n')

edit('scripts/index_sync.py', 6, '                    "change, A1), then the Srangam kit DYNASTIES (corpus-index deployed again), then python "\n                    "scripts\\\\index_sync.py --apply" % sum(1 for r in rows.get("dynasties", []) if r.get("n")))\n    if "aliases" in got.get("features_waiting", []):   # GENEALOGY_HEAL_2026_11_10\n        wait.append("the epithets wait (Kaunteya = Arjuna): paste docs\\\\cloud\\\\C26_index_aliases_2026-11-10.sql in one "',
     '                    "change, A1), then the Srangam kit DYNASTIES (corpus-index deployed again), then python "\n                    "scripts\\\\index_sync.py --apply" % sum(1 for r in rows.get("dynasties", []) if r.get("n")))\n    if "vamsas" in got.get("waiting", []):   # VAMSA_WAYIN_2026_11_18\n        wait.append("the vamsas wait (%d dynasties of G6c): paste docs\\\\cloud\\\\C29_index_vamsas_2026-11-18.sql (B1, the "\n                    "change, A1), then the Srangam kit VAMSA_WAYIN (corpus-index deployed again), then python "\n                    "scripts\\\\index_sync.py --dynasty-works every --apply" % len(rows.get("vamsas", [])))\n    if "aliases" in got.get("features_waiting", []):   # GENEALOGY_HEAL_2026_11_10\n        wait.append("the epithets wait (Kaunteya = Arjuna): paste docs\\\\cloud\\\\C26_index_aliases_2026-11-10.sql in one "')

edit('tests/test_vamsa_site_2026_11_18.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for rel in files:\n                if MARK.encode() in (REPO / rel).read_bytes():\n                    self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)\n            self.assertIn("Nothing to do", run().stdout)\n',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for rel in files:\n                now = (REPO / rel).read_bytes()\n                # VAMSA_WAYIN_2026_11_18: a later patch changes the file again; this one\'s replay is then compared no more\n                if MARK.encode() in now and b"VAMSA_WAYIN_2026_11_18" not in now:\n                    self.assertEqual((t / rel).read_bytes(), now, rel)\n            self.assertIn("Nothing to do", run().stdout)\n')

edit('tests/test_vamsa_names_2026_11_18.py', 1, '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for rel in files:\n                if MARK.encode() in (REPO / rel).read_bytes():\n                    self.assertEqual((t / rel).read_bytes(), (REPO / rel).read_bytes(), rel)\n            self.assertIn("Nothing to do", run().stdout)\n',
     '            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)\n            for rel in files:\n                now = (REPO / rel).read_bytes()\n                # VAMSA_WAYIN_2026_11_18: a later patch changes the file again; this one\'s replay is then compared no more\n                if MARK.encode() in now and b"VAMSA_WAYIN_2026_11_18" not in now:\n                    self.assertEqual((t / rel).read_bytes(), now, rel)\n            self.assertIn("Nothing to do", run().stdout)\n')


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

