#!/usr/bin/env python3
# -*- coding: ascii -*-
"""

patch_vamsa_findings_site_2026_11_19.py  (2026-11-19)  VAMSA_FINDINGS_SITE_2026_11_19

Our findings on the vamsa page (C31). The findings a person approved on the desk (R1, data\\vamsa_findings\\<dynasty>.json)
go to the site with their dynasty's row, each citation resolved for a reader from what the site carries already: a
generation, a verse (its name, words and line), a second name a text states, Dikshitar's person, Raychaudhuri's claim
(only one the site carries) and B. C. Law's page, never his words. Sent only once the site's manifest says it takes
them (docs\\cloud\\C31_vamsa_findings_2026-11-19.sql); until then the rows go as before, their hashes unchanged.

  scripts/index_sync.py       findings_for, finding_cite, said_names, without_findings; vamsa_rows and build take
                              findings_dir; --findings (default data\\vamsa_findings); the plan says when they wait
  scripts/vamsa_findings.py   --report's NEXT, once every finding is decided: the plan of index_sync.py
  tests/test_vamsa_wayin_2026_11_18.py   its replay compares only while no later patch is on top

Anchored edits, all or nothing; a file that already carries the marker is skipped; .bak_findingssite_<date> copies.

  python scripts\\patch_vamsa_findings_site_2026_11_19.py --check
  python scripts\\patch_vamsa_findings_site_2026_11_19.py
"""
from __future__ import annotations
import argparse, datetime, os, py_compile, shutil, sys, tempfile
from pathlib import Path

MARK = 'VAMSA_FINDINGS_SITE_2026_11_19'
TAG = 'findingssite'
FILES = ['scripts/index_sync.py', 'scripts/vamsa_findings.py', 'tests/test_vamsa_wayin_2026_11_18.py']
NEEDS = {'scripts/index_sync.py': 'VAMSA_WAYIN_2026_11_18', 'scripts/vamsa_findings.py': 'VAMSA_FINDINGS_V2_2026_11_19', 'tests/test_vamsa_wayin_2026_11_18.py': 'VAMSA_WAYIN_2026_11_18'}
REQUIRES = {}   # another file that must carry a marker first
E = []


def edit(f, n, old, new):
    E.append((f, n, old, new))


edit('scripts/index_sync.py', 1, 'B. C. Law\'s, in copyright, never). Sent only when the site has the table (C29) and corpus-index takes it (the Srangam\nkit VAMSA_WAYIN), as the dynasties were.\n"""\nfrom __future__ import annotations',
     'B. C. Law\'s, in copyright, never). Sent only when the site has the table (C29) and corpus-index takes it (the Srangam\nkit VAMSA_WAYIN), as the dynasties were.\n\nVAMSA_FINDINGS_SITE_2026_11_19 (C31): and our findings on each dynasty (R1, scripts\\\\vamsa_findings.py), only those a\nperson approved, each with its citations resolved for a reader from what the site carries: a generation, a verse (its\nname, its words, its line), a second name a text states, Dikshitar\'s person, Raychaudhuri\'s claim (only one the site\ncarries: C23\'s rule) and B. C. Law\'s page, never his words (his book is in copyright and stays on the desk). A field\n"findings" of the vamsas\' rows (data\\\\vamsa_findings\\\\<dynasty>.json, --findings), sent only once the site\'s\nmanifest says it takes them ({"features": {"vamsa_findings": true}}: docs\\\\cloud\\\\C31_vamsa_findings_2026-11-19.sql);\nuntil then the rows go without it, their hashes as before.\n"""\nfrom __future__ import annotations')

edit('scripts/index_sync.py', 2, 'OPTIONAL = ("claims", "dynasties", "vamsas")   # sent only when the site has the table (C23, C28, C29) and corpus-index takes it\nRAY_SHOWN = 3   # VAMSA_WAYIN_2026_11_18: a generation\'s claims of Raychaudhuri carried, at most (the count says how many)\nMAX_ROWS, MAX_BYTES, MAX_KEYS = 1000, 3 * 1024 * 1024, 5000\nINDEX_RIGHTS = ("the relations derived from the index, with the entry\'s own words: Cologne Digital Sanskrit "',
     'OPTIONAL = ("claims", "dynasties", "vamsas")   # sent only when the site has the table (C23, C28, C29) and corpus-index takes it\nRAY_SHOWN = 3   # VAMSA_WAYIN_2026_11_18: a generation\'s claims of Raychaudhuri carried, at most (the count says how many)\nFINDINGS_FEATURE = "vamsa_findings"   # VAMSA_FINDINGS_SITE_2026_11_19: the manifest\'s word that the site takes them (C31)\nMAX_ROWS, MAX_BYTES, MAX_KEYS = 1000, 3 * 1024 * 1024, 5000\nINDEX_RIGHTS = ("the relations derived from the index, with the entry\'s own words: Cologne Digital Sanskrit "')

edit('scripts/index_sync.py', 3, '\ndef build(db: str, kin_db: str, vamsa_db: str, immutable: bool = False, claims_db: str = "",\n          vamsa_read_dir: str = "", dynasty_works: str = "all") -> dict:\n    """{table: [row]}: the site\'s rows, from the stores the dashboard\'s Vamsa page reads; read-only. vamsa_read_dir:\n    G5a\'s readings (data\\\\vamsa_read), for the dynasties (VAMSA_JOIN_2026_11_11); none given, none sent."""',
     '\ndef build(db: str, kin_db: str, vamsa_db: str, immutable: bool = False, claims_db: str = "",\n          vamsa_read_dir: str = "", dynasty_works: str = "all", findings_dir: str = "") -> dict:\n    """{table: [row]}: the site\'s rows, from the stores the dashboard\'s Vamsa page reads; read-only. vamsa_read_dir:\n    G5a\'s readings (data\\\\vamsa_read), for the dynasties (VAMSA_JOIN_2026_11_11); none given, none sent."""')

edit('scripts/index_sync.py', 4, '        out["vamsas"] = vamsa_rows(vamsa_read_dir, out["dynasties"], g,\n                                   {r["key"]: r.get("canonical") for r in out["persons"]}, out["claims"], cix[1],\n                                   _entity_claims(claims_db, {c["key"] for c in out["claims"]}, immutable))\n    counts = {t: len(out[t]) for t in TABLES if t != "meta"}\n    out["meta"].append(finish({"key": "run", "value": {"mark": MARK, "scheme": SCHEME, "counts": counts,',
     '        out["vamsas"] = vamsa_rows(vamsa_read_dir, out["dynasties"], g,\n                                   {r["key"]: r.get("canonical") for r in out["persons"]}, out["claims"], cix[1],\n                                   _entity_claims(claims_db, {c["key"] for c in out["claims"]}, immutable),\n                                   findings_dir=findings_dir)   # VAMSA_FINDINGS_SITE_2026_11_19\n    counts = {t: len(out[t]) for t in TABLES if t != "meta"}\n    out["meta"].append(finish({"key": "run", "value": {"mark": MARK, "scheme": SCHEME, "counts": counts,')

edit('scripts/index_sync.py', 5, '\ndef vamsa_rows(vamsa_read_dir: str, dyn_rows: list, g: dict, persons: dict, claims: list, pair_ix: dict,\n               ent_claims: dict) -> list:\n    """VAMSA_WAYIN_2026_11_18: one row a dynasty of G6c (aligned.json), for the way in by vamsa: its founder, vamsa, the\n    works that tell it, its generations. A work\'s name in a generation is matched to the step of the dynasties sent',
     '\ndef vamsa_rows(vamsa_read_dir: str, dyn_rows: list, g: dict, persons: dict, claims: list, pair_ix: dict,\n               ent_claims: dict, findings_dir: str = "") -> list:\n    """VAMSA_WAYIN_2026_11_18: one row a dynasty of G6c (aligned.json), for the way in by vamsa: its founder, vamsa, the\n    works that tell it, its generations. A work\'s name in a generation is matched to the step of the dynasties sent')

edit('scripts/index_sync.py', 6, '            gens.append(gen)\n        slug = dy.get("slug") or ""\n        out.append(finish({"key": slug, "vamsa": VA.vamsa_of(slug), "ord": order.get(slug, 99),\n                           "anchor": dy.get("anchor") or "", "father": dy.get("father") or "",\n                           "title": dy.get("title") or "", "works": list(dy.get("order") or []),\n                           "counts": dy.get("counts") or {}, "rows": gens, "names": sorted(names),\n                           "aligned_at": al.get("at") or ""}))\n    return out\n\n',
     '            gens.append(gen)\n        slug = dy.get("slug") or ""\n        row = {"key": slug, "vamsa": VA.vamsa_of(slug), "ord": order.get(slug, 99),\n               "anchor": dy.get("anchor") or "", "father": dy.get("father") or "",\n               "title": dy.get("title") or "", "works": list(dy.get("order") or []),\n               "counts": dy.get("counts") or {}, "rows": gens, "names": sorted(names),\n               "aligned_at": al.get("at") or ""}\n        found = findings_for(findings_dir, slug, gens, claim_of, vamsa_read_dir)   # VAMSA_FINDINGS_SITE_2026_11_19\n        if found:\n            row["findings"] = found\n        out.append(finish(row))\n    return out\n\n\ndef findings_for(findings_dir: str, slug: str, gens: list, claim_of: dict, vamsa_read_dir: str = "") -> list:\n    """VAMSA_FINDINGS_SITE_2026_11_19: a dynasty\'s findings a person approved (R1: <findings_dir>\\\\<slug>.json) as the\n    site shows them: the finding in our own words, and each citation resolved from what the site carries already:\n    "gen" a generation, "verse" a work\'s verse (its name, words and line), "second" a second name the text states,\n    "index" Dikshitar\'s person, "ray" Raychaudhuri\'s claim (only one the site carries), "law" B. C. Law\'s page and\n    nothing more (in copyright: his words never leave the desk). A citation that cannot be resolved here is left out,\n    never guessed; a finding not approved, or with a problem the checks found, is never sent. [] when there is none."""\n    if not findings_dir:\n        return []\n    p = Path(findings_dir) / ("%s.json" % slug)\n    if not slug or not p.exists():\n        return []\n    try:\n        d = json.loads(p.read_text(encoding="utf-8"))\n    except (OSError, ValueError):\n        return []\n    ids = d.get("ids") or {}\n    by_gen = {x.get("gen"): x for x in gens}\n    verse, pui, second = {}, {}, {}\n    for x in gens:\n        for wk, c in sorted((x.get("cells") or {}).items()):\n            if c.get("ref"):\n                verse.setdefault((wk, c["ref"]), (x.get("gen"), c))\n        person = (x.get("pui") or {}).get("person") or ""\n        if person:\n            pui.setdefault(person.split(":")[-1], x["pui"])\n    out = []\n    for f in d.get("findings") or []:\n        if f.get("status") != "approved" or f.get("problems") or not isinstance(f.get("text"), str):\n            continue\n        cites = []\n        for cid in f.get("cites") or []:\n            c = finding_cite(cid, ids, by_gen, verse, pui, claim_of, second, vamsa_read_dir)\n            if c and c not in cites:\n                cites.append(c)\n        out.append({"n": f.get("n"), "kind": f.get("kind") or "", "text": f["text"], "cites": cites,\n                    "model": d.get("model") or "", "prompt": d.get("prompt_version") or "",\n                    "read_at": d.get("at") or "", "approved_at": f.get("reviewed_at") or ""})\n    return out\n\n\ndef finding_cite(cid, ids: dict, by_gen: dict, verse: dict, pui: dict, claim_of: dict, second: dict,\n                 vamsa_read_dir: str = ""):\n    """VAMSA_FINDINGS_SITE_2026_11_19: one citation of a finding (g:3, v:ram1:R 1,69.18, a:mbh1:MBh 1,90.45, pi:17973,\n    r:phai1923:67:20, l:6971) for a reader, or None."""\n    if not isinstance(cid, str):\n        return None\n    kind, _c, rest = cid.partition(":")\n    if kind == "g" and rest.lstrip("-").isdigit() and int(rest) in by_gen:\n        return {"t": "gen", "gen": int(rest), "name": by_gen[int(rest)].get("name") or ""}\n    if kind in ("v", "a"):\n        wk, _c, ref = rest.partition(":")\n        if not (wk and ref):\n            return None\n        if kind == "v":\n            c = {"t": "verse", "work": wk, "ref": ref}\n            hit = verse.get((wk, ref))\n            if hit:\n                c["gen"] = hit[0]\n                c.update({k: hit[1][k] for k in ("name", "words", "line") if hit[1].get(k)})\n            return c\n        if wk not in second:\n            second[wk] = said_names(vamsa_read_dir, wk)\n        c = {"t": "second", "work": wk, "ref": ref}\n        for keep, other, r2, wds in second[wk]:\n            if r2 == ref:\n                c.update({"name": keep, "other": other, "words": wds})\n                break\n        return c\n    if kind == "pi":\n        p = pui.get(rest)\n        if not p:\n            return None\n        c = {"t": "index", "person": p["person"], "head": p.get("head") or ""}\n        if p.get("page"):\n            c["page"] = True\n        return c\n    if kind == "r":\n        cl = claim_of.get(rest)\n        if not cl:\n            return None\n        return {"t": "ray", "key": rest, "printed": cl.get("printed") or "", "pdf_page": cl.get("pdf_page"),\n                "claim": cl.get("claim") or ""}\n    if kind == "l":\n        return {"t": "law", "page": str((ids.get(cid) or {}).get("page") or "")}   # the page only, never his words\n    return None\n\n\ndef said_names(vamsa_read_dir: str, work: str) -> list:\n    """VAMSA_FINDINGS_SITE_2026_11_19: [(name, second name, ref, words)] the work\'s own statements of a second name\n    (vamsa_align.aliases_said, as R1\'s pack shows them)."""\n    if not vamsa_read_dir:\n        return []\n    try:\n        import vamsa_align as VA\n        return [(keep, other, ref, wds or "") for _ch, keep, other, ref, wds in\n                VA.aliases_said(VA.statements_of(vamsa_read_dir, work))]\n    except (OSError, ValueError, KeyError, TypeError):\n        return []\n\n')

edit('scripts/index_sync.py', 7, '\n\ndef sync(rows: dict, sink, apply: bool, log=print) -> dict:\n    """Send what differs: a table whose digest the server has is left alone; else only the rows whose hash differs,',
     '\n\ndef without_findings(rows: dict) -> dict:\n    """VAMSA_FINDINGS_SITE_2026_11_19: the vamsas as a site without C31 stores them: no findings. Their hashes are then\n    the ones such a site keeps (C29\'s), so once C31 is pasted they differ and go again with the findings."""\n    out = dict(rows)\n    out["vamsas"] = [finish({k: v for k, v in r.items() if k not in ("findings", "row_hash")}) if "findings" in r else r\n                     for r in rows.get("vamsas", [])]\n    return out\n\n\ndef sync(rows: dict, sink, apply: bool, log=print) -> dict:\n    """Send what differs: a table whose digest the server has is left alone; else only the rows whose hash differs,')

edit('scripts/index_sync.py', 8, '        rows = without_aliases(rows)   # GENEALOGY_HEAL_2026_11_10: C26 not pasted yet\n        got["features_waiting"].append("aliases")\n    for t in TABLES:\n        if t in OPTIONAL and t not in man and not rows.get(t):',
     '        rows = without_aliases(rows)   # GENEALOGY_HEAL_2026_11_10: C26 not pasted yet\n        got["features_waiting"].append("aliases")\n    if not (man.get("features") or {}).get(FINDINGS_FEATURE):   # VAMSA_FINDINGS_SITE_2026_11_19: C31 not pasted yet\n        if any("findings" in r for r in rows.get("vamsas", [])):\n            got["features_waiting"].append(FINDINGS_FEATURE)\n        rows = without_findings(rows)\n    for t in TABLES:\n        if t in OPTIONAL and t not in man and not rows.get(t):')

edit('scripts/index_sync.py', 9, '                    help="VAMSA_SITE_2026_11_18: the dynasties of G5a\'s three works (all, as before) or of every work "\n                         "read (every: with G6\'s); send every only once the site\'s page loads one work at a time")\n    ap.add_argument("--if-configured", action="store_true",\n                    help="the scheduled tick: exit 0 doing nothing until the secret, the stores, C21 and corpus-index "',
     '                    help="VAMSA_SITE_2026_11_18: the dynasties of G5a\'s three works (all, as before) or of every work "\n                         "read (every: with G6\'s); send every only once the site\'s page loads one work at a time")\n    ap.add_argument("--findings", default="", help="VAMSA_FINDINGS_SITE_2026_11_19: R1\'s findings, the approved ones "\n                                                   "sent (default data\\\\vamsa_findings)")\n    ap.add_argument("--if-configured", action="store_true",\n                    help="the scheduled tick: exit 0 doing nothing until the secret, the stores, C21 and corpus-index "')

edit('scripts/index_sync.py', 10, '    vrd = a.vamsa_read or str(ROOT / "data" / "vamsa_read")   # VAMSA_JOIN_2026_11_11\n    clm = a.claims_db or str(ROOT / "data" / "shelf" / "claims.db")\n    print("index_sync.py  %s  %s" % (MARK, "APPLY" if a.apply else "PLAN (nothing sent)"))\n    if a.if_configured and not a.dump and a.sink in ("auto", "edge"):',
     '    vrd = a.vamsa_read or str(ROOT / "data" / "vamsa_read")   # VAMSA_JOIN_2026_11_11\n    clm = a.claims_db or str(ROOT / "data" / "shelf" / "claims.db")\n    fnd = a.findings or str(ROOT / "data" / "vamsa_findings")   # VAMSA_FINDINGS_SITE_2026_11_19\n    print("index_sync.py  %s  %s" % (MARK, "APPLY" if a.apply else "PLAN (nothing sent)"))\n    if a.if_configured and not a.dump and a.sink in ("auto", "edge"):')

edit('scripts/index_sync.py', 11, '    t0 = time.time()\n    rows = build(db, kin, vam, immutable=a.immutable, claims_db=clm, vamsa_read_dir=vrd,\n                 dynasty_works=a.dynasty_works)\n    sizes = {t: sum(len(json.dumps(r, ensure_ascii=False)) for r in rows[t]) for t in TABLES}\n    print("built in %.1f s: %s" % (time.time() - t0, ", ".join("%s %d (%.1f MB)" % (t, len(rows[t]), sizes[t] / 1e6)',
     '    t0 = time.time()\n    rows = build(db, kin, vam, immutable=a.immutable, claims_db=clm, vamsa_read_dir=vrd,\n                 dynasty_works=a.dynasty_works, findings_dir=fnd)\n    sizes = {t: sum(len(json.dumps(r, ensure_ascii=False)) for r in rows[t]) for t in TABLES}\n    print("built in %.1f s: %s" % (time.time() - t0, ", ".join("%s %d (%.1f MB)" % (t, len(rows[t]), sizes[t] / 1e6)')

edit('scripts/index_sync.py', 12, '                    "change, A1), then the Srangam kit VAMSA_WAYIN (corpus-index deployed again), then python "\n                    "scripts\\\\index_sync.py --dynasty-works every --apply" % len(rows.get("vamsas", [])))\n    if "aliases" in got.get("features_waiting", []):   # GENEALOGY_HEAL_2026_11_10\n        wait.append("the epithets wait (Kaunteya = Arjuna): paste docs\\\\cloud\\\\C26_index_aliases_2026-11-10.sql in one "',
     '                    "change, A1), then the Srangam kit VAMSA_WAYIN (corpus-index deployed again), then python "\n                    "scripts\\\\index_sync.py --dynasty-works every --apply" % len(rows.get("vamsas", [])))\n    if FINDINGS_FEATURE in got.get("features_waiting", []):   # VAMSA_FINDINGS_SITE_2026_11_19\n        wait.append("our findings wait (%d approved): paste docs\\\\cloud\\\\C31_vamsa_findings_2026-11-19.sql (B1, the "\n                    "change, A1), then python scripts\\\\index_sync.py --dynasty-works every --apply"\n                    % sum(len(r.get("findings") or []) for r in rows.get("vamsas", [])))\n    if "aliases" in got.get("features_waiting", []):   # GENEALOGY_HEAL_2026_11_10\n        wait.append("the epithets wait (Kaunteya = Arjuna): paste docs\\\\cloud\\\\C26_index_aliases_2026-11-10.sql in one "')

edit('scripts/vamsa_findings.py', 1, '    say("%d proposed, %d approved, %d dropped, %d refused; the review page: %s"\n        % (tot["proposed"], tot["approved"], tot["dropped"], tot["refused"], p),\n        ("python scripts\\\\vamsa_findings.py --approve %s   (or --drop %s), once read" % (first, first)) if first else "")\n    return 0\n',
     '    say("%d proposed, %d approved, %d dropped, %d refused; the review page: %s"\n        % (tot["proposed"], tot["approved"], tot["dropped"], tot["refused"], p),\n        ("python scripts\\\\vamsa_findings.py --approve %s   (or --drop %s), once read" % (first, first)) if first else\n        # VAMSA_FINDINGS_SITE_2026_11_19: all decided: the approved ones go to the vamsa page (C31 pasted first)\n        ("python scripts\\\\index_sync.py --dynasty-works every   (the plan: %d approved finding(s) for the site)"\n         % tot["approved"]) if tot["approved"] else "")\n    return 0\n')

edit('tests/test_vamsa_wayin_2026_11_18.py', 1, '            self.assertIn("Nothing to do", buf.getvalue())\n            for rel in files:\n                self.assertEqual((t / rel).read_bytes().replace(b"\\r\\n", b"\\n"),\n                                 (REPO / rel).read_bytes().replace(b"\\r\\n", b"\\n"), rel)',
     '            self.assertIn("Nothing to do", buf.getvalue())\n            for rel in files:\n                if b"VAMSA_FINDINGS_SITE_2026_11_19" in (REPO / rel).read_bytes():\n                    continue   # VAMSA_FINDINGS_SITE_2026_11_19: a later patch on top; that patch\'s test replays it\n                self.assertEqual((t / rel).read_bytes().replace(b"\\r\\n", b"\\n"),\n                                 (REPO / rel).read_bytes().replace(b"\\r\\n", b"\\n"), rel)')


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

